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
from strategy import QuantStrategy
from scan_stats import ScanStats
from status_server import start_status_server

# --- 1. Core init ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
api = MarketAPI(CONFIG["SDT_KEY"], CONFIG["CSQAQ_TOKEN"])
db = MarketDB(CONFIG["DB_NAME"])
strat = QuantStrategy(CONFIG)

# --- Status monitoring ---
heartbeat_path = os.path.join(
    os.path.dirname(CURRENT_DIR), "heartbeat.json"
)
stats = ScanStats(heartbeat_path=heartbeat_path)
STATUS_HOST = CONFIG.get("STATUS_HOST", "0.0.0.0")
STATUS_PORT = int(CONFIG.get("STATUS_PORT", 8199))
start_status_server(stats, host=STATUS_HOST, port=STATUS_PORT)


def is_excluded_wear(name):
    """Filter out unwanted wear conditions."""
    if not name:
        return False
    n = str(name).lower()
    return "well-worn" in n or "battle-scarred" in n


def load_target_names():
    """Load target item names from local map."""
    file_path = os.path.join(CURRENT_DIR, "..", "data", "csqaq_id_map.json")
    if not os.path.exists(file_path):
        print(f"❓找不到目标映射文件 {file_path}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❓读取目标映射失败: {e}")
        return []

    hot_keywords = ["AK-47", "M4A1-S", "AWP", "USP-S", "Glock-18", "★", "Gloves", "Knife", "MAC-10"]
    names = [
        str(k) for k in data.keys()
        if any(kd in str(k) for kd in hot_keywords) and not is_excluded_wear(k)
    ]
    names = sorted(set(names))
    print(f"✅成功加载 {len(names)} 个目标")
    return names


def load_blacklist():
    """Load blacklist set and file path."""
    blacklist_file = CONFIG.get("BLACKLIST_FILE", "low_sales_blacklist.txt")
    blacklist = set()
    if os.path.exists(blacklist_file):
        try:
            with open(blacklist_file, "r", encoding="utf-8") as f:
                blacklist = {line.strip() for line in f if line.strip()}
        except Exception as e:
            print(f"⚠️ 黑名单读取失败，继续空黑名单: {e}")
    return blacklist_file, blacklist


def append_blacklist(name, blacklist, blacklist_file):
    """Append one name to blacklist only once."""
    if name in blacklist:
        return False

    blacklist.add(name)
    try:
        with open(blacklist_file, "a", encoding="utf-8") as f:
            f.write(f"{name}\n")
    except Exception as e:
        print(f"⚠️ 黑名单写入失败 {name} | {e}")
    return True


def _to_positive_int(value):
    """Convert value to positive int or return None."""
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
    """
    Try to resolve series_id from API payloads.
    If all candidates are missing, return None.
    """
    candidates = []

    if isinstance(ref, dict):
        candidates.extend([
            ref.get("series_id"),
            ref.get("seriesId"),
            ref.get("seriesID"),
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
            item.get("goodsSeriesId"),
        ])
        series_obj = item.get("series")
        if isinstance(series_obj, dict):
            candidates.extend([
                series_obj.get("id"),
                series_obj.get("series_id"),
                series_obj.get("seriesId"),
            ])

    for candidate in candidates:
        series_id = _to_positive_int(candidate)
        if series_id is not None:
            return series_id
    return None


