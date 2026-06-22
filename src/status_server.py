"""Lightweight HTTP status server for remote monitoring.

Provides:
  GET /           - Real-time dashboard HTML
  GET /api/status - JSON status snapshot
  GET /health     - Simple health check (200 = alive)
  GET /heartbeat  - Last heartbeat timestamp
  GET /positions  - Portfolio JSON
  GET /trades     - Recent trades JSON
  GET /dashboard  - Position visualization page
  GET /backtest   - Latest HTML backtest report

Runs in a daemon thread, does not block the main scan loop.
"""
import json
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler


_DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CS2 实时仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f172a;color:#e2e8f0;padding:16px}
.container{max-width:800px;margin:0 auto}
h1{font-size:1.3rem;margin-bottom:16px;color:#f1f5f9;display:flex;align-items:center;gap:8px}
.status-dot{width:10px;height:10px;border-radius:50%;display:inline-block}
.dot-scanning{background:#22c55e;animation:pulse 1.5s infinite}
.dot-sleeping{background:#f59e0b}
.dot-stopped{background:#ef4444}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}

/* Progress */
.progress-wrap{background:#1e293b;border-radius:10px;padding:16px;margin-bottom:12px}
.progress-label{display:flex;justify-content:space-between;font-size:0.8rem;color:#94a3b8;margin-bottom:8px}
.progress-bar{height:8px;background:#334155;border-radius:4px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,#22c55e,#16a34a);border-radius:4px;transition:width .5s}

/* Cards */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px;margin-bottom:12px}
.card{background:#1e293b;border-radius:10px;padding:12px;text-align:center}
.card-label{display:block;font-size:0.7rem;color:#94a3b8;margin-bottom:4px}
.card-value{display:block;font-size:1.3rem;font-weight:700}
.buy-val{color:#22c55e}.hold-val{color:#94a3b8}.sell-val{color:#ef4444}.skip-val{color:#f59e0b}.err-val{color:#ef4444}

/* Lists */
.section{margin-bottom:12px}
.section-title{font-size:0.85rem;color:#94a3b8;margin-bottom:8px}
.list-card{background:#1e293b;border-radius:10px;overflow:hidden}
.list-item{display:flex;justify-content:space-between;padding:10px 14px;border-bottom:1px solid #1e293b;font-size:0.82rem}
.list-item:last-child{border-bottom:none}
.list-item:hover{background:#1e293b88}
.item-name{color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:50%}
.item-price{color:#94a3b8}.item-score{font-weight:600}
.empty{text-align:center;color:#475569;padding:20px;font-size:0.82rem}

/* Nav */
.nav{display:flex;gap:8px;margin-bottom:16px}
.nav a{color:#94a3b8;text-decoration:none;font-size:0.78rem;padding:6px 12px;border-radius:6px;background:#1e293b;transition:all .2s}
.nav a:hover,.nav a.active{color:#22c55e;background:#1e293b}

/* Footer */
.footer{text-align:center;color:#475569;margin-top:20px;font-size:0.7rem}

@media(max-width:480px){.cards{grid-template-columns:repeat(3,1fr)}.card-value{font-size:1rem}}
</style>
</head>
<body>
<div class="container">
<div class="nav">
  <a href="/" class="active">📡 仪表盘</a>
  <a href="/dashboard">💼 持仓</a>
  <a href="/backtest">📊 回测</a>
</div>

<h1>
  <span class="status-dot" id="dot"></span>
  <span id="statusText">-</span>
  <span style="font-size:0.7rem;color:#475569;font-weight:400" id="roundInfo"></span>
</h1>

<div class="progress-wrap">
  <div class="progress-label"><span id="batchLabel">批次 -/-</span><span id="seenLabel">已遍历 0</span></div>
  <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>
</div>

<div class="cards">
  <div class="card"><span class="card-label">已扫描</span><span class="card-value" id="scanned">0</span></div>
  <div class="card"><span class="card-label">BUY</span><span class="card-value buy-val" id="buys">0</span></div>
  <div class="card"><span class="card-label">HOLD</span><span class="card-value hold-val" id="holds">0</span></div>
  <div class="card"><span class="card-label">SELL</span><span class="card-value sell-val" id="sells">0</span></div>
  <div class="card"><span class="card-label">跳过</span><span class="card-value skip-val" id="skips">0</span></div>
  <div class="card"><span class="card-label">错误</span><span class="card-value err-val" id="errors">0</span></div>
</div>

<div class="section">
  <div class="section-title">💎 最近 BUY 信号</div>
  <div class="list-card" id="recentBuys"><div class="empty">暂无</div></div>
</div>

<div class="section">
  <div class="section-title">📋 最近扫描记录</div>
  <div class="list-card" id="recentItems"><div class="empty">暂无</div></div>
</div>

<p class="footer" id="updateTime">-</p>
</div>

<script>
const API = '/api/status';
function fmt(v){return v==null?'-':v}
function fetchData(){
  fetch(API).then(r=>r.json()).then(d=>{
    // Status dot
    const dot=document.getElementById('dot');
    dot.className='status-dot dot-'+(d.status||'idle');
    document.getElementById('statusText').textContent={
      scanning:'扫描中',sleeping:'休眠中',stopped:'已停止',idle:'空闲'
    }[d.status]||d.status||'-';
    document.getElementById('roundInfo').textContent=
      '第'+(d.round_count||0)+'轮 · 共'+fmt(d.total_items)+'商品';

    // Progress
    const batch=d.current_batch||0, totalB=d.total_batches||1;
    document.getElementById('batchLabel').textContent='批次 '+batch+'/'+totalB;
    document.getElementById('seenLabel').textContent='已遍历 '+(d.items_scanned||0);
    document.getElementById('progressFill').style.width=(totalB>0?batch/totalB*100:0)+'%';

    // Cards
    document.getElementById('scanned').textContent=fmt(d.items_scanned);
    document.getElementById('buys').textContent=fmt(d.buy_signals);
    document.getElementById('holds').textContent=fmt(d.hold_signals);
    document.getElementById('sells').textContent=fmt(d.sell_signals);
    const skips=(d.items_skipped_price||0)+(d.items_skipped_sales||0)+(d.items_skipped_min_price||0)+(d.items_skipped_blacklist||0)+(d.cooldown_skips||0)+(d.throttle_skips||0);
    document.getElementById('skips').textContent=skips;
    document.getElementById('errors').textContent=fmt(d.errors);

    // Recent BUYs
    const buys=d.recent_buy_signals||[];
    const bDiv=document.getElementById('recentBuys');
    if(buys.length){
      bDiv.innerHTML=buys.slice(0,5).map(b=>
        '<div class="list-item"><span class="item-name">'+(b.name||'?').substring(0,40)+'</span>'+
        '<span class="item-price">买¥'+(b.buy_price||0)+'</span>'+
        '<span class="item-score">分'+fmt(b.score)+'</span></div>'
      ).join('');
    }else{bDiv.innerHTML='<div class="empty">暂无</div>'}

    // Recent items
    const items=d.recent_items||[];
    const iDiv=document.getElementById('recentItems');
    if(items.length){
      iDiv.innerHTML=items.slice(0,10).map(i=>
        '<div class="list-item"><span class="item-name">'+(i.name||'?').substring(0,40)+'</span>'+
        '<span style="color:#94a3b8">'+i.action+'</span>'+
        '<span style="color:#64748b;font-size:0.75rem">'+(i.time||'')+'</span></div>'
      ).join('');
    }else{iDiv.innerHTML='<div class="empty">暂无</div>'}

    document.getElementById('updateTime').textContent='更新于 '+new Date().toLocaleTimeString('zh-CN');
  }).catch(()=>{});
}
fetchData();
setInterval(fetchData,10000);
</script>
</body>
</html>'''


_DASHBOARD_POSITIONS_HTML = r'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CS2 持仓面板</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f172a;color:#e2e8f0;padding:16px}
.container{max-width:800px;margin:0 auto}
h1{font-size:1.3rem;margin-bottom:16px;color:#f1f5f9}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:16px}
.card{background:#1e293b;border-radius:10px;padding:14px;text-align:center}
.card-label{display:block;font-size:0.7rem;color:#94a3b8;margin-bottom:4px}
.card-value{display:block;font-size:1.4rem;font-weight:700}
.return-big{font-size:2rem;font-weight:800;text-align:center;padding:12px;margin-bottom:8px}
.return-pos{color:#22c55e}.return-neg{color:#ef4444}

table{width:100%;border-collapse:collapse;font-size:0.82rem;background:#1e293b;border-radius:10px;overflow:hidden}
th{background:#334155;color:#94a3b8;font-weight:600;padding:10px 10px;text-align:left;white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid #0f172a}
tr:hover{background:#1e293b88}
tr.win{background:rgba(34,197,94,0.08)}
tr.loss{background:rgba(239,68,68,0.08)}
.num{text-align:right;font-variant-numeric:tabular-nums}

.nav{display:flex;gap:8px;margin-bottom:16px}
.nav a{color:#94a3b8;text-decoration:none;font-size:0.78rem;padding:6px 12px;border-radius:6px;background:#1e293b;transition:all .2s}
.nav a:hover,.nav a.active{color:#22c55e}
.footer{text-align:center;color:#475569;margin-top:20px;font-size:0.7rem}
.empty{text-align:center;color:#475569;padding:32px;font-size:0.85rem}

@media(max-width:480px){.cards{grid-template-columns:repeat(2,1fr)}.return-big{font-size:1.4rem}}
</style>
</head>
<body>
<div class="container">
<div class="nav">
  <a href="/">📡 仪表盘</a>
  <a href="/dashboard" class="active">💼 持仓</a>
  <a href="/backtest">📊 回测</a>
</div>

<h1>💼 持仓面板</h1>

<div class="cards" id="overviewCards"></div>
<div class="return-big" id="totalReturn"></div>

<div style="margin-bottom:8px;color:#94a3b8;font-size:0.8rem" id="posCount"></div>
<table id="posTable"><thead><tr>
  <th>商品</th><th class="num">买入价</th><th class="num">当前价</th><th class="num">盈亏%</th><th class="num">盈亏¥</th><th class="num">持仓</th><th>买入时间</th>
</tr></thead><tbody id="posBody"></tbody></table>

<p class="footer" id="updateTime">-</p>
</div>

<script>
function fetchData(){
  fetch('/positions').then(r=>r.json()).then(d=>{
    // Overview cards
    document.getElementById('overviewCards').innerHTML=
      '<div class="card"><span class="card-label">初始资金</span><span class="card-value">¥'+(d.initial_balance||0).toFixed(0)+'</span></div>'+
      '<div class="card"><span class="card-label">现金</span><span class="card-value">¥'+(d.cash||0).toFixed(0)+'</span></div>'+
      '<div class="card"><span class="card-label">持仓市值</span><span class="card-value">¥'+(d.open_positions_value||0).toFixed(0)+'</span></div>'+
      '<div class="card"><span class="card-label">总资产</span><span class="card-value">¥'+(d.total_assets||0).toFixed(0)+'</span></div>';

    // Big return number
    const ret=d.total_return_pct||0;
    const cls=ret>=0?'return-pos':'return-neg';
    document.getElementById('totalReturn').innerHTML=
      '<span class="'+cls+'">'+(ret>=0?'+':'')+ret.toFixed(1)+'%</span>';

    // Positions
    document.getElementById('posCount').textContent='持仓: '+(d.open_count||0)+' 个';
    const rows=d.positions||[];
    const tbody=document.getElementById('posBody');
    if(rows.length){
      tbody.innerHTML=rows.map(p=>{
        const pnlCls=p.pnl>=0?'win':'loss';
        return '<tr class="'+pnlCls+'"><td>'+(p.name||'?').substring(0,30)+'</td>'+
          '<td class="num">¥'+(p.buy_price||0).toFixed(1)+'</td>'+
          '<td class="num">¥'+(p.current_price||0).toFixed(1)+'</td>'+
          '<td class="num" style="color:'+(p.pnl_pct>=0?'#22c55e':'#ef4444')+'">'+(p.pnl_pct>=0?'+':'')+(p.pnl_pct||0).toFixed(1)+'%</td>'+
          '<td class="num">¥'+(p.pnl||0).toFixed(0)+'</td>'+
          '<td class="num">'+(p.hold_hours||0)+'h</td>'+
          '<td style="color:#64748b;font-size:0.75rem">'+(p.buy_time||'')+'</td></tr>';
      }).join('');
    }else{
      tbody.innerHTML='<tr><td colspan="7" class="empty">暂无持仓</td></tr>';
    }

    document.getElementById('updateTime').textContent='更新于 '+new Date().toLocaleTimeString('zh-CN');
  }).catch(()=>{});
}
fetchData();
setInterval(fetchData,30000);
</script>
</body>
</html>'''


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
        elif self.path == "/api/status":
            snap = self.stats.get_snapshot() if self.stats else {"status": "no_stats"}
            self._json(snap)
        elif self.path == "/positions":
            self._serve_positions()
        elif self.path == "/trades":
            self._serve_trades()
        elif self.path == "/dashboard":
            self._html(_DASHBOARD_POSITIONS_HTML, 200)
        elif self.path == "/backtest" or self.path.startswith("/backtest"):
            self._serve_backtest()
        elif self.path == "/" or self.path == "/index.html":
            self._html(_DASHBOARD_HTML, 200)
        else:
            snap = self.stats.get_snapshot() if self.stats else {"status": "no_stats"}
            self._json(snap)

    def _serve_backtest(self):
        """Serve the latest HTML backtest report."""
        import os
        src_dir = os.path.dirname(os.path.abspath(__file__))
        latest = None
        for report_dir in [
            os.path.join(src_dir, "..", "shared_data", "backtest_reports"),
            os.path.join(src_dir, "..", "output", "backtest_reports"),
        ]:
            candidate = os.path.join(os.path.abspath(report_dir), "latest.html")
            if os.path.exists(candidate):
                latest = candidate
                break
        if not latest or not os.path.exists(latest):
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
        import time, sqlite3 as sq3
        now_ts = int(time.time())
        fee_rate = 0.025
        initial_balance = 10000.0

        conn = sq3.connect(self.db.db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(SUM(price * (1 - ?)), 0) FROM executions WHERE side='SELL'", (fee_rate,))
        total_sell_proceeds = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(price * (1 + ?)), 0) FROM executions WHERE side='BUY'", (fee_rate,))
        total_buy_cost = float(cursor.fetchone()[0])

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
