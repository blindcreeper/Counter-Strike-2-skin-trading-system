"""
常驻量化流水线：
1) 持续运行 src/main.py 扫描并筛选机会
2) 按计划执行回测并发送钉钉通知
"""

import os
import sys
import time
import logging
import threading
import argparse

import schedule


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")

sys.path.insert(0, SRC_DIR)
sys.path.insert(0, SCRIPT_DIR)

import main as scanner_main
from backtest_quick import quick_backtest
from send_dingtalk_error import send_error_notification


LOG_DIR = os.path.join(ROOT_DIR, "output", "pipeline_logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "live_pipeline.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_scanner_forever():
    """持续运行主扫描器。"""
    logger.info("启动主扫描器 src/main.py ...")
    try:
        scanner_main.run()
    except Exception as exc:
        logger.error("主扫描器异常退出: %s", exc, exc_info=True)
        raise


def run_backtest_once():
    """执行一次回测任务。"""
    logger.info("触发定时回测任务...")
    ok = False
    try:
        result = quick_backtest()
        ok = bool(result) if result is not None else True
        if ok:
            logger.info("定时回测执行完成")
        else:
            logger.error("定时回测返回失败状态")
    except Exception as exc:
        logger.error("定时回测异常: %s", exc, exc_info=True)
        ok = False

    if not ok:
        webhook = os.getenv("DINGTALK_WEBHOOK", "").strip()
        if webhook:
            send_error_notification(webhook, "live_pipeline 定时回测失败，请查看 workflow 日志。")


def main():
    parser = argparse.ArgumentParser(description="CS2 常驻扫描+定时回测流水线")
    parser.add_argument(
        "--backtest-interval-minutes",
        type=int,
        default=int(os.getenv("BACKTEST_INTERVAL_MINUTES", "360")),
        help="回测间隔（分钟）",
    )
    parser.add_argument(
        "--run-duration-minutes",
        type=int,
        default=int(os.getenv("RUN_DURATION_MINUTES", "0")),
        help="整体运行时长（分钟），0 表示无限运行",
    )
    parser.add_argument(
        "--run-backtest-immediately",
        action="store_true",
        help="启动后立刻执行一次回测",
    )
    args = parser.parse_args()

    logger.info("=" * 68)
    logger.info("CS2 常驻流水线启动：持续扫描 + 定时回测")
    logger.info("回测间隔: %s 分钟", args.backtest_interval_minutes)
    logger.info(
        "运行时长: %s",
        "无限" if args.run_duration_minutes <= 0 else f"{args.run_duration_minutes} 分钟",
    )
    logger.info("=" * 68)

    scanner_thread = threading.Thread(target=run_scanner_forever, daemon=True, name="scanner")
    scanner_thread.start()

    schedule.every(args.backtest_interval_minutes).minutes.do(run_backtest_once)
    if args.run_backtest_immediately:
        run_backtest_once()

    start_ts = time.time()
    run_seconds = args.run_duration_minutes * 60

    while True:
        if not scanner_thread.is_alive():
            logger.error("主扫描器线程已退出，流水线终止")
            sys.exit(1)

        schedule.run_pending()
        time.sleep(5)

        if run_seconds > 0 and time.time() - start_ts >= run_seconds:
            logger.info("达到设定运行时长，流水线正常结束")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("收到中断信号，流水线停止")