def log_opportunity(data):
    """保存高分信号到CSV"""
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
    """Main scan loop with integrated status tracking."""
    print("=" * 60)
    print(f"  CS2 Quant Scanner  |  PID: {os.getpid()}")
    print(f"  Status API: http://{STATUS_HOST}:{STATUS_PORT}/")
    print("=" * 60)

    names = load_target_names()
    if not names:
        print("❓没有目标商品，退出")
        return

    blacklist_file, blacklist = load_blacklist()
    print(f"📌 黑名单: {len(blacklist)} 个")

    # cooldown settings
    buy_cooldown_sec = CONFIG.get("BUY_COOLDOWN_MINUTES", 120) * 60
    max_buy_per_hour = CONFIG.get("MAX_BUY_PER_HOUR", 15)
    recent_buy_times = deque()
    recent_buy_by_name = {}

    round_num = 0

    while True:
        round_num += 1
        active_names = [n for n in names if n not in blacklist]
        stats.start_round(round_num, len(active_names))
        print(f"\n{'='*50}")
        print(f"🔄 第 {round_num} 轮扫描 | 有效商品: {len(active_names)}")
        print(f"{'='*50}")

        batch_size = CONFIG["BATCH_SIZE"]
        total_batches = (len(active_names) + batch_size - 1) // batch_size

        for i in range(0, len(active_names), batch_size):
            batch = active_names[i:i + batch_size]
            batch_idx = i // batch_size + 1
            stats.start_batch(batch_idx, total_batches)
            print(f"\n--- 批次 {batch_idx}/{total_batches} ({len(batch)} items) ---")

            sdt_prices = api.get_batch_sdt(batch)
            csqaq_prices = api.get_batch_csqaq(batch)
            price_map = {}

            for item in sdt_prices:
                n = item.get("marketHashName", "")
                p = item.get("lowestPrice")
                if n and p:
                    price_map.setdefault(n, {})["悠悠"] = float(p)

            for n, info in csqaq_prices.items():
                p = info.get("sell_price") or info.get("price")
                if p:
                    price_map.setdefault(n, {})["Buff"] = float(p)

            for name in batch:
                try:
                    platforms = price_map.get(name)
                    if not platforms:
                        continue

                    buy_plat = "悠悠"
                    sell_plat = "Buff"
                    buy_price = platforms.get(buy_plat)
                    sell_price = platforms.get(sell_plat)

                    if not buy_price or not sell_price:
                        continue

                    if buy_price < CONFIG["MIN_PRICE"] or buy_price > CONFIG["MAX_PRICE"]:
                        stats.record_skip("price")
                        continue

                    cross_platform_spread = (sell_price - buy_price) / buy_price
                    if cross_platform_spread <= CONFIG.get("MIN_PROFIT", 0.07):
                        continue

                    sales = 0
                    csqaq_info = csqaq_prices.get(name, {})
                    if isinstance(csqaq_info, dict):
                        sales = csqaq_info.get("sales_24h", 0) or 0

                    if sales < CONFIG["MIN_SALES_24H"]:
                        if sales < CONFIG["MIN_SALES_24H"] // 2:
                            added = append_blacklist(name, blacklist, blacklist_file)
                            if added:
                                print(f"🚫 销量过低({sales})，加入黑名单: {name[:40]}")
                        stats.record_skip("sales")
                        continue

                    if name in blacklist:
                        stats.record_skip("blacklist")
                        continue

                    # UU platform fee calculation
                    platform_fee_rate = CONFIG.get("PLATFORM_FEE_RATE", 0.025)
                    
                    # UU platform: buy fee + sell fee
                    buy_fee = buy_price * platform_fee_rate
                    sell_fee = sell_price * platform_fee_rate
                    net_profit = (sell_price - buy_price) - buy_fee - sell_fee
                    net_profit_rate = net_profit / buy_price if buy_price > 0 else 0

                    series_id = extract_series_id(item, csqaq_info)
                    db.save_item_snapshot(name, buy_price, sales, series_id=series_id)
                    analysis_data = db.get_item_analysis_data(name)

                    print(
                        f"🔍 {name[:30]:<30} | {buy_plat}->{sell_plat} | "
                        f"买{buy_price:.1f} 卖{sell_price:.1f} | 利润:{net_profit_rate:>7.2%}"
                    )

                    report = strat.analyze(
                        analysis_data,
                        trade_ctx={
                            "name": name,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "buy_from": buy_plat,
                            "sell_to": sell_plat,
                            "sales": sales,
                            "net_profit_rate": net_profit_rate,
                            "cross_platform_spread": cross_platform_spread,
                        },
                    )
                    action = report.get("action", "WAIT")
                    status_map = {"WAIT": "⏳", "BUY": "💎", "SELL": "🔻", "HOLD": "⚖", "SKIP": "⏸"}
                    status = status_map.get(action, "⚖")
                    print(
                        f"{status} {name[:30]:<30} | 买价{buy_price:>8.1f} | 销量{sales:>3} | "
                        f"S1:{report.get('score1', '-')!s:>6} S2:{report.get('score2', '-')!s:>6} SCR:{report.get('score', '-')!s:>6} | {report.get('msg', '')}"
                    )

                    stats.record_item(name, action, score=report.get("score"))

                    if action == "BUY":
                        now_ts = time.time()
                        while recent_buy_times and now_ts - recent_buy_times[0] > 3600:
                            recent_buy_times.popleft()

                        last_buy_ts = recent_buy_by_name.get(name)
                        if last_buy_ts and now_ts - last_buy_ts < buy_cooldown_sec:
                            cooldown_left = int((buy_cooldown_sec - (now_ts - last_buy_ts)) / 60)
                            print(f"⏳{name[:30]:<30} | 冷却中，剩余约{max(cooldown_left, 1)} 分钟")
                            stats.record_cooldown()
                            continue

                        if len(recent_buy_times) >= max_buy_per_hour:
                            print(f"⏳BUY 节流触发：近1小时已达上限({max_buy_per_hour})，跳过{name[:30]}")
                            stats.record_throttle()
                            continue

                        log_opportunity({
                            "time": datetime.now().strftime("%m-%d %H:%M:%S"),
                            "name": name,
                            "price": buy_price,
                            "buy_from": buy_plat,
                            "sell_to": sell_plat,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "profit": f"{net_profit_rate:.2%}",
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
                    print(f"⚠️ 单品处理异常: {name} | {e}")
                    stats.record_error(f"{name}: {e}")
                    continue

            print(f"--- 进度 {min(i + CONFIG['BATCH_SIZE'], len(names))}/{len(names)} ---")
            time.sleep(62)

        stats.finish_round()
        print(f"\n✅轮次结束，休眠{CONFIG['SLEEP_TIME']}s...")
        time.sleep(CONFIG["SLEEP_TIME"])


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stats.stop()
        print("\n🛑 用户停止扫描")
