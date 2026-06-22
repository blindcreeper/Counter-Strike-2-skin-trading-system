"""Generate standalone HTML backtest report with SVG charts."""
import json
import os
from datetime import datetime


def _sparkline_svg(values, width=300, height=60):
    """Render equity curve as SVG polyline."""
    if not values or len(values) < 2:
        return '<p style="color:#888">暂无净值数据</p>'

    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1
    n = len(values)
    step = max(1, n // width)
    pts = []
    for i in range(0, n, step if step > 1 else 1):
        chunk = values[i: min(i + step, n)]
        avg = sum(chunk) / len(chunk)
        pts.append(avg)
    pts = pts[:width]

    # Scale to SVG coords
    pad = 5
    h = height - pad * 2
    w = width
    x_step = (w - pad) / max(len(pts) - 1, 1)

    points = []
    for i, v in enumerate(pts):
        x = pad + i * x_step
        y = pad + h - ((v - mn) / rng * h)
        points.append(f"{x:.1f},{y:.1f}")

    poly = " ".join(points)

    # Fill area
    fill_pts = f"{pad},{height - pad} " + " ".join(points) + f" {w - pad},{height - pad}"

    # Determine color
    trend_color = "#22c55e" if pts[-1] >= pts[0] else "#ef4444"

    return f'''<svg width="{width}" height="{height}" style="max-width:100%">
  <defs>
    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{trend_color}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="{trend_color}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <polygon points="{fill_pts}" fill="url(#eqGrad)"/>
  <polyline points="{poly}" fill="none" stroke="{trend_color}" stroke-width="2" stroke-linejoin="round"/>
</svg>'''


def _trade_table(trades):
    """Render trade records as HTML table."""
    if not trades:
        return '<p style="color:#888">暂无交易</p>'

    rows = []
    for t in trades[:100]:
        name = str(t.get("name", "?"))[:40]
        bp = float(t.get("buy_price", 0) or 0)
        sp = float(t.get("sell_price", 0) or 0)
        pr = float(t.get("profit_rate", 0) or 0)
        np_ = float(t.get("net_profit", 0) or 0)
        hh = t.get("holding_hours", "-")
        hold = f"{hh:.0f}h" if isinstance(hh, (int, float)) else str(hh)
        cls = "win" if pr > 0 else "loss"
        em = "▲" if pr > 0 else "▼"
        rows.append(
            f'<tr class="{cls}"><td>{em}</td>'
            f'<td>{name}</td>'
            f'<td class="num">¥{bp:.1f}</td><td class="num">¥{sp:.1f}</td>'
            f'<td class="num">{pr:+.1%}</td><td class="num">¥{np_:+.1f}</td>'
            f'<td class="num">{hold}</td></tr>'
        )

    return f'''<table>
<thead><tr>
  <th></th><th>商品</th><th class="num">买入</th><th class="num">卖出</th>
  <th class="num">收益率</th><th class="num">利润</th><th class="num">持仓</th>
</tr></thead>
<tbody>{"".join(rows)}</tbody></table>'''


def _trend_table(history):
    """Render recent backtest history comparison."""
    if not history or len(history) < 2:
        return ""

    rows = []
    for r in history:
        ret = r.get("total_return", 0)
        wr = r.get("win_rate", 0)
        dd = r.get("max_drawdown", 0)
        date = str(r.get("backtest_date", "?"))[:10]
        cls = "win" if ret > 0 else "loss"
        rows.append(
            f'<tr class="{cls}"><td>{date}</td>'
            f'<td class="num">{ret:+.1%}</td><td class="num">{wr:.0%}</td>'
            f'<td class="num">{dd:.1%}</td><td class="num">{r.get("total_trades", 0)}</td>'
            f'<td class="num">{r.get("sharpe_ratio", 0):.2f}</td></tr>'
        )

    return f'''<h3>🆚 历史趋势</h3>
<table>
<thead><tr>
  <th>日期</th><th class="num">收益</th><th class="num">胜率</th>
  <th class="num">回撤</th><th class="num">笔数</th><th class="num">夏普</th>
</tr></thead>
<tbody>{"".join(rows)}</tbody></table>'''


def _metric_card(label, value, color=""):
    style = f'style="color:{color}"' if color else ""
    return f'<div class="card"><span class="card-label">{label}</span><span class="card-value" {style}>{value}</span></div>'


def _histogram_svg(trades, width=600, height=160):
    """Render profit distribution histogram as SVG."""
    if not trades:
        return '<p style="color:#888;text-align:center">暂无交易数据</p>'

    # Bin from -30% to +30%, step 5%
    bins = []
    for i in range(-30, 30, 5):
        bins.append((i / 100, (i + 5) / 100))
    bin_labels = [f"{b[0]:+.0%}" for b in bins]
    bin_counts = [0] * len(bins)

    for t in trades:
        pr = float(t.get("profit_rate", 0) or 0)
        for idx, (lo, hi) in enumerate(bins):
            if lo <= pr < hi:
                bin_counts[idx] += 1
                break

    max_count = max(bin_counts) if max(bin_counts) > 0 else 1
    bar_w = (width - 60) / len(bins)
    pad_l, pad_b, pad_t = 40, 20, 25
    h = height - pad_b - pad_t

    bars = []
    for i, count in enumerate(bin_counts):
        x = pad_l + i * bar_w + 2
        bar_h = (count / max_count) * h if count > 0 else 1
        y = height - pad_b - bar_h
        color = "#22c55e" if bins[i][0] >= 0 else "#ef4444"
        label = str(count) if count > 0 else ""
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 4:.1f}" height="{bar_h:.1f}" '
            f'fill="{color}" rx="2" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2 - 2:.1f}" y="{y - 4:.1f}" '
            f'text-anchor="middle" fill="#94a3b8" font-size="9">{label}</text>'
        )
        # X-axis label
        bars.append(
            f'<text x="{x + bar_w / 2 - 2:.1f}" y="{height - 2:.1f}" '
            f'text-anchor="middle" fill="#64748b" font-size="8">{bin_labels[i]}</text>'
        )

    return f'''<svg width="{width}" height="{height}" style="max-width:100%">
  <line x1="{pad_l}" y1="{height - pad_b}" x2="{width - 20}" y2="{height - pad_b}" stroke="#334155" stroke-width="1"/>
  {"".join(bars)}
</svg>'''


