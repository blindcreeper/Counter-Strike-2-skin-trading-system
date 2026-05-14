"""
数据规律分析脚本 - 从 collect 模式积累的数据中找出涨势好的商品共同特征
直接从 item_history 的 price_series 分析，不依赖 CSV
"""

import sqlite3
import json
import os
import sys
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CONFIG

DB_PATH = CONFIG["DB_NAME"]
FEE_RATE = CONFIG.get("PLATFORM_FEE_RATE", 0.025)


def load_all_items():
    """加载所有商品的价格序列"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT hash_name, price_series, sales_series FROM item_history")
    items = []
    for row in cursor.fetchall():
        name, ps, ss = row
        prices = json.loads(ps) if ps else []
        sales = json.loads(ss) if ss else []
        if len(prices) >= 10:
            items.append({"name": name, "prices": prices, "sales": sales})
    conn.close()
    return items


def calc_features(prices, sales):
    """计算单个商品的所有量化特征"""
    if len(prices) < 10:
        return None

    n = len(prices)
    p = np.array(prices, dtype=float)

    # 1. 收益率（整体涨幅）
    total_return = (p[-1] - p[0]) / p[0] if p[0] > 0 else 0

    # 2. 近10期 slope
    recent10 = p[-10:]
    slope = (recent10[-1] - recent10[0]) / recent10[0] if recent10[0] > 0 else 0

    # 3. 波动率
    returns = np.diff(p) / p[:-1]
    volatility = np.std(returns) if len(returns) > 0 else 0

    # 4. ER (效率比)
    total_change = abs(p[-1] - p[-10])
    path_length = sum(abs(p[i] - p[i-1]) for i in range(max(0, n-10), n))
    er = total_change / path_length if path_length > 0 else 0

    # 5. Hurst 指数
    hurst = calc_hurst(p)

    # 6. 价格变化次数
    changes = sum(1 for i in range(max(0, n-10), n) if p[i] != p[i-1])

    # 7. 价格区间
    price_level = p[-1]

    # 8. 最大涨幅（任意区间）
    max_gain = 0
    for i in range(n):
        for j in range(i+1, n):
            gain = (p[j] - p[i]) / p[i]
            if gain > max_gain:
                max_gain = gain

    # 9. 最大回撤
    cummax = np.maximum.accumulate(p)
    drawdowns = (p - cummax) / cummax
    max_dd = float(drawdowns.min())

    # 10. 均线趋势（价格是否在MA上方）
    if n >= 10:
        ma10 = np.mean(p[-10:])
        above_ma = 1 if p[-1] > ma10 else 0
        ma_ratio = (p[-1] - ma10) / ma10
    else:
        above_ma = 0
        ma_ratio = 0

    # 11. 销量水平
    avg_sales = np.mean(sales[-5:]) if len(sales) >= 5 else (sales[-1] if sales else 0)

    # 12. 连涨/连跌
    consec_up = 0
    for i in range(len(p)-1, 0, -1):
        if p[i] > p[i-1]:
            consec_up += 1
        else:
            break

    return {
        "total_return": total_return,
        "slope_10": slope,
        "volatility": volatility,
        "er": er,
        "hurst": hurst,
        "changes": changes,
        "price_level": float(price_level),
        "max_gain": max_gain,
        "max_drawdown": max_dd,
        "above_ma": above_ma,
        "ma_ratio": ma_ratio,
        "avg_sales": float(avg_sales),
        "consec_up": consec_up,
        "n_points": n,
    }


def calc_hurst(prices):
    if len(prices) < 4:
        return 0.5
    y = np.array(prices, dtype=float)
    n = len(y)
    max_lag = max(2, n // 2)
    if max_lag <= 2:
        return 0.5
    lags = range(2, max_lag)
    tau = []
    for lag in lags:
        diff = y[lag:] - y[:-lag]
        std = np.std(diff)
        tau.append(np.sqrt(std if std > 0 else 1e-9))
    if len(tau) < 2:
        return 0.5
    try:
        m = np.polyfit(np.log(list(lags)), np.log(tau), 1)
        return float(m[0])
    except Exception:
        return 0.5


def percentile_bucket(value, percentiles):
    """把值映射到分位区间"""
    for i, p in enumerate(percentiles):
        if value <= p:
            return i
    return len(percentiles)


def main():
    print("=" * 70)
    print("  CS2 数据规律分析 - 从 collect 模式积累数据中找特征")
    print("=" * 70)

    items = load_all_items()
    print(f"\n加载 {len(items)} 个商品（数据点 >= 10）")

    # 计算所有特征
    results = []
    for item in items:
        features = calc_features(item["prices"], item["sales"])
        if features:
            features["name"] = item["name"]
            results.append(features)

    if not results:
        print("没有足够数据")
        return

    print(f"成功计算特征: {len(results)} 个商品\n")

    # 定义"涨得好"的标准：整体涨幅 > 3%
    GAIN_THRESHOLD = 0.03
    gainers = [r for r in results if r["total_return"] >= GAIN_THRESHOLD]
    losers = [r for r in results if r["total_return"] <= -0.02]
    neutral = [r for r in results if -0.02 < r["total_return"] < GAIN_THRESHOLD]

    print(f"涨得好 (>=3%): {len(gainers)} 个 ({len(gainers)/len(results)*100:.1f}%)")
    print(f"跌得多 (<=-2%): {len(losers)} 个 ({len(losers)/len(results)*100:.1f}%)")
    print(f"横盘中性:       {len(neutral)} 个 ({len(neutral)/len(results)*100:.1f}%)")

    # ========== 对比分析：涨 vs 不涨 ==========
    print("\n" + "=" * 70)
    print("  特征对比：涨得好 vs 不涨")
    print("=" * 70)

    def group_stats(group, key):
        vals = [r[key] for r in group if r.get(key) is not None]
        if not vals:
            return None
        return {
            "mean": np.mean(vals),
            "median": np.median(vals),
            "p25": np.percentile(vals, 25),
            "p75": np.percentile(vals, 75),
        }

    features_to_compare = [
        ("slope_10", "近10期斜率"),
        ("er", "效率比(ER)"),
        ("hurst", "Hurst指数"),
        ("changes", "价格变化次数"),
        ("volatility", "波动率"),
        ("price_level", "价格水平"),
        ("avg_sales", "平均销量"),
        ("max_drawdown", "最大回撤"),
        ("ma_ratio", "偏离MA10"),
        ("consec_up", "连续上涨次数"),
    ]

    print(f"\n{'特征':<16} {'涨得好(均值)':<16} {'涨得好(中位)':<16} {'不涨(均值)':<16} {'不涨(中位)':<16} {'区分度':<8}")
    print("-" * 88)

    non_gainers = [r for r in results if r["total_return"] < GAIN_THRESHOLD]
    discriminative_features = []

    for key, label in features_to_compare:
        g_stats = group_stats(gainers, key)
        ng_stats = group_stats(non_gainers, key)
        if g_stats and ng_stats:
            # 区分度 = 涨组均值 vs 不涨组均值的差异（标准化）
            combined_std = np.std([r[key] for r in results])
            if combined_std > 0:
                discrimination = abs(g_stats["mean"] - ng_stats["mean"]) / combined_std
            else:
                discrimination = 0
            print(f"{label:<16} {g_stats['mean']:>14.4f} {g_stats['median']:>14.4f} {ng_stats['mean']:>14.4f} {ng_stats['median']:>14.4f} {discrimination:>7.2f}")
            discriminative_features.append((key, label, discrimination, g_stats["mean"], ng_stats["mean"]))

    # ========== 最具区分力的特征 ==========
    print("\n" + "=" * 70)
    print("  最具区分力的特征 TOP 5")
    print("=" * 70)
    discriminative_features.sort(key=lambda x: x[2], reverse=True)
    for i, (key, label, disc, g_mean, ng_mean) in enumerate(discriminative_features[:5], 1):
        direction = "越高越涨" if g_mean > ng_mean else "越低越涨"
        print(f"  {i}. {label}: 区分度={disc:.3f} ({direction})")
        print(f"     涨组均值={g_mean:.4f}, 不涨组均值={ng_mean:.4f}")

    # ========== 分位数分析 ==========
    print("\n" + "=" * 70)
    print("  分位数分析：各区间上涨概率")
    print("=" * 70)

    for key, label, disc, g_mean, ng_mean in discriminative_features[:3]:
        vals = [r[key] for r in results]
        p20 = np.percentile(vals, 20)
        p40 = np.percentile(vals, 40)
        p60 = np.percentile(vals, 60)
        p80 = np.percentile(vals, 80)
        buckets = [
            (f"<{p20:.4f}", lambda v, t=p20: v < t),
            (f"{p20:.4f}-{p40:.4f}", lambda v, t1=p20, t2=p40: t1 <= v < t2),
            (f"{p40:.4f}-{p60:.4f}", lambda v, t1=p40, t2=p60: t1 <= v < t2),
            (f"{p60:.4f}-{p80:.4f}", lambda v, t1=p60, t2=p80: t1 <= v < t2),
            (f">={p80:.4f}", lambda v, t=p80: v >= t),
        ]
        print(f"\n  {label}:")
        for bucket_label, test_fn in buckets:
            bucket_items = [r for r in results if test_fn(r[key])]
            if bucket_items:
                gain_count = sum(1 for r in bucket_items if r["total_return"] >= GAIN_THRESHOLD)
                win_rate = gain_count / len(bucket_items) * 100
                avg_return = np.mean([r["total_return"] for r in bucket_items]) * 100
                print(f"    {bucket_label:<25s} | n={len(bucket_items):>4d} | 上涨率={win_rate:>5.1f}% | 平均涨幅={avg_return:>6.2f}%")

    # ========== 推荐过滤条件 ==========
    print("\n" + "=" * 70)
    print("  推荐过滤条件（基于数据规律）")
    print("=" * 70)

    # 用涨幅组的分位数来确定阈值
    if gainers:
        print("\n  涨得好组的特征范围:")
        for key, label, disc, _, _ in discriminative_features[:5]:
            g_vals = [r[key] for r in gainers]
            ng_vals = [r[key] for r in non_gainers]
            g_p25 = np.percentile(g_vals, 25)
            g_p75 = np.percentile(g_vals, 75)
            print(f"    {label}: 涨组 [{g_p25:.4f}, {g_p75:.4f}]")

        # 具体阈值推荐
        print("\n  推荐 app_config.json strategy 设置:")

        # slope: 涨组的下界
        g_slopes = [r["slope_10"] for r in gainers]
        g_slope_p25 = np.percentile(g_slopes, 25)

        # ER
        g_ers = [r["er"] for r in gainers]
        g_er_median = np.percentile(g_ers, 50)

        # price_level
        g_prices = [r["price_level"] for r in gainers]
        g_price_p75 = np.percentile(g_prices, 75)

        # volatility
        g_vols = [r["volatility"] for r in gainers]
        g_vol_p75 = np.percentile(g_vols, 75)

        # changes
        g_changes = [r["changes"] for r in gainers]
        g_changes_median = np.percentile(g_changes, 50)

        print(f"""
    基于数据分析的推荐值（涨组特征区间）:

    MIN_SLOPE_THRESHOLD: {g_slope_p25:.4f}   # slope >= 此值才考虑买入
    MIN_ER_THRESHOLD:    {g_er_median:.4f}   # ER 效率比下限
    MAX_PRICE:           {g_price_p75:.0f}        # 价格上限
    MAX_VOLATILITY:      {g_vol_p75:.4f}   # 波动率上限（太波动的不碰）
    MIN_CHANGES:         {g_changes_median:.0f}         # 价格变化次数下限（太冷清的不好）
        """)

    # ========== 涨幅 TOP 20 ==========
    print("\n" + "=" * 70)
    print("  涨幅 TOP 20 商品")
    print("=" * 70)
    top20 = sorted(results, key=lambda x: x["total_return"], reverse=True)[:20]
    for i, r in enumerate(top20, 1):
        print(f"  {i:>2}. {r['name'][:45]:<45} | 涨幅:{r['total_return']:>7.2%} | "
              f"slope:{r['slope_10']:>6.3f} | ER:{r['er']:>5.3f} | "
              f"价格:{r['price_level']:>7.1f} | 销量:{r['avg_sales']:>5.0f}")

    # ========== 跌幅 TOP 10 ==========
    print("\n" + "=" * 70)
    print("  跌幅 TOP 10 商品（要避开的）")
    print("=" * 70)
    bottom10 = sorted(results, key=lambda x: x["total_return"])[:10]
    for i, r in enumerate(bottom10, 1):
        print(f"  {i:>2}. {r['name'][:45]:<45} | 跌幅:{r['total_return']:>7.2%} | "
              f"slope:{r['slope_10']:>6.3f} | ER:{r['er']:>5.3f} | "
              f"价格:{r['price_level']:>7.1f} | 销量:{r['avg_sales']:>5.0f}")

    print("\n" + "=" * 70)
    print("  分析完成！根据以上结果调整 strategy 参数后切换到 trade 模式")
    print("=" * 70)


if __name__ == "__main__":
    main()
