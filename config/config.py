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

CONFIG = {
    # --- 鉴权信息 ---
    # 优先级：环境变量 > app_config.json > 默认值（便于本地调试）
    "SDT_KEY": os.getenv("SDT_KEY", API_CFG.get("sdt_key", "aa1f20fe10ca45248d260201df963772")),
    "CSQAQ_TOKEN": os.getenv("CSQAQ_TOKEN", API_CFG.get("csqaq_token", "SBWSE1M7Q6P8E65703O8O9Q7")),
    
    # --- 价格与基础过滤 ---
    "MIN_PRICE": 30.0,          # 最低买入价 30 元
    "MAX_PRICE": 6000,        # 最高买入价 3000 元
    "MIN_SALES_24H": 40,        # Buff 24小时销量门槛 (低流动性直接跳过)
    "FEE_RATE": 0.025,          # 平台综合手续费 (Buff一般为2.5%)

    # --- 量化因子阈值 (大脑的判断标准) ---
    "MIN_PROFIT": 0.07,         # 预期净利润率需 > 7% 才考虑入场
    "MIN_ER": 0.6,              # 价格效率比 (0.6以上代表走势足够平滑，不是乱跳)
    "MIN_HURST": 0.17,          # Hurst 指数门槛
    "BUY_SCORE_THRESHOLD": 76,  # 新版策略综合分门槛（提高后更严格）
    "BUY_COOLDOWN_MINUTES": 120,# 同一单品信号冷却时间
    "MAX_BUY_PER_HOUR": 15,     # 每小时最多记录 BUY 数
    
    # --- 运行逻辑配置 ---
    "BATCH_SIZE": 50,           # 每次批量请求 50 个饰品
    "SLEEP_TIME": 3000,           # 轮次间歇时间 (秒)
    "HISTORY_WINDOW": 60,       # 关键修改：数据库保留最近 60 条记录 (支持计算长线 Hurst 指数)
    
    # --- 文件与数据库 ---
    "DB_NAME": os.path.join(ROOT_DIR, "cs2_quant.db"),
    "BLACKLIST_FILE": os.path.join(ROOT_DIR, "low_sales_blacklist.txt"),
    "LOG_FILE": os.path.join(ROOT_DIR, "opportunities.csv")


}
