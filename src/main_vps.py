import csv
import json
import os
import sys
import time
from collections import deque
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CONFIG
from api_client import MarketAPI
from database import MarketDB
from execution_engine import ExecutionEngine
from strategy import QuantStrategy
from scan_stats import ScanStats
from status_server import start_status_server
from dingtalk_notify import notify_buy_signal, notify_error, notify_scan_report

# --- 1. Core init ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
api = MarketAPI(CONFIG["SDT_KEY"], CONFIG["CSQAQ_TOKEN"])
db = MarketDB(CONFIG["DB_NAME"])
executor = ExecutionEngine(db, CONFIG)
strat = QuantStrategy(CONFIG)

# --- Status monitoring ---
heartbeat_path = os.path.join(
    os.path.dirname(CURRENT_DIR), "heartbeat.json"
)
stats = ScanStats(heartbeat_path=heartbeat_path)
STATUS_HOST = CONFIG.get("STATUS_HOST", "0.0.0.0")
STATUS_PORT = int(CONFIG.get("STATUS_PORT", 8199))
start_status_server(stats, host=STATUS_HOST, port=STATUS_PORT)
last_report_ts = 0


def is_excluded_wear(name):
    if not name:
        return False
    n = str(name).lower()
    return "well-worn" in n or "battle-scarred" in n


def load_target_names():
    file_path = os.path.join(CURRENT_DIR, "..", "data", "csqaq_id_map.json")
    if not os.path.exists(file_path):
        print("target map not found")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("target map load failed:", e)
        return []
    hot_keywords = ["AK-47", "M4A1-S", "AWP", "USP-S", "Glock-18", "\u2605", "Gloves", "Knife", "MAC-10"]
    names = [
        str(k) for k in data.keys()
        if any(kd in str(k) for kd in hot_keywords) and not is_excluded_wear(k)
    ]
    names = sorted(set(names))
    print(f"loaded {len(names)} targets")
    return names


def load_blacklist():
    blacklist_file = CONFIG.get("BLACKLIST_FILE", "low_sales_blacklist.txt")
    blacklist = set()
    if os.path.exists(blacklist_file):
        try:
            with open(blacklist_file, "r", encoding="utf-8") as f:
                blacklist = {line.strip() for line in f if line.strip()}
        except Exception:
            pass
    return blacklist_file, blacklist


def append_blacklist(name, blacklist, blacklist_file):
    if name in blacklist:
        return False
    blacklist.add(name)
    try:
        with open(blacklist_file, "a", encoding="utf-8") as f:
            f.write(name + "\n")
    except Exception:
        pass
    return True


