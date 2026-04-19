import sqlite3
import json
import time

class MarketDB:
    def __init__(self, db_name="cs2_quant.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """初始化表结构：单品表 + 热门系列表"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # 1. 单品历史表：记录具体的皮肤价格和销量
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS item_history (
                    hash_name TEXT PRIMARY KEY,
                    series_id INTEGER,        -- 关联热门系列ID
                    price_series TEXT,       -- 存储价格列表 (JSON)
                    sales_series TEXT,       -- 存储销量列表 (JSON)
                    last_update INTEGER
                )
            ''')
            
            # 2. 热门系列表：记录板块宏观走势 (对应你新获取的 API)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS series_history (
                    series_id INTEGER PRIMARY KEY,
                    series_name TEXT,
                    recent_15d_data TEXT,    -- 存储 API 返回的 recently_data
                    sell_price_30 REAL,      -- 30日涨跌幅，用于宏观过滤
                    last_update INTEGER
                )
            ''')
            conn.commit()

    # --- 单品数据操作 ---

    def save_item_snapshot(self, name, price, sales, series_id=None):
        """保存单品快照点"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT price_series, sales_series, series_id FROM item_history WHERE hash_name = ?", (name,))
            row = cursor.fetchone()

            if row:
                prices = json.loads(row[0])
                sales_list = json.loads(row[1])
                old_series_id = row[2]
            else:
                prices, sales_list = [], []
                old_series_id = None

            # 仅在本次拿到有效 series_id 时覆盖；否则保留历史值
            if isinstance(series_id, (int, float)) and int(series_id) > 0:
                effective_series_id = int(series_id)
            else:
                effective_series_id = old_series_id

            # 保持 60 个采样点（如果是每天扫2次，则为30天数据）
            prices.append(float(price))
            sales_list.append(int(sales))
            if len(prices) > 60: prices.pop(0)
            if len(sales_list) > 60: sales_list.pop(0)

            cursor.execute('''
                INSERT OR REPLACE INTO item_history 
                (hash_name, series_id, price_series, sales_series, last_update)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, effective_series_id, json.dumps(prices), json.dumps(sales_list), int(time.time())))
            conn.commit()

    # --- 热门系列数据操作 ---

    def save_series_snapshot(self, s_id, s_name, recent_data, price_30):
        """保存板块宏观数据"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO series_history 
                (series_id, series_name, recent_15d_data, sell_price_30, last_update)
                VALUES (?, ?, ?, ?, ?)
            ''', (s_id, s_name, json.dumps(recent_data), price_30, int(time.time())))
            conn.commit()

    # --- 数据读取接口（用于策略分析） ---

    def get_item_analysis_data(self, name):
        """获取用于计算趋势强度的数据"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            # 关联查询：单品数据 + 所属板块的30日走势
            cursor.execute('''
                SELECT i.price_series, i.sales_series, s.sell_price_30, s.series_name
                FROM item_history i
                LEFT JOIN series_history s ON i.series_id = s.series_id
                WHERE i.hash_name = ?
            ''', (name,))
            row = cursor.fetchone()
            if row and row[0]:
                return {
                    "prices": json.loads(row[0]),
                    "sales": json.loads(row[1]),
                    "series_trend": row[2] if row[2] else 0,
                    "series_name": row[3]
                }
            return None
