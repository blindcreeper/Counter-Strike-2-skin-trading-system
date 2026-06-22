"""DingTalk notification helper with richer scan reporting."""
import json
import os
from datetime import datetime

import requests

from database import MarketDB


def _load_webhook():
    webhook = os.getenv("DINGTALK_WEBHOOK", "")
    if webhook:
        return webhook
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "config", "app_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("notification", {}).get("dingtalk_webhook", "")
    except Exception:
        return ""


WEBHOOK = _load_webhook()
SECRET_WORD = "ding"


def _send(content):
    if not WEBHOOK or "your_token" in WEBHOOK:
        return False
    try:
        msg = {"msgtype": "text", "text": {"content": content}}
        payload = json.dumps(msg).encode("utf-8")
        response = requests.post(
            WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=10,
        )
        return response.status_code == 200 and response.json().get("errcode") == 0
    except Exception:
        return False


def _build_scan_extras():
    from config import CONFIG
    db_path = CONFIG.get("DB_NAME", os.path.join(os.path.dirname(__file__), "..", "shared_data", "cs2_quant.db"))
    open_positions = 0
    pending_evals = 0
    try:
        db = MarketDB(db_path)
        open_positions = len([
            row for row in db.get_signal_events(action="BUY")
            if row.get("evaluation_status") == "pending"
        ])
        pending_evals = len(db.get_pending_signal_evaluations())
    except Exception:
        pass
    return open_positions, pending_evals


def notify_scan_report(stats_snapshot):
    s = stats_snapshot
    status_map = {
        "scanning": "扫描中",
        "sleeping": "休眠中",
        "stopped": "已停止",
        "idle": "空闲",
    }
    status_cn = status_map.get(s.get("status", ""), s.get("status", ""))
    open_positions, pending_evals = _build_scan_extras()

    lines = [
        f"{SECRET_WORD} CS2扫描器报告",
        "",
        f"状态: {status_cn} (第{s.get('round_count', 0)}轮)",
        f"进度: 批次 {s.get('current_batch', 0)}/{s.get('total_batches', 0)}",
        f"遍历商品: {s.get('items_seen', 0)}",
        f"拿到双边报价: {s.get('items_with_quotes', 0)}",
        f"已扫描: {s.get('items_scanned', 0)}个商品通过过滤",
        f"跳过(价格): {s.get('items_skipped_price', 0)}",
        f"跳过(销量): {s.get('items_skipped_sales', 0)}",
        f"跳过(价差因子): {s.get('items_skipped_edge', 0)}",
        f"跳过(安全垫): {s.get('items_skipped_cushion', 0)}",
        f"BUY信号: {s.get('buy_signals', 0)}",
        f"WAIT信号: {s.get('wait_signals', 0)}",
        f"HOLD信号: {s.get('hold_signals', 0)}",
        f"SELL信号: {s.get('sell_signals', 0)}",
        f"错误: {s.get('errors', 0)}",
        f"待评估信号: {pending_evals}",
        f"跟踪中持仓: {open_positions}",
    ]
    if s.get("last_error"):
        lines.append(f"最近错误: {str(s.get('last_error'))[:80]}")

    recent = s.get("recent_items", [])[:5]
    if recent:
        lines.append("")
        lines.append("近期扫描:")
        for item in recent:
            lines.append(f"- {str(item.get('name', ''))[:35]} {item.get('action', '-')}")

    last_buy = s.get("last_buy_signal")
    if last_buy:
        lines.append("")
        lines.append("最近BUY:")
        lines.append(
            f"- {str(last_buy.get('name', '-'))[:35]} | 分数:{last_buy.get('score', '-')} | 时间:{str(last_buy.get('time', '-'))[:16]}"
        )

    recent_buys = s.get("recent_buy_signals", [])[:5]
    if recent_buys:
        lines.append("")
        lines.append("本轮BUY明细:")
        for item in recent_buys:
            lines.append(
                f"- {str(item.get('name', '-'))[:28]} | 买:{item.get('buy_price', '-')} 卖:{item.get('sell_price', '-')} | "
                f"垫:{item.get('profit_rate', '-')} | 分:{item.get('score', '-')}"
            )

    lines.append("")
    lines.append("http://38.207.171.210:8199/")
    return _send("\r\n".join(lines))


def notify_buy_signal(name, buy_price, sell_price, edge_rate, score,
                      estimated_net_return=None, factor_text="",
                      buy_platform=None, trend_score=None):
    trend_str = f"趋势评分: {trend_score:.1f}" if trend_score is not None else "趋势评分: -"
    buy_plat_str = f"买入平台: {buy_platform}" if buy_platform else ""
    lines = [
        f"{SECRET_WORD} CS2 趋势买入信号!",
        "",
        f"商品: {name[:50]}",
    ]
    if buy_plat_str:
        lines.append(buy_plat_str)
    lines.extend([
        f"买入价: {buy_price:.1f}",
        f"参考卖价: {sell_price:.1f}",
        trend_str,
        f"综合分: {score}",
        f"价差: {edge_rate:.2%}",
        f"因子: {factor_text[:80]}" if factor_text else "因子: -",
        "",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ])
    return _send("\r\n".join(lines))


def notify_simulated_sell(name, entry_price, sell_price, net_return, holding_hours, reason):
    result = "盈利" if net_return > 0 else "亏损"
    lines = [
        f"{SECRET_WORD} CS2 虚拟交易结算",
        "",
        f"商品: {name[:50]}",
        f"买入价: {entry_price:.1f}",
        f"卖出价: {sell_price:.1f}",
        f"净收益: {net_return:.2%} ({result})",
        f"持仓时长: {holding_hours:.0f}小时",
        f"平仓原因: {reason}",
        "",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return _send("\r\n".join(lines))


def notify_error(error_msg):
    lines = [
        f"{SECRET_WORD} CS2扫描器异常!",
        "",
        f"错误: {str(error_msg)[:200]}",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return _send("\r\n".join(lines))
