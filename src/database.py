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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_events (
                    signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_time INTEGER,
                    hash_name TEXT,
                    action TEXT,
                    buy_price REAL,
                    sell_price REAL,
                    sales_24h INTEGER,
                    price_edge_rate REAL,
                    estimated_net_return REAL,
                    score REAL,
                    score1 REAL,
                    score2 REAL,
                    slope TEXT,
                    er REAL,
                    hurst REAL,
                    changes INTEGER,
                    series_id INTEGER,
                    signal_meta TEXT,
                    evaluation_status TEXT DEFAULT 'pending',
                    eval_due_24h INTEGER,
                    eval_due_72h INTEGER,
                    eval_due_168h INTEGER,
                    outcome_24h REAL,
                    outcome_72h REAL,
                    outcome_168h REAL,
                    max_return_24h REAL,
                    max_return_72h REAL,
                    max_return_168h REAL,
                    evaluated_at INTEGER,
                    simulated_sell_price REAL,
                    simulated_return REAL,
                    simulated_sell_time INTEGER
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash_name TEXT UNIQUE,
                    status TEXT,
                    quantity INTEGER,
                    entry_time INTEGER,
                    entry_price REAL,
                    last_price REAL,
                    last_mark_time INTEGER,
                    take_profit_rate REAL,
                    stop_loss_rate REAL,
                    max_holding_hours INTEGER,
                    signal_id INTEGER,
                    notes TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id INTEGER,
                    signal_id INTEGER,
                    hash_name TEXT,
                    side TEXT,
                    exec_time INTEGER,
                    price REAL,
                    quantity INTEGER,
                    gross_amount REAL,
                    fee_amount REAL,
                    net_amount REAL,
                    realized_return REAL,
                    reason TEXT,
                    execution_meta TEXT
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

    def record_signal_event(self, signal_data):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            now_ts = int(time.time())
            signal_time = int(signal_data.get("signal_time", now_ts))
            cursor.execute('''
                INSERT INTO signal_events (
                    signal_time, hash_name, action, buy_price, sell_price,
                    sales_24h, price_edge_rate, estimated_net_return,
                    score, score1, score2, slope, er, hurst, changes,
                    series_id, signal_meta, eval_due_24h, eval_due_72h,
                    eval_due_168h
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_time,
                signal_data.get("hash_name"),
                signal_data.get("action"),
                signal_data.get("buy_price"),
                signal_data.get("sell_price"),
                signal_data.get("sales_24h"),
                signal_data.get("price_edge_rate"),
                signal_data.get("estimated_net_return"),
                signal_data.get("score"),
                signal_data.get("score1"),
                signal_data.get("score2"),
                signal_data.get("slope"),
                signal_data.get("er"),
                signal_data.get("hurst"),
                signal_data.get("changes"),
                signal_data.get("series_id"),
                json.dumps(signal_data.get("signal_meta", {}), ensure_ascii=False),
                signal_time + 24 * 3600,
                signal_time + 72 * 3600,
                signal_time + 168 * 3600,
            ))
            conn.commit()
            return cursor.lastrowid

    def upsert_position(self, position_data):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO positions (
                    hash_name, status, quantity, entry_time, entry_price,
                    last_price, last_mark_time, take_profit_rate,
                    stop_loss_rate, max_holding_hours, signal_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hash_name) DO UPDATE SET
                    status=excluded.status,
                    quantity=excluded.quantity,
                    entry_time=excluded.entry_time,
                    entry_price=excluded.entry_price,
                    last_price=excluded.last_price,
                    last_mark_time=excluded.last_mark_time,
                    take_profit_rate=excluded.take_profit_rate,
                    stop_loss_rate=excluded.stop_loss_rate,
                    max_holding_hours=excluded.max_holding_hours,
                    signal_id=excluded.signal_id,
                    notes=excluded.notes
            ''', (
                position_data.get("hash_name"),
                position_data.get("status", "OPEN"),
                position_data.get("quantity", 1),
                position_data.get("entry_time"),
                position_data.get("entry_price"),
                position_data.get("last_price"),
                position_data.get("last_mark_time"),
                position_data.get("take_profit_rate"),
                position_data.get("stop_loss_rate"),
                position_data.get("max_holding_hours"),
                position_data.get("signal_id"),
                position_data.get("notes"),
            ))
            conn.commit()

    def get_open_position(self, name):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT position_id, hash_name, status, quantity, entry_time,
                       entry_price, last_price, last_mark_time,
                       take_profit_rate, stop_loss_rate, max_holding_hours,
                       signal_id, notes
                FROM positions
                WHERE hash_name = ? AND status = 'OPEN'
            ''', (name,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "position_id": row[0],
                "hash_name": row[1],
                "status": row[2],
                "quantity": row[3],
                "entry_time": row[4],
                "entry_price": row[5],
                "last_price": row[6],
                "last_mark_time": row[7],
                "take_profit_rate": row[8],
                "stop_loss_rate": row[9],
                "max_holding_hours": row[10],
                "signal_id": row[11],
                "notes": row[12],
            }

    def close_position(self, name, exit_price, exit_time, note=""):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE positions
                SET status = 'CLOSED', last_price = ?, last_mark_time = ?, notes = ?
                WHERE hash_name = ? AND status = 'OPEN'
            ''', (exit_price, exit_time, note, name))
            conn.commit()

    def record_execution(self, execution_data):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO executions (
                    position_id, signal_id, hash_name, side, exec_time,
                    price, quantity, gross_amount, fee_amount, net_amount,
                    realized_return, reason, execution_meta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                execution_data.get("position_id"),
                execution_data.get("signal_id"),
                execution_data.get("hash_name"),
                execution_data.get("side"),
                execution_data.get("exec_time"),
                execution_data.get("price"),
                execution_data.get("quantity"),
                execution_data.get("gross_amount"),
                execution_data.get("fee_amount"),
                execution_data.get("net_amount"),
                execution_data.get("realized_return"),
                execution_data.get("reason"),
                json.dumps(execution_data.get("execution_meta", {}), ensure_ascii=False),
            ))
            conn.commit()

    def get_pending_signal_evaluations(self, now_ts=None):
        now_ts = int(now_ts or time.time())
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT signal_id, signal_time, hash_name, buy_price,
                       outcome_24h, outcome_72h, outcome_168h
                FROM signal_events
                WHERE evaluation_status = 'pending'
                  AND eval_due_24h <= ?
            ''', (now_ts,))
            rows = cursor.fetchall()
            return [
                {
                    "signal_id": row[0],
                    "signal_time": row[1],
                    "hash_name": row[2],
                    "buy_price": row[3],
                    "outcome_24h": row[4],
                    "outcome_72h": row[5],
                    "outcome_168h": row[6],
                }
                for row in rows
            ]

    def update_signal_evaluation(self, signal_id, evaluation_data):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE signal_events
                SET outcome_24h = COALESCE(?, outcome_24h),
                    outcome_72h = COALESCE(?, outcome_72h),
                    outcome_168h = COALESCE(?, outcome_168h),
                    max_return_24h = COALESCE(?, max_return_24h),
                    max_return_72h = COALESCE(?, max_return_72h),
                    max_return_168h = COALESCE(?, max_return_168h),
                    evaluated_at = ?,
                    evaluation_status = ?
                WHERE signal_id = ?
            ''', (
                evaluation_data.get("outcome_24h"),
                evaluation_data.get("outcome_72h"),
                evaluation_data.get("outcome_168h"),
                evaluation_data.get("max_return_24h"),
                evaluation_data.get("max_return_72h"),
                evaluation_data.get("max_return_168h"),
                int(time.time()),
                evaluation_data.get("evaluation_status", "completed"),
                signal_id,
            ))
            conn.commit()

    def get_signal_events(self, action=None, min_signal_time=None):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM signal_events WHERE 1=1"
            params = []
            if action:
                query += " AND action = ?"
                params.append(action)
            if min_signal_time:
                query += " AND signal_time >= ?"
                params.append(int(min_signal_time))
            query += " ORDER BY signal_time DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_open_positions(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT position_id, hash_name, status, quantity, entry_time,
                       entry_price, last_price, last_mark_time,
                       take_profit_rate, stop_loss_rate, max_holding_hours,
                       signal_id, notes
                FROM positions WHERE status = 'OPEN'
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def update_signal_simulated_sell(self, signal_id, sell_price, simulated_return, sell_time):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE signal_events
                SET simulated_sell_price = ?,
                    simulated_return = ?,
                    simulated_sell_time = ?
                WHERE signal_id = ?
            ''', (sell_price, simulated_return, sell_time, signal_id))
            conn.commit()

    def ensure_simulated_sell_columns(self):
        """Add simulated sell columns if missing."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(signal_events)")
            existing = {row[1] for row in cursor.fetchall()}
            if "simulated_sell_price" not in existing:
                cursor.execute("ALTER TABLE signal_events ADD COLUMN simulated_sell_price REAL")
            if "simulated_return" not in existing:
                cursor.execute("ALTER TABLE signal_events ADD COLUMN simulated_return REAL")
            if "simulated_sell_time" not in existing:
                cursor.execute("ALTER TABLE signal_events ADD COLUMN simulated_sell_time INTEGER")
            conn.commit()