def _donut_svg(trades, size=160):
    """Render close reason donut chart as SVG ring."""
    if not trades:
        return '<p style="color:#888;text-align:center">暂无交易</p>'

    reasons = {}
    for t in trades:
        r = str(t.get("close_reason", "timeout"))
        reasons[r] = reasons.get(r, 0) + 1

    colors = {"take_profit": "#22c55e", "stop_loss": "#ef4444", "timeout": "#6b7280"}
    names = {"take_profit": "止盈", "stop_loss": "止损", "timeout": "超时"}
    total = sum(reasons.values())

    cx, cy = size / 2, size / 2
    r = 55
    sw = 18
    circ = 2 * 3.14159 * r

    segments = []
    offset = 0
    for key in ["take_profit", "stop_loss", "timeout"]:
        count = reasons.get(key, 0)
        if count == 0:
            continue
        pct = count / total
        dash_len = circ * pct
        gap = circ - dash_len
        color = colors.get(key, "#888")
        segments.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-dasharray="{dash_len:.1f} {gap:.1f}" '
            f'stroke-dashoffset="-{offset:.1f}" stroke-linecap="butt" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += dash_len

    # Legend
    legend = []
    ly = cy + r + sw + 16
    lx_start = cx - 100
    for i, key in enumerate(["take_profit", "stop_loss", "timeout"]):
        count = reasons.get(key, 0)
        if count == 0:
            continue
        lx = lx_start + i * 68
        legend.append(
            f'<circle cx="{lx}" cy="{ly}" r="5" fill="{colors[key]}"/>'
            f'<text x="{lx + 8}" y="{ly + 4}" fill="#94a3b8" font-size="10">'
            f'{names[key]} {count}笔 {count / total:.0%}</text>'
        )

    return f'''<svg width="{size}" height="{size + 40}" style="max-width:100%" viewBox="0 0 {size} {size + 40}">
  {"".join(segments)}
  {"".join(legend)}
</svg>'''


