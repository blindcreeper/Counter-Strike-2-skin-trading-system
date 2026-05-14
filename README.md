# CS2 皮肤趋势预测交易系统

> 基于 SteamDT 日K数据(365天)的多因子趋势预测，自动产生 BUY 信号，模拟交易验证策略，7天锁仓期后虚拟卖出，钉钉实时推送。

---

## 系统做什么

CS2 游戏皮肤在不同交易平台上有不同售价，且所有平台买入后有 7 天锁仓期。本系统利用历史日K数据预测 7 天价格趋势，买入看涨商品，7 天后卖出验证收益。

**数据流：**

```
SteamDT K线 API（365天日K） + CSQAQ API（悠悠/Buff 双边报价）
  → 扫描器每轮遍历 2000+ 商品
    → 价格/销量过滤
      → 日K趋势评分（8因子模型）+ 多因子综合评分
        → BUY 信号 → 模拟开仓（记录入场价/时间）
          → 钉钉推送 BUY 提醒
          → 每轮扫描更新持仓价格
            → 7天锁仓到期后自动虚拟卖出
              → 计算收益，记录完整交易流水
```

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 趋势预测 | 基于 SteamDT 365天日K数据，8因子模型计算趋势评分(-100~+100) |
| 动态平台选择 | 自动比较悠悠/Buff 价格，买入更便宜的平台 |
| 多因子评分 | 动量 + 跨平台价差 + 平台对 + 关键词 + 价格区间 |
| 模拟交易 | 虚拟开仓/平仓，7天锁仓期后自动卖出，记录完整交易流水 |
| 持仓管理 | 止盈(+8%)/止损(-5%)/超时平仓，实时追踪浮动盈亏 |
| 状态监控 | HTTP API 暴露持仓、资金、交易记录（端口 8199） |
| 钉钉通知 | BUY 信号 + 虚拟卖出结算 + 扫描报告 + 异常告警 |
| Docker 部署 | scanner + scheduler 双容器，共享数据卷，一键部署 |

---

## 趋势预测模型

### 8因子模型（predict_7d_trend）

基于 SteamDT 365天日K收盘价，每个因子映射到分数区间，总分 -100~+100：

| 因子 | 计算方式 | 权重范围 | 逻辑 |
|------|---------|---------|------|
| 短期动量 | 近10日 slope | -25~+25 | 2.5周趋势方向 |
| 中期动量 | 近30日 slope | -25~+25 | 1个月趋势方向 |
| 动量加速度 | 10日slope - 30日slope | -15~+15 | 趋势加强/减弱 |
| MA20偏离 | price vs MA20 | -15~+15 | 短中期位置 |
| MA60偏离 | price vs MA60 | -10~+10 | 中长期位置 |
| 波动率 | 近20日收益率标准差 | -10~+10 | 低波动=稳定趋势 |
| 价格位置 | 近30日高低百分位 | -15~+15 | 接近新高=强势 |
| MA交叉 | MA5 vs MA20 | -10~+10 | 金叉/死叉信号 |

### 信号判断

| 信号 | 条件 |
|------|------|
| **BUY** | 趋势评分 ≥ 50 且通过数据驱动过滤（slope/MA10/价格） |
| **SELL** | 价格跌破 MA10（持仓中） |
| **HOLD** | 趋势不足，继续观察 |
| **WAIT** | 历史数据不足，积累中 |

### 数据驱动过滤（基于 1317 商品回测分析）

1. **slope ≥ 阈值**（区分度 0.92，最关键指标）
2. **价格在 MA10 上方**（区分度 0.80）
3. **低价品优先**（涨组 75% 在 ¥446 以下）

---

## 模拟交易

### 交易生命周期

```
BUY 信号 → 模拟开仓（记录入场价/时间，选最便宜平台买入）
  → 每轮扫描更新最新价格
    → 触发条件之一则虚拟卖出：
      ├── 止盈：净收益率 ≥ 8%
      ├── 止损：净收益率 ≤ -5%
      └── 超时：持仓 ≥ 168小时（7天锁仓期）
```

### 费率模型

- 买入手续费：2.5%
- 卖出手续费：2.5%
- 净收益 = 涨幅 - 5%（双边手续费）

### 监控端点

