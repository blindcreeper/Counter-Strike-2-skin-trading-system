"""
快速回测脚本 - 无需Menu直接运行
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from run_backtest import CompleteBacktestSystem


def _load_app_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, "..", "config", "app_config.json")
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def quick_backtest():
    """快速执行一次回测（支持钉钉通知）"""
    system = CompleteBacktestSystem()
    app_cfg = _load_app_config()
    backtest_cfg = app_cfg.get("backtest", {}) if isinstance(app_cfg.get("backtest"), dict) else {}
    notif_cfg = app_cfg.get("notification", {}) if isinstance(app_cfg.get("notification"), dict) else {}

    dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK", notif_cfg.get("dingtalk_webhook", ""))
    hours_back = int(backtest_cfg.get("hours_back", 72))
    initial_balance = float(backtest_cfg.get("initial_balance", 10000))
    enable_charts = bool(backtest_cfg.get("enable_charts", True))
    
    print("\n" + "="*70)
    print("🚀 快速回测模式 - 执行72小时机会数据回测".center(70))
    print("="*70 + "\n")
    
    return system.run_backtest(
        hours_back=hours_back,
        initial_balance=initial_balance,
        enable_charts=enable_charts,
        enable_dingtalk=bool(dingtalk_webhook),
        dingtalk_webhook=dingtalk_webhook,
    )


def quick_backtest_extended():
    """扩展回测 - 7天数据（支持钉钉通知）"""
    system = CompleteBacktestSystem()
    app_cfg = _load_app_config()
    notif_cfg = app_cfg.get("notification", {}) if isinstance(app_cfg.get("notification"), dict) else {}

    dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK", notif_cfg.get("dingtalk_webhook", ""))
    
    print("\n" + "="*70)
    print("📊 扩展回测模式 - 执行7天机会数据回测".center(70))
    print("="*70 + "\n")
    
    return system.run_backtest(
        hours_back=168,  # 7天
        initial_balance=10000,
        enable_charts=True,
        enable_dingtalk=bool(dingtalk_webhook),
        dingtalk_webhook=dingtalk_webhook,
    )


def view_history():
    """查看历史回测"""
    system = CompleteBacktestSystem()
    system.view_backtest_history(limit=20)
    system.view_backtest_statistics(days=7)


def quick_auto_tune():
    system = CompleteBacktestSystem()
    print("\n" + "="*70)
    print("🧠 自动调参模式 - 执行小规模参数搜索".center(70))
    print("="*70 + "\n")
    return system.run_auto_tune(trials=8, hours_back=72, initial_balance=10000)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == 'quick':
            quick_backtest()
        elif cmd == 'extended':
            quick_backtest_extended()
        elif cmd == 'history':
            view_history()
        elif cmd == 'tune':
            quick_auto_tune()
        else:
            print("用法: python backtest_quick.py [quick|extended|history|tune|auto]")
            print("")
            print("quick    - 快速回测72小时数据")
            print("extended - 扩展回测7天数据")
            print("history  - 查看回测历史")
            print("tune     - 小规模自动调参")
    else:
        # 默认执行快速回测
        quick_backtest()