def generate_html(metrics, trades=None, history=None, title=None):
    """Generate complete standalone HTML report."""
    trades = trades or []
    history = history or []
    title = title or f"CS2 回测报告 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    ret = metrics.get("total_return", 0)
    wr = metrics.get("win_rate", 0)
    dd = metrics.get("max_drawdown", 0)
    sharpe = metrics.get("sharpe_ratio", 0)

    ret_color = "#22c55e" if ret > 0 else "#ef4444"
    wr_color = "#22c55e" if wr > 0.5 else ("#f59e0b" if wr > 0.4 else "#ef4444")
    sparkline = _sparkline_svg(metrics.get("account_values", []), width=600, height=100)
    histogram = _histogram_svg(trades, width=600, height=160)
    donut = _donut_svg(trades, size=200)
    trade_html = _trade_table(trades)
    trend_html = _trend_table(history)

    # Conclusion
    if metrics.get("total_trades", 0) == 0:
        conclusion = "本期无交易记录"
        con_color = "#888"
    elif ret > 0.05:
        conclusion = "策略表现良好 ✅"
        con_color = "#22c55e"
    elif ret > 0:
        conclusion = "小幅盈利，胜率偏低 🟡"
        con_color = "#f59e0b"
    elif ret > -0.05:
        conclusion = "小幅亏损，关注回撤 🟠"
        con_color = "#f59e0b"
    else:
        conclusion = "亏损严重，建议暂停开仓 🔴"
        con_color = "#ef4444"

    html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       background:#0f172a; color:#e2e8f0; padding:24px; }}
.container {{ max-width:860px; margin:0 auto; }}
h1 {{ font-size:1.5rem; margin-bottom:20px; color:#f1f5f9; }}
h3 {{ font-size:1rem; margin:24px 0 12px; color:#94a3b8; }}

/* Metric cards */
.cards {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:12px; margin-bottom:24px; }}
.card {{ background:#1e293b; border-radius:10px; padding:16px; text-align:center; }}
.card-label {{ display:block; font-size:0.75rem; color:#94a3b8; margin-bottom:4px; }}
.card-value {{ display:block; font-size:1.5rem; font-weight:700; }}

/* Chart */
.chart {{ background:#1e293b; border-radius:10px; padding:20px; margin-bottom:12px; text-align:center; }}

/* Conclusion */
.conclusion {{ background:#1e293b; border-radius:10px; padding:16px; margin-bottom:24px;
              border-left:4px solid {con_color}; font-size:0.95rem; }}
.conclusion b {{ color:{con_color}; }}

/* Table */
table {{ width:100%; border-collapse:collapse; font-size:0.85rem; background:#1e293b; border-radius:10px; overflow:hidden; }}
th {{ background:#334155; color:#94a3b8; font-weight:600; padding:10px 12px; text-align:left; white-space:nowrap; }}
td {{ padding:8px 12px; border-bottom:1px solid #1e293b; }}
tr:hover {{ background:#1e293b88; }}
tr.win {{ border-left:3px solid #22c55e; }}
tr.loss {{ border-left:3px solid #ef4444; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}

/* Responsive */
@media (max-width:640px) {{
  body {{ padding:12px; }}
  .cards {{ grid-template-columns:repeat(2, 1fr); }}
  table {{ font-size:0.75rem; }}
  th, td {{ padding:6px 8px; }}
}}
</style>
</head>
<body>
<div class="container">

<h1>📊 {title}</h1>

<div class="cards">
  {_metric_card("初始资金", f"¥{metrics.get('initial_balance', 10000):.0f}")}
  {_metric_card("最终资金", f"¥{metrics['final_balance']:.0f}")}
  {_metric_card("总收益", f"¥{metrics['total_profit']:+.0f} ({ret:+.1%})", ret_color)}
  {_metric_card("胜率", f"{wr:.0%} ({metrics.get('winning_trades', 0)}赢/{metrics.get('losing_trades', 0)}亏)", wr_color)}
  {_metric_card("最大回撤", f"{dd:.1%}")}
  {_metric_card("夏普比率", f"{sharpe:.2f}")}
</div>

<div class="conclusion"><b>💡 结论:</b> {conclusion}</div>

<h3>📈 净值曲线</h3>
<div class="chart">{sparkline}</div>

<h3>📊 收益分布</h3>
<div class="chart">{histogram}</div>

<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px">
  <div style="flex:1;min-width:180px">
    <h3>🎯 平仓原因</h3>
    <div class="chart">{donut}</div>
  </div>
</div>

<h3>📦 交易明细 (最近100笔)</h3>
{trade_html}

{trend_html}

<p style="text-align:center;color:#475569;margin-top:32px;font-size:0.8rem;">
  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | CS2 Quant System
</p>

</div>
</body>
</html>'''

    return html


def save_report(html, output_dir=None):
    """Save HTML report and return path."""
    if output_dir is None:
        # Docker: use shared_data so both scanner (status_server) and scheduler can access
        shared = os.environ.get("SHARED_DATA_DIR", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "shared_data"
        ))
        output_dir = os.path.join(shared, "backtest_reports")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"backtest_{timestamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    latest = os.path.join(output_dir, "latest.html")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(html)
    return path, latest
