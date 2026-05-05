"""
回测历史数据库 - 持久化保存回测历史，支持长期追踪和对比
"""

import sqlite3
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CONFIG


class BacktestDatabase:
    """回测历史数据库管理"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or CONFIG.get("BACKTEST_DB", 
                                              os.path.join(os.path.dirname(CONFIG["DB_NAME"]), "backtest_history.db"))
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 回测记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backtest_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            initial_balance REAL,
            final_balance REAL,
            total_profit REAL,
            total_return REAL,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            win_rate REAL,
            avg_profit REAL,
            max_profit_trade REAL,
            max_loss_trade REAL,
            avg_return REAL,
            best_return REAL,
            worst_return REAL,
            max_drawdown REAL,
            sharpe_ratio REAL,
            version TEXT,
            strategy_params TEXT,
            objective_score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("PRAGMA table_info(backtest_records)")
        record_columns = [row[1] for row in cursor.fetchall()]
        if "strategy_params" not in record_columns:
            cursor.execute("ALTER TABLE backtest_records ADD COLUMN strategy_params TEXT")
        if "objective_score" not in record_columns:
            cursor.execute("ALTER TABLE backtest_records ADD COLUMN objective_score REAL")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS optimization_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_time TEXT DEFAULT CURRENT_TIMESTAMP,
            optimizer_name TEXT,
            objective_name TEXT,
            search_space TEXT,
            best_params TEXT,
            best_score REAL,
            trials_count INTEGER,
            notes TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS optimization_trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            trial_no INTEGER,
            params TEXT,
            score REAL,
            total_return REAL,
            win_rate REAL,
            max_drawdown REAL,
            sharpe_ratio REAL,
            trades_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(run_id) REFERENCES optimization_runs(id)
        )
        """)
        
        # 单笔交易记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backtest_id INTEGER NOT NULL,
            name TEXT,
            buy_price REAL,
            sell_price REAL,
            net_profit REAL,
            profit_rate REAL,
            trade_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(backtest_id) REFERENCES backtest_records(id)
        )
        """)
        
        # 账户净值曲线表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_curves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backtest_id INTEGER NOT NULL,
            account_value REAL,
            sequence INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(backtest_id) REFERENCES backtest_records(id)
        )
        """)
        
        conn.commit()
        conn.close()
    
    def save_backtest(self, metrics, trades, account_values, version="002", strategy_params=None, objective_score=None):
        """保存完整回测记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        backtest_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 保存回测摘要
        cursor.execute("""
        INSERT INTO backtest_records (
            backtest_date, initial_balance, final_balance, total_profit, total_return,
            total_trades, winning_trades, losing_trades, win_rate,
            avg_profit, max_profit_trade, max_loss_trade,
            avg_return, best_return, worst_return, max_drawdown, sharpe_ratio, version,
            strategy_params, objective_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            backtest_date,
            metrics.get('initial_balance', 10000),
            metrics['final_balance'],
            metrics['total_profit'],
            metrics['total_return'],
            metrics['total_trades'],
            metrics['winning_trades'],
            metrics['losing_trades'],
            metrics['win_rate'],
            metrics['avg_profit'],
            metrics['max_profit_trade'],
            metrics['max_loss_trade'],
            metrics['avg_return'],
            metrics['best_return'],
            metrics['worst_return'],
            metrics['max_drawdown'],
            metrics['sharpe_ratio'],
            version,
            json.dumps(strategy_params or {}, ensure_ascii=False),
            objective_score,
        ))
        
        backtest_id = cursor.lastrowid

        def _normalize_trade_time(value):
            """Convert pandas/python datetime-like values to SQLite-friendly text."""
            if value is None:
                return None

            # pandas.Timestamp compatibility without importing pandas
            if hasattr(value, "to_pydatetime"):
                try:
                    value = value.to_pydatetime()
                except Exception:
                    pass

            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M:%S")

            # Fallback: store as text to avoid sqlite binding type errors
            return str(value)
        
        # 保存单笔交易
        for trade in trades:
            cursor.execute("""
            INSERT INTO trade_records (
                backtest_id, name, buy_price, sell_price, net_profit, profit_rate, trade_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                backtest_id,
                trade.get('name'),
                trade.get('buy_price'),
                trade.get('sell_price'),
                trade.get('net_profit'),
                trade.get('profit_rate'),
                _normalize_trade_time(trade.get('timestamp'))
            ))
        
        # 保存账户曲线
        for seq, value in enumerate(account_values):
            cursor.execute("""
            INSERT INTO account_curves (backtest_id, account_value, sequence)
            VALUES (?, ?, ?)
            """, (backtest_id, value, seq))
        
        conn.commit()
        conn.close()
        
        return backtest_id

    def save_optimization_run(self, optimizer_name, objective_name, search_space, best_params, best_score, trials_count, notes=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO optimization_runs (
            optimizer_name, objective_name, search_space,
            best_params, best_score, trials_count, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            optimizer_name,
            objective_name,
            json.dumps(search_space, ensure_ascii=False),
            json.dumps(best_params, ensure_ascii=False),
            best_score,
            trials_count,
            notes,
        ))
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return run_id

    def save_optimization_trial(self, run_id, trial_no, params, metrics, score):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO optimization_trials (
            run_id, trial_no, params, score, total_return,
            win_rate, max_drawdown, sharpe_ratio, trades_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            trial_no,
            json.dumps(params, ensure_ascii=False),
            score,
            metrics.get('total_return'),
            metrics.get('win_rate'),
            metrics.get('max_drawdown'),
            metrics.get('sharpe_ratio'),
            metrics.get('total_trades'),
        ))
        conn.commit()
        conn.close()
    
    def get_latest_backtest(self):
        """获取最新一次回测"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM backtest_records ORDER BY created_at DESC LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        columns = [
            'id', 'backtest_date', 'start_time', 'end_time', 'initial_balance',
            'final_balance', 'total_profit', 'total_return', 'total_trades',
            'winning_trades', 'losing_trades', 'win_rate', 'avg_profit',
            'max_profit_trade', 'max_loss_trade', 'avg_return', 'best_return',
            'worst_return', 'max_drawdown', 'sharpe_ratio', 'version', 'created_at'
        ]
        return dict(zip(columns, row))
    
    def get_backtest_history(self, limit=30):
        """获取回测历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT backtest_date, final_balance, total_profit, total_return, 
               total_trades, win_rate, max_drawdown, sharpe_ratio
        FROM backtest_records ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'backtest_date': row[0],
            'final_balance': row[1],
            'total_profit': row[2],
            'total_return': row[3],
            'total_trades': row[4],
            'win_rate': row[5],
            'max_drawdown': row[6],
            'sharpe_ratio': row[7]
        } for row in rows]
    
    def get_backtest_trades(self, backtest_id):
        """获取特定回测的所有交易"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT name, buy_price, sell_price, net_profit, profit_rate, trade_time
        FROM trade_records WHERE backtest_id = ? ORDER BY trade_time
        """, (backtest_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'name': row[0],
            'buy_price': row[1],
            'sell_price': row[2],
            'net_profit': row[3],
            'profit_rate': row[4],
            'trade_time': row[5]
        } for row in rows]
    
    def get_backtest_curve(self, backtest_id):
        """获取特定回测的账户净值曲线"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT account_value, sequence FROM account_curves 
        WHERE backtest_id = ? ORDER BY sequence
        """, (backtest_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def get_statistics(self, days=7):
        """获取回测统计（N天内）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
        SELECT COUNT(*) as count,
               AVG(total_return) as avg_return,
               AVG(win_rate) as avg_win_rate,
               AVG(max_drawdown) as avg_drawdown,
               SUM(total_profit) as total_profit
        FROM backtest_records 
        WHERE created_at >= datetime('now', '-{days} days')
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row or row[0] == 0:
            return None
        
        return {
            'count': row[0],
            'avg_return': row[1],
            'avg_win_rate': row[2],
            'avg_drawdown': row[3],
            'total_profit': row[4]
        }