def _to_positive_int(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        iv = int(value)
        return iv if iv > 0 else None
    s = str(value).strip()
    if s.isdigit():
        iv = int(s)
        return iv if iv > 0 else None
    return None


def extract_series_id(item, ref):
    candidates = []
    if isinstance(ref, dict):
        candidates.extend([
            ref.get("series_id"),
            ref.get("seriesId"),
            ref.get("seriesID"),
            ref.get("goodId"),
            ref.get("goodsSeriesId"),
        ])
        series_obj = ref.get("series")
        if isinstance(series_obj, dict):
            candidates.extend([
                series_obj.get("id"),
                series_obj.get("series_id"),
                series_obj.get("seriesId"),
            ])
    if isinstance(item, dict):
        candidates.extend([
            item.get("series_id"),
            item.get("seriesId"),
            item.get("seriesID"),
            item.get("goodId"),
            item.get("goodsSeriesId"),
        ])
        series_obj = item.get("series")
        if isinstance(series_obj, dict):
            candidates.extend([
                series_obj.get("id"),
                series_obj.get("series_id"),
                series_obj.get("seriesId"),
            ])
    for c in candidates:
        sid = _to_positive_int(c)
        if sid is not None:
            return sid
    return None


def log_opportunity(data):
    log_file = CONFIG.get("LOG_FILE", "opportunities.csv")
    fieldnames = [
        "time", "name", "price", "buy_from", "sell_to",
        "buy_price", "sell_price", "profit",
        "slope", "hurst", "er", "changes", "score1", "score2", "score",
    ]
    file_exists = os.path.isfile(log_file)
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        row = {k: data.get(k, "") for k in fieldnames}
        writer.writerow(row)


def run():
    global last_report_ts
    print("=" * 60)
    print(f"  CS2 Quant Scanner  |  PID: {os.getpid()}")
    print(f"  Status API: http://{STATUS_HOST}:{STATUS_PORT}/")
    print("=" * 60)

    names = load_target_names()
    if not names:
        print("no targets, exit")
        return

    blacklist_file, blacklist = load_blacklist()
    print(f"blacklist: {len(blacklist)}")

    buy_cooldown_sec = CONFIG.get("BUY_COOLDOWN_MINUTES", 120) * 60
    max_buy_per_hour = CONFIG.get("MAX_BUY_PER_HOUR", 15)
    recent_buy_times = deque()
    recent_buy_by_name = {}
    round_num = 0

    while True:
        round_num += 1
        active_names = [n for n in names if n not in blacklist]
        stats.start_round(round_num, len(active_names))
        print(f"\nround {round_num} | items: {len(active_names)}")

        batch_size = CONFIG["BATCH_SIZE"]
        total_batches = (len(active_names) + batch_size - 1) // batch_size

        for i in range(0, len(active_names), batch_size):
            batch = active_names[i:i + batch_size]
            batch_idx = i // batch_size + 1
            stats.start_batch(batch_idx, total_batches)
            print(f"batch {batch_idx}/{total_batches} ({len(batch)})")

            csqaq_prices = api.get_batch_csqaq(batch)

            for name in batch:
                try:
                    stats.record_seen()
                    info = csqaq_prices.get(name)
                    if not info or not isinstance(info, dict):
                        continue

                    buy_price = info.get("yyypSellPrice") or 0
                    sell_price = info.get("buffSellPrice") or 0
                    sales = info.get("buffSellNum") or info.get("yyypSellNum") or 0

                    if not buy_price or not sell_price:
                        continue

                    stats.record_quote()

                    if buy_price < CONFIG["MIN_PRICE"] or buy_price > CONFIG["MAX_PRICE"]:
                        stats.record_skip("price")
                        continue

                    if sales < CONFIG["MIN_SALES_24H"]:
                        if sales < CONFIG["MIN_SALES_24H"] // 2:
                            append_blacklist(name, blacklist, blacklist_file)
                        stats.record_skip("sales")
                        continue

                    if name in blacklist:
                        stats.record_skip("blacklist")
                        continue

                    platform_fee_rate = CONFIG.get("PLATFORM_FEE_RATE", 0.025)
                    price_edge_rate = (sell_price - buy_price) / buy_price
                    if price_edge_rate <= CONFIG.get("MIN_EDGE_SCORE", 0.02):
                        stats.record_skip("edge")
                        continue

                    buy_fee = buy_price * platform_fee_rate
                    sell_fee = sell_price * platform_fee_rate
                    estimated_net_profit = (sell_price - buy_price) - buy_fee - sell_fee
                    estimated_net_return = estimated_net_profit / buy_price if buy_price > 0 else 0

                    if estimated_net_return <= CONFIG.get("MIN_NET_PROFIT_RATE", 0.02):
                        print(
                            f"⏳ {name[:30]:<30} | edge{price_edge_rate:>7.2%} cushion{estimated_net_return:>7.2%} | "
                            f"below cushion threshold({CONFIG.get('MIN_NET_PROFIT_RATE', 0.02):.2%})"
                        )
                        stats.record_skip("cushion")
                        continue

                    series_id = extract_series_id(None, info)
                    db.save_item_snapshot(name, buy_price, sales, series_id=series_id)
                    analysis_data = db.get_item_analysis_data(name)

                    report = strat.analyze(
                        analysis_data,
                        trade_ctx={
                            "name": name,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "buy_from": "\u60a0\u60a0",
                            "sell_to": "Buff",
                            "sales": sales,
                            "estimated_net_return": estimated_net_return,
                            "net_profit_rate": estimated_net_return,
                            "price_edge_rate": price_edge_rate,
                            "cross_platform_spread": price_edge_rate,
                        },
                    )
                    action = report.get("action", "WAIT")

                    status_map = {"WAIT": "\u23f3", "BUY": "\U0001f48e", "SELL": "\U0001f53b", "HOLD": "\u2696", "SKIP": "\u23f8"}
                    status = status_map.get(action, "\u2696")
                    print(
                        f"{status} {name[:30]:<30} | buy{buy_price:>8.1f} sell{sell_price:>8.1f} sales{sales:>3} "
                        f"edge:{price_edge_rate:>7.2%} | S1:{report.get('score1','-'):>6} S2:{report.get('score2','-'):>6} SCR:{report.get('score','-'):>6}"
                    )

                    signal_payload = {
                        "signal_time": int(time.time()),
                        "hash_name": name,
                        "action": action,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "sales_24h": sales,
                        "price_edge_rate": price_edge_rate,
                        "estimated_net_return": estimated_net_return,
                        "score": report.get("score"),
                        "score1": report.get("score1"),
                        "score2": report.get("score2"),
                        "slope": report.get("slope"),
                        "er": report.get("er"),
                        "hurst": report.get("hurst"),
                        "changes": report.get("changes"),
                        "series_id": series_id,
                        "signal_meta": {
                            "buy_from": "悠悠",
                            "sell_to": "Buff",
                            "message": report.get("msg", ""),
                        },
                    }
                    signal_id, position = executor.on_signal(name, action, signal_payload)
                    if action != "BUY":
                        executor.maybe_close_position(name, sell_price)

                    stats.record_item(
                        name,
                        action,
                        score=report.get("score"),
                        buy_price=buy_price,
                        sell_price=sell_price,
                        profit_rate=estimated_net_return,
                    )

                    if action == "BUY":
                        notify_buy_signal(
                            name,
                            buy_price,
                            sell_price,
                            price_edge_rate,
                            report.get("score"),
                            estimated_net_return=estimated_net_return,
                            factor_text=report.get("msg", ""),
                        )
                        now_ts = time.time()
                        while recent_buy_times and now_ts - recent_buy_times[0] > 3600:
                            recent_buy_times.popleft()
                        last_buy_ts = recent_buy_by_name.get(name)
                        if last_buy_ts and now_ts - last_buy_ts < buy_cooldown_sec:
                            stats.record_cooldown()
                            continue
                        if len(recent_buy_times) >= max_buy_per_hour:
                            stats.record_throttle()
                            continue
                        log_opportunity({
                            "time": datetime.now().strftime("%m-%d %H:%M:%S"),
                            "name": name,
                            "price": buy_price,
                            "buy_from": "\u60a0\u60a0",
                            "sell_to": "Buff",
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "profit": f"{price_edge_rate:.2%}",
                            "slope": report.get("slope"),
                            "hurst": report.get("hurst"),
                            "er": report.get("er"),
                            "changes": report.get("changes"),
                            "score1": report.get("score1"),
                            "score2": report.get("score2"),
                        })
                        recent_buy_by_name[name] = now_ts
                        recent_buy_times.append(now_ts)
                except Exception as e:
                    print(f"error: {name} | {e}")
                    stats.record_error(f"{name}: {e}")
                    notify_error(f"{name}: {e}")
                    continue

            now_report_ts = time.time()
            # per-batch periodic report disabled; only report at round end

            print(f"--- progress {min(i + batch_size, len(active_names))}/{len(active_names)} ---")
            time.sleep(62)

        stats.finish_round()
        notify_scan_report(stats.get_snapshot())
        print(f"round done, sleep {CONFIG['SLEEP_TIME']}s")
        time.sleep(CONFIG["SLEEP_TIME"])


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stats.stop()
        print("stopped")