```bash
curl http://<VPS_IP>:8199/positions   # 持仓 + 资金概况（初始资金/现金/持仓市值/总资产/收益率）
curl http://<VPS_IP>:8199/trades      # 最近 30 笔交易记录
curl http://<VPS_IP>:8199/            # 扫描状态
curl http://<VPS_IP>:8199/health      # 健康检查
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/blindcreeper/Counter-Strike-2-skin-trading-system.git
cd Counter-Strike-2-skin-trading-system
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config/app_config.example.json config/app_config.json
```

Edit `config/app_config.json`：

| 配置项 | 说明 | 申请地址 |
|--------|------|---------|
| `sdt_key` | SteamDT API Key | https://open.steamdt.com |
| `csqaq_token` | CSQAQ ApiToken | https://api.csqaq.com |

环境变量 `SDT_KEY`、`CSQAQ_TOKEN`、`DINGTALK_WEBHOOK` 优先级高于配置文件。

### 3. Run

```bash
# 启动扫描器
python src/main.py

# Docker 一键部署
docker compose up -d --build
```

### 4. Monitor

```bash
curl http://localhost:8199/positions
curl http://localhost:8199/trades
docker compose logs -f scanner
```

---

## 项目结构

```
├── config/
│   ├── config.py              # 核心配置（API key/阈值/路径）
│   └── app_config.json        # JSON 配置（策略参数/模式/钉钉 webhook）
│
├── src/
│   ├── main.py                # 扫描器唯一入口（collect/trade 双模式）
│   ├── api_client.py          # SteamDT / CSQAQ API 封装（含 kline）
│   ├── strategy.py            # 趋势预测引擎（8因子模型 + 多因子评分）
│   ├── database.py            # MarketDB（SQLite：价格历史/信号/持仓/交易）
│   ├── execution_engine.py    # 模拟交易引擎（开仓/止盈止损/7天卖出）
│   ├── scan_stats.py          # 线程安全扫描统计
│   ├── status_server.py       # HTTP 状态 API（/positions /trades /health）
│   └── dingtalk_notify.py     # 钉钉通知（BUY/卖出结算/扫描报告/异常）
│
├── scripts/
│   └── data_analysis.py       # 数据规律分析脚本（collect 模式数据分析）
│
├── data/
│   └── csqaq_id_map.json      # 商品名映射表
│
├── docker-compose.yml         # 双容器编排
├── Dockerfile                 # Python 3.11-slim
├── entrypoint.sh              # Docker 入口脚本
└── requirements.txt
```

---

## 运行模式

### collect 模式（数据采集）

跳过所有策略过滤，广撒网记录所有商品的评分数据，用于积累分析数据，找到有效因子阈值。

### trade 模式（趋势交易）

完整策略流程：过滤 → 日K趋势评分 → BUY 信号 → 模拟交易。

在 `app_config.json` 中设置 `"mode": "collect"` 或 `"mode": "trade"`。

---

## 配置说明

### config/app_config.json

```json
{
  "mode": "trade",
  "api": {
    "sdt_key": "你的 SteamDT API Key",
    "csqaq_token": "你的 CSQAQ ApiToken"
  },
  "strategy": {
    "TREND_SCORE_THRESHOLD": 50,
    "HOLDING_PERIOD_HOURS": 168,
    "TAKE_PROFIT_RATE": 0.08,
    "STOP_LOSS_RATE": -0.05
  }
}
```

### 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TREND_SCORE_THRESHOLD` | 50 | 趋势评分 BUY 门槛（-100~+100） |
| `HOLDING_PERIOD_HOURS` | 168 | 锁仓期（小时），7天=168h |
| `TAKE_PROFIT_RATE` | 0.08 | 止盈线（净收益率） |
| `STOP_LOSS_RATE` | -0.05 | 止损线（净收益率） |
| `BUY_SCORE_THRESHOLD` | 28 | 综合分门槛 |
| `MAX_PRICE` | 6000 | 最高买入价 |
| `MIN_SALES_24H` | 40 | Buff 24h 最低销量 |

---

## API 数据源

| 数据源 | API | 提供内容 |
|--------|-----|---------|
| SteamDT | `open.steamdt.com` | 365天日K数据(OHLC)、批量价格查询 |
| CSQAQ | `api.csqaq.com` | 悠悠/Buff 双边报价 + 24h 销量 |

---

## 依赖

```
pandas>=1.3.0
numpy>=1.21.0
requests>=2.26.0
schedule>=1.1.0
```
