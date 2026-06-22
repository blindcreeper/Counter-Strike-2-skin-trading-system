"""Lightweight HTTP status server for remote monitoring.

Provides:
  GET /           - JSON status snapshot
  GET /health     - Simple health check (200 = alive)
  GET /heartbeat  - Last heartbeat timestamp

Runs in a daemon thread, does not block the main scan loop.
"""
import json
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler


class StatusHandler(BaseHTTPRequestHandler):
    stats = None  # set before server starts
    db = None     # set before server starts

    def do_GET(self):
        if self.path == "/health":
            self._json({"status": "alive", "time": datetime.now().isoformat()}, 200)
        elif self.path == "/heartbeat":
            snap = self.stats.get_snapshot() if self.stats else {}
            self._json({
                "last_heartbeat": snap.get("last_heartbeat"),
                "status": snap.get("status", "unknown"),
            })
        elif self.path == "/positions":
            self._serve_positions()
        elif self.path == "/trades":
            self._serve_trades()
        elif self.path == "/backtest" or self.path.startswith("/backtest"):
            self._serve_backtest()
        else:
            snap = self.stats.get_snapshot() if self.stats else {"status": "no_stats"}
            self._json(snap)

    def _serve_backtest(self):
        """Serve the latest HTML backtest report."""
        import os
        # Look in shared_data first (Docker shared volume), fall back to output/
        src_dir = os.path.dirname(os.path.abspath(__file__))
        for report_dir in [
            os.path.join(src_dir, "..", "shared_data", "backtest_reports"),
            os.path.join(src_dir, "..", "output", "backtest_reports"),
        ]:
            latest = os.path.join(os.path.abspath(report_dir), "latest.html")
            if os.path.exists(latest):
                break
        if not os.path.exists(latest):
            self._html("<h1 style='color:#94a3b8;text-align:center;margin-top:100px'>暂无回测报告</h1><p style='text-align:center;color:#475569'>运行回测后将自动生成</p>", 404)
            return
        try:
            with open(latest, "r", encoding="utf-8") as f:
                body = f.read()
            self._html(body, 200)
        except Exception as e:
            self._html(f"<h1>读取报告失败</h1><pre>{e}</pre>", 500)

    def _serve_positions(self):
        if not self.db:
            self._json({"error": "db not configured"}, 500)
            return
        import time, sqlite3 as sq3, os, sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from config import CONFIG
        now_ts = int(time.time())
        fee_rate = float(CONFIG.get("PLATFORM_FEE_RATE", CONFIG.get("FEE_RATE", 0.025)))
        initial_balance = float(CONFIG.get("INITIAL_BALANCE", 10000.0))

        conn = sq3.connect(self.db.db_name)
        cursor = conn.cursor()

        # Calculate realized PnL from all SELL executions
        cursor.execute("SELECT COALESCE(SUM(price * (1 - ?)), 0) FROM executions WHERE side='SELL'", (fee_rate,))
        total_sell_proceeds = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(price * (1 + ?)), 0) FROM executions WHERE side='BUY'", (fee_rate,))
        total_buy_cost = float(cursor.fetchone()[0])

        # Open positions: current value
        positions = self.db.get_all_open_positions()
        rows = []
        total_open_value = 0.0
        total_open_cost = 0.0
        for p in positions:
            hold_h = (now_ts - int(p["entry_time"])) / 3600
            entry = float(p["entry_price"])
            last = float(p["last_price"])
            cost_with_fee = entry * (1 + fee_rate)
            value_after_fee = last * (1 - fee_rate)
            pnl = value_after_fee - cost_with_fee
            pnl_pct = pnl / cost_with_fee * 100 if cost_with_fee > 0 else 0
            rows.append({
                "name": p["hash_name"],
                "buy_price": entry,
                "current_price": last,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 1),
                "hold_hours": round(hold_h, 0),
                "buy_time": datetime.fromtimestamp(int(p["entry_time"])).strftime("%m-%d %H:%M"),
            })
            total_open_value += value_after_fee
            total_open_cost += cost_with_fee
        conn.close()

        realized_pnl = total_sell_proceeds - total_buy_cost
        # Cash = initial - total buy cost (with fee) + total sell proceeds
        cash = initial_balance - total_buy_cost + total_sell_proceeds
        total_assets = cash + total_open_value
        total_return_pct = (total_assets - initial_balance) / initial_balance * 100

        self._json({
            "initial_balance": initial_balance,
            "cash": round(cash, 2),
            "open_positions_value": round(total_open_value, 2),
            "total_assets": round(total_assets, 2),
            "total_return_pct": round(total_return_pct, 1),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(total_open_value - total_open_cost, 2),
            "open_count": len(rows),
            "positions": rows,
        })

    def _serve_trades(self):
        if not self.db:
            self._json({"error": "db not configured"}, 500)
            return
        import sqlite3 as sq3
        conn = sq3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hash_name, side, exec_time, price, realized_return, reason
            FROM executions ORDER BY exec_time DESC LIMIT 30
        """)
        rows = []
        for r in cursor.fetchall():
            ret = r[4]
            rows.append({
                "name": r[0],
                "side": r[1],
                "time": datetime.fromtimestamp(int(r[2])).strftime("%m-%d %H:%M"),
                "price": r[3],
                "return_pct": round(ret * 100, 1) if ret is not None else None,
                "reason": r[5],
            })
        conn.close()
        self._json({"trades": rows})

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body, code=200):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # suppress access logs


def start_status_server(stats, host="0.0.0.0", port=8199, db=None):
    """Start the status HTTP server in a daemon thread."""
    StatusHandler.stats = stats
    StatusHandler.db = db
    server = HTTPServer((host, port), StatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[StatusServer] http://{host}:{port}/  (daemon thread)")
    return server
