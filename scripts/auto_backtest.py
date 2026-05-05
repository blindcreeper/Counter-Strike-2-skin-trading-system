"""
CS2 皮肤量化回测系统 - 自动定时回测脚本
用法: python auto_backtest.py
"""

import os
import sys
import json
import schedule
import time
import logging
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from backtest_quick import quick_backtest, quick_auto_tune
from auto_tuner import AutoTuner
from backtest_db import BacktestDatabase
from run_backtest import CompleteBacktestSystem

# 计算项目根目录与日志目录（避免受 cwd 影响）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
LOG_DIR = os.path.join(ROOT_DIR, "output", "backtest_logs")
os.makedirs(LOG_DIR, exist_ok=True)
APP_CONFIG_FILE = os.path.join(ROOT_DIR, "config", "app_config.json")


def _load_app_config():
    try:
        with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, 'scheduler.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def scheduled_backtest():
    """定时执行的回测任务"""
    logger.info("🚀 定时回测任务启动...")
    try:
        quick_backtest()
        logger.info("✅ 定时回测任务完成")
    except Exception as e:
        logger.error(f"❌ 回测任务失败: {e}", exc_info=True)


def scheduled_auto_tune():
    """定时执行自动调参任务"""
    logger.info("🧠 自动调参任务启动...")
    try:
        quick_auto_tune()
        logger.info("✅ 自动调参任务完成")
    except Exception as e:
        logger.error(f"❌ 自动调参任务失败: {e}", exc_info=True)


def scheduled_apply_params():
    """按节奏启用 pending 参数。"""
    logger.info("🧩 参数生效检查启动...")
    try:
        system = CompleteBacktestSystem()
        tuner = AutoTuner(system, BacktestDatabase())
        changed, reason = tuner.apply_pending_params_if_due()
        logger.info(f"✅ 参数生效检查完成 | changed={changed} | reason={reason}")
    except Exception as e:
        logger.error(f"❌ 参数生效检查失败: {e}", exc_info=True)


def main():
    """主程序"""
    logger.info("=" * 60)
    logger.info("CS2 皮肤量化回测系统 - 自动定时任务启动")
    logger.info("=" * 60)
    
    # 获取调度配置：环境变量 > app_config.json > 默认值
    app_cfg = _load_app_config()
    scheduler_cfg = app_cfg.get("scheduler", {}) if isinstance(app_cfg.get("scheduler"), dict) else {}
    tuning_cfg = app_cfg.get("tuning", {}) if isinstance(app_cfg.get("tuning"), dict) else {}
    run_mode = os.getenv('SCHEDULE_MODE', str(scheduler_cfg.get("mode", 'daily')))
    run_time = os.getenv('SCHEDULE_TIME', str(scheduler_cfg.get("time", '22:00')))
    interval = os.getenv('SCHEDULE_INTERVAL', str(scheduler_cfg.get("interval_hours", '6')))  # 小时
    tuning_enabled = bool(tuning_cfg.get("enabled", False))
    tuning_day = str(tuning_cfg.get("weekly_day", "sunday")).lower()
    tuning_time = str(tuning_cfg.get("weekly_time", "03:30"))
    
    logger.info(f"定时模式: {run_mode}")
    logger.info(f"运行时间: {run_time}")
    
    # 设置定时任务
    if run_mode == 'daily':
        schedule.every().day.at(run_time).do(scheduled_backtest)
        logger.info(f"✅ 已设置: 每天 {run_time} 自动执行回测")
    
    elif run_mode == 'hourly':
        schedule.every().hour.do(scheduled_backtest)
        logger.info("✅ 已设置: 每小时自动执行回测")
    
    elif run_mode == 'interval':
        hours = int(interval)
        schedule.every(hours).hours.do(scheduled_backtest)
        logger.info(f"✅ 已设置: 每 {hours} 小时自动执行回测")
    
    elif run_mode == 'immediate':
        # 立即运行一次，然后定时
        scheduled_backtest()
        schedule.every().day.at(run_time).do(scheduled_backtest)
        logger.info(f"✅ 已设置: 立即运行，然后每天 {run_time} 自动执行")
    
    else:
        logger.warning(f"未知的定时模式: {run_mode}，使用默认 daily 模式")
        schedule.every().day.at(run_time).do(scheduled_backtest)
        logger.info(f"✅ 已设置: 每天 {run_time} 自动执行回测")

    if tuning_enabled and hasattr(schedule.every(), tuning_day):
        getattr(schedule.every(), tuning_day).at(tuning_time).do(scheduled_auto_tune)
        logger.info(f"✅ 已设置: 每周 {tuning_day} {tuning_time} 自动调参")

    schedule.every().day.at("03:10").do(scheduled_apply_params)
    logger.info("✅ 已设置: 每天 03:10 检查是否应用 pending 参数")
    
    # 主循环
    logger.info("进入主循环，按 Ctrl+C 停止...")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次任务
    
    except KeyboardInterrupt:
        logger.info("\n🛑 用户停止定时任务")
        logger.info("再见！")
    
    except Exception as e:
        logger.error(f"❌ 发生错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
