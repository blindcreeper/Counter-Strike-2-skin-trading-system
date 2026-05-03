import os
import sys
import math
import statistics
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import CONFIG
from database import MarketDB


def _bucketize(value, ranges):
    for lower, upper, label in ranges:
        if lower <= value < upper:
            return label
    return ranges[-1][2]


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def summarize_group(samples, target_return=0.03):
    if not samples:
        return None
    outcomes = [_safe_float(s.get("outcome_72h")) for s in samples]
    max_returns = [_safe_float(s.get("max_return_72h")) for s in samples]
    hit_count = sum(1 for value in outcomes if value > 0)
    target_hits = sum(1 for value in max_returns if value >= target_return)
    return {
        "count": len(samples),
        "hit_rate": hit_count / len(samples),
        "target_hit_rate": target_hits / len(samples),
        "avg_outcome_72h": statistics.mean(outcomes) if outcomes else 0.0,
        "avg_max_return_72h": statistics.mean(max_returns) if max_returns else 0.0,
    }


def analyze_signal_factors(days=30, action="BUY", target_return=0.03):
    db = MarketDB(CONFIG["DB_NAME"])
    min_signal_time = int((datetime.now() - timedelta(days=days)).timestamp())
    events = db.get_signal_events(action=action, min_signal_time=min_signal_time)
    events = [event for event in events if event.get("outcome_72h") is not None]

    edge_ranges = [
        (0.00, 0.02, "0-2%"),
        (0.02, 0.04, "2-4%"),
        (0.04, 0.06, "4-6%"),
        (0.06, math.inf, ">=6%"),
    ]
    score_ranges = [
        (0, 50, "<50"),
        (50, 60, "50-60"),
        (60, 70, "60-70"),
        (70, 80, "70-80"),
        (80, math.inf, ">=80"),
    ]

    edge_groups = {}
    score_groups = {}
    keyword_groups = {}

    for event in events:
        edge_bucket = _bucketize(_safe_float(event.get("price_edge_rate")), edge_ranges)
        score_bucket = _bucketize(_safe_float(event.get("score")), score_ranges)
        keyword = "UNKNOWN"
        item_name = str(event.get("hash_name", ""))
        if "Knife" in item_name:
            keyword = "KNIFE"
        elif "Glove" in item_name or "Gloves" in item_name:
            keyword = "GLOVES"
        elif "AWP" in item_name:
            keyword = "AWP"

        edge_groups.setdefault(edge_bucket, []).append(event)
        score_groups.setdefault(score_bucket, []).append(event)
        keyword_groups.setdefault(keyword, []).append(event)

    return {
        "generated_at": datetime.now().isoformat(),
        "action": action,
        "days": days,
        "sample_count": len(events),
        "target_return": target_return,
        "edge_groups": {k: summarize_group(v, target_return) for k, v in edge_groups.items()},
        "score_groups": {k: summarize_group(v, target_return) for k, v in score_groups.items()},
        "keyword_groups": {k: summarize_group(v, target_return) for k, v in keyword_groups.items()},
    }


def format_report_text(report):
    lines = [
        f"信号因子命中率报告 | 样本: {report['sample_count']} | 周期: {report['days']}天",
        f"目标收益阈值: {report['target_return']:.2%}",
        "",
        "Edge 分组:",
    ]
    for label, stats in sorted(report["edge_groups"].items()):
        if not stats:
            continue
        lines.append(
            f"- {label}: 样本{stats['count']} 命中{stats['hit_rate']:.1%} 达标{stats['target_hit_rate']:.1%} 平均72h{stats['avg_outcome_72h']:.2%}"
        )
    lines.append("")
    lines.append("Score 分组:")
    for label, stats in sorted(report["score_groups"].items()):
        if not stats:
            continue
        lines.append(
            f"- {label}: 样本{stats['count']} 命中{stats['hit_rate']:.1%} 达标{stats['target_hit_rate']:.1%} 平均72h{stats['avg_outcome_72h']:.2%}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    report = analyze_signal_factors()
    print(format_report_text(report))
