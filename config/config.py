import os
import json

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)  # 在根目录
APP_CONFIG_FILE = os.path.join(BASE_DIR, "app_config.json")


def _load_app_config():
    """Load optional global app config JSON."""
    if not os.path.exists(APP_CONFIG_FILE):
        return {}
    try:
        with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


APP_CFG = _load_app_config()
API_CFG = APP_CFG.get("api", {}) if isinstance(APP_CFG.get("api"), dict) else {}
STRATEGY_CFG = APP_CFG.get("strategy", {}) if isinstance(APP_CFG.get("strategy"), dict) else {}
TUNING_CFG = APP_CFG.get("tuning", {}) if isinstance(APP_CFG.get("tuning"), dict) else {}


def _resolve_active_strategy_config():
    active = {}
    if isinstance(STRATEGY_CFG, dict):
        active.update(STRATEGY_CFG)

    if isinstance(TUNING_CFG, dict):
        pending_params = TUNING_CFG.get("pending_params")
        applied_params = TUNING_CFG.get("applied_params")
        if isinstance(applied_params, dict):
            active.update(applied_params)
        if isinstance(pending_params, dict):
            active.setdefault("_pending_params", pending_params)
    return active


ACTIVE_STRATEGY_CFG = _resolve_active_strategy_config()

# 运行模式: "collect" = 数据采集(跳过过滤，广撒网记录) | "trade" = 正常交易(按策略过滤)
RUN_MODE = APP_CFG.get("mode", "trade")

CONFIG = {
    # --- 鉴权信息 ---
    # 优先级：环境变量 > app_config.json > 默认值（便于本地调试）
    "SDT_KEY": os.getenv("SDT_KEY", API_CFG.get("sdt_key", "CHANGE_ME")),
    "CSQAQ_TOKEN": os.getenv("CSQAQ_TOKEN", API_CFG.get("csqaq_token", "CHANGE_ME")),
    
    # --- 价格与基础过滤 ---
    "MIN_PRICE": 30.0,          # 最低买入价 30 元
    "MAX_PRICE": 6000,        # 最高买入价 3000 元
    "MIN_SALES_24H": 40,        # Buff 24小时销量门槛(低流动性直接跳过)
    "FEE_RATE": 0.025,          # 平台综合手续费率(Buff一般为2.5%)

    # --- 量化因子阈值(大脑的判断标准) ---
    "MIN_EDGE_SCORE": float(ACTIVE_STRATEGY_CFG.get("MIN_EDGE_SCORE", 0.02)),     # 最低跨平台价差因子，作为趋势预测特征的基础门槛
    "MIN_NET_PROFIT_RATE": float(ACTIVE_STRATEGY_CFG.get("MIN_NET_PROFIT_RATE", 0.0)), # 先放宽到0%，优先让BUY信号产出用于验证链路
    "MIN_ER": 0.6,              # 价格效率比(0.6以上代表走势足够平滑，不是乱跳)
    "MIN_HURST": 0.17,          # Hurst 指数门槛
    "BUY_SCORE_THRESHOLD": int(ACTIVE_STRATEGY_CFG.get("BUY_SCORE_THRESHOLD", 28)),  # 显著放宽综合分门槛，先确保BUY信号能产出
    "TREND_SCORE_THRESHOLD": float(ACTIVE_STRATEGY_CFG.get("TREND_SCORE_THRESHOLD", 50)),
    "HOLDING_PERIOD_HOURS": int(ACTIVE_STRATEGY_CFG.get("HOLDING_PERIOD_HOURS", 168)),
    "BUY_COOLDOWN_MINUTES": 120,# 同一商品信号冷却时间
    "MAX_BUY_PER_HOUR": 15,     # 每小时最多记录 BUY 数
    "TAKE_PROFIT_RATE": float(ACTIVE_STRATEGY_CFG.get("TAKE_PROFIT_RATE", 0.08)),   # 持仓止盈阈值
    "STOP_LOSS_RATE": float(ACTIVE_STRATEGY_CFG.get("STOP_LOSS_RATE", -0.05)),    # 持仓止损阈值
    
    # --- 运行逻辑配置 ---
    "BATCH_SIZE": 50,           # 每次批量请求 50 个饰品
    "SLEEP_TIME": 3000,           # 轮次间歇时间 (秒)
    "HISTORY_WINDOW": 60,       # 关键修改：数据库保留最近60 条记录
    
    # --- DEFAULT_PLATFORM (UU) ---
    "DEFAULT_PLATFORM": "悠悠",
    "PLATFORM_FEE_RATE": 0.025,

    # --- Status Server ---
    "STATUS_HOST": os.getenv("STATUS_HOST", "0.0.0.0"),
    "STATUS_PORT": int(os.getenv("STATUS_PORT", "8199")),
    "DINGTALK_REPORT_INTERVAL_SECONDS": int(os.getenv("DINGTALK_REPORT_INTERVAL_SECONDS", "900")),

    # --- 文件与数据库 ---
    "DB_NAME": os.path.join(ROOT_DIR, "shared_data", "cs2_quant.db"),
    "BLACKLIST_FILE": os.path.join(ROOT_DIR, "shared_data", "low_sales_blacklist.txt"),
    "LOG_FILE": os.path.join(ROOT_DIR, "shared_data", "opportunities.csv")


}
