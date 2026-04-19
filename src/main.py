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

# --- 1. Core init ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
api = MarketAPI(CONFIG["SDT_KEY"], CONFIG["CSQAQ_TOKEN"])
db = MarketDB(CONFIG["DB_NAME"])
strat = QuantStrategy(CONFIG)


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
        print(f"❌ 找不到目标映射文件: {file_path}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 读取目标映射失败: {e}")
        return []

    hot_keywords = ["AK-47", "M4A1-S", "AWP", "USP-S", "Glock-18", "★", "Gloves", "Knife", "MAC-10"]
    names = [
        str(k) for k in data.keys()
        if any(kd in str(k) for kd in hot_keywords) and not is_excluded_wear(k)
    ]
    names = sorted(set(names))
    print(f"✅ 成功加载 {len(names)} 个目标")
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
        print(f"⚠️ 黑名单写入失败: {name} | {e}")
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
    """保存高分信号到 CSV"""
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


# --- 2. Runtime ---
def run():
    all_names = load_target_names()
    blacklist_file, blacklist = load_blacklist()
    names = [n for n in all_names if n not in blacklist]
    buy_cooldown_sec = int(CONFIG.get("BUY_COOLDOWN_MINUTES", 90)) * 60
    max_buy_per_hour = int(CONFIG.get("MAX_BUY_PER_HOUR", 15))
    recent_buy_by_name = {}
    recent_buy_times = deque()

    if not names:
        print("⚠️ 过滤后无剩余目标，请检查目标名单或黑名单")
        return

    print(f"🎌 扫描器启动 | 原始目标: {len(all_names)} | 黑名单过滤后: {len(names)}")
    print("=" * 60)

    while True:
        # Keep names synced with in-memory blacklist (instant effect in current process).
        names = [n for n in all_names if n not in blacklist]
        if not names:
            print(f"⚠️ 当前目标已全部被过滤，休眠 {CONFIG['SLEEP_TIME']}s...")
            time.sleep(CONFIG["SLEEP_TIME"])
            continue

        # A. Sync macro series snapshots
        try:
            series_list = api.get_series_list()
            if series_list:
                for s in series_list:
                    try:
                        db.save_series_snapshot(
                            s.get("id"),
                            s.get("name", ""),
                            s.get("recently_data", []),
                            s.get("sell_price_30", 0),
                        )
                    except Exception as row_err:
                        print(f"⚠️ 板块快照写入失败: {row_err}")
        except Exception as e:
            print(f"⚠️ 宏观数据同步失败: {e}")

        # B. Batch scan
        for i in range(0, len(names), CONFIG["BATCH_SIZE"]):
            batch = names[i:i + CONFIG["BATCH_SIZE"]]
            sdt_data = api.get_batch_sdt(batch)
            csqaq_data = api.get_batch_csqaq(batch)
            if not isinstance(csqaq_data, dict):
                csqaq_data = {}

            for item in sdt_data:
                name = item.get("marketHashName")
                if not name or name in blacklist or is_excluded_wear(name):
                    continue

                ref = csqaq_data.get(name)
                if not ref:
                    continue

                try:
                    all_platforms = item.get("dataList", [])
                    domestic_platforms = [
                        p for p in all_platforms
                        if p.get("sellPrice", 0) > 0 and p.get("platform", "").upper() != "STEAM"
                    ]
                    if len(domestic_platforms) < 2:
                        continue

                    domestic_platforms.sort(key=lambda x: x["sellPrice"])
                    buy_p = domestic_platforms[0]
                    buy_price = float(buy_p["sellPrice"])
                    buy_plat = buy_p.get("platform", "UNKNOWN")

                    domestic_platforms.sort(key=lambda x: x["sellPrice"], reverse=True)
                    sell_p = domestic_platforms[0]
                    sell_price = float(sell_p["sellPrice"])
                    sell_plat = sell_p.get("platform", "UNKNOWN")

                    if buy_price < CONFIG.get("MIN_PRICE", 30.0) or buy_price > CONFIG.get("MAX_PRICE", 3000.0):
                        continue

                    sales = int(ref.get("buffSellNum", 0))
                    min_sales = CONFIG.get("MIN_SALES_24H", 40)
                    if sales < min_sales:
                        added = append_blacklist(name, blacklist, blacklist_file)
                        if added:
                            print(f"🚫 销量过低({sales})，加入黑名单: {name[:40]}")
                        continue

                    # 修正利润计算：同时扣除买入和卖出手续费
                    buy_fee_rate = CONFIG.get("FEE_RATE", 0.03)  # 买入平台手续费
                    sell_fee_rate = 0.025 if sell_plat.upper() == "BUFF" else CONFIG.get("FEE_RATE", 0.03)
                    
                    # 实际买入成本 = 买入价 + 买入手续费
                    total_buy_cost = buy_price * (1 + buy_fee_rate)
                    
                    # 实际卖出收入 = 卖出价 - 卖出手续费
                    net_sell_income = sell_price * (1 - sell_fee_rate)
                    
                    # 净利润率 = (净卖出收入 - 总买入成本) / 买入价
                    net_profit_rate = (net_sell_income - total_buy_cost) / buy_price

                    series_id = extract_series_id(item, ref)
                    db.save_item_snapshot(name, buy_price, sales, series_id=series_id)
                    analysis_data = db.get_item_analysis_data(name)

                    print(
                        f"🔎 {name[:30]:<30} | {buy_plat}->{sell_plat} | "
                        f"买:{buy_price:.1f} 卖:{sell_price:.1f} | 利润:{net_profit_rate:>7.2%}"
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
                        },
                    )
                    action = report.get("action", "WAIT")
                    status_map = {"WAIT": "⏳", "BUY": "💎", "SELL": "🔻", "HOLD": "⚪", "SKIP": "⏭"}
                    status = status_map.get(action, "⚪")
                    print(
                        f"{status} {name[:30]:<30} | 买价{buy_price:>8.1f} | 销量{sales:>3} | "
                        f"S1:{report.get('score1', '-')!s:>6} S2:{report.get('score2', '-')!s:>6} SCR:{report.get('score', '-')!s:>6} | {report.get('msg', '')}"
                    )

                    if action == "BUY":
                        now_ts = time.time()
                        while recent_buy_times and now_ts - recent_buy_times[0] > 3600:
                            recent_buy_times.popleft()

                        last_buy_ts = recent_buy_by_name.get(name)
                        if last_buy_ts and now_ts - last_buy_ts < buy_cooldown_sec:
                            cooldown_left = int((buy_cooldown_sec - (now_ts - last_buy_ts)) / 60)
                            print(f"⏸ {name[:30]:<30} | 冷却中，剩余约 {max(cooldown_left, 1)} 分钟")
                            continue

                        if len(recent_buy_times) >= max_buy_per_hour:
                            print(f"⏸ BUY 节流触发：近1小时已达上限({max_buy_per_hour})，跳过 {name[:30]}")
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
                    continue

            print(f"--- 进度 {min(i + CONFIG['BATCH_SIZE'], len(names))}/{len(names)} ---")
            time.sleep(62)

        print(f"\n✅ 轮次结束，休眠 {CONFIG['SLEEP_TIME']}s...")
        time.sleep(CONFIG["SLEEP_TIME"])


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n🛑 用户停止扫描")
