"""
回测系统配置文件 - 配置回测相关参数
在 config.py 的基础上扩展回测专用配置
"""

import os

# 继承原有配置
from config import CONFIG as BASE_CONFIG

# 回测专用配置
BACKTEST_CONFIG = {
    # --- 虚拟账户配置 ---
    "INITIAL_BALANCE": 10000,           # 初始虚拟资金（元）
    "VIRTUAL_POSITION_SIZE": 1,         # 每笔虚拟交易数量
    
    # --- 数据库配置 ---
    "BACKTEST_DB": os.path.join(os.path.dirname(BASE_CONFIG["DB_NAME"]), "backtest_history.db"),
    "BACKTEST_LOG_DIR": "./backtest_logs",
    "BACKTEST_CHART_DIR": "./backtest_charts",
    
    # --- 回测参数 ---
    "DEFAULT_HOURS_BACK": 72,           # 默认回溯时间（小时）
    "MIN_BACKTEST_TRADES": 5,           # 最少交易笔数，少于此的回测结果不计入统计
    
    # --- 图表配置 ---
    "ENABLE_CHARTS": True,              # 是否生成图表
    "CHART_DPI": 300,                   # 图表分辨率
    "CHART_STYLE": "seaborn",           # 图表风格
    
    # --- 通知配置 ---
    "ENABLE_EMAIL": False,              # 是否启用邮件通知
    "EMAIL_CONFIG": {
        # SMTP 服务器配置（如需启用邮件，请填写）
        "host": "smtp.gmail.com",
        "port": 587,
        "sender": "your_email@gmail.com",
        "password": "your_app_password",  # 使用应用专用密码
        "recipient": "recipient@example.com"
    },
    "ENABLE_DINGTALK": True,           # 是否启用钉钉通知
    "DINGTALK_WEBHOOK": "https://oapi.dingtalk.com/robot/send?access_token=99fcd1e51e476655d047eada2738de4cdd9aa16cb2eb5b6a905fa6a1d4c0aa3b",             # 钉钉 webhook URL
    
    # --- 自动调度配置 ---
    "AUTO_BACKTEST_ENABLED": True,     # 是否启用自动回测
    "AUTO_BACKTEST_TYPE": "daily",      # 调度类型: daily, hourly, hours, minutes
    "AUTO_BACKTEST_PARAM": 22,          # 调度参数（小时/分钟时使用）
    
    # --- 性能指标阈值 ---
    "GOOD_WIN_RATE": 0.55,              # 优秀胜率阈值
    "GOOD_RETURN": 0.05,                # 优秀收益率阈值（>5%）
    "GOOD_SHARPE": 1.5,                 # 优秀夏普比率阈值
    "BAD_DRAWDOWN": 0.20,               # 不良最大回撤阈值（<-20%）
}

# 合并配置
CONFIG = {**BASE_CONFIG, **BACKTEST_CONFIG}
