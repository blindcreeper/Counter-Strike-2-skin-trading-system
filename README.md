# CS2 皮肤跨平台量化套利系统

> 实时扫描悠悠有品 / Buff / HaloSkins 等平台价差，多因子策略评分，自动产生 BUY 信号，虚拟资金回测验证策略，钉钉实时推送。

---

## 系统做什么

CS2 游戏皮肤在不同交易平台上的售价存在差异。本系统持续监控这些价差，用量化策略评分后自动发现套利机会，并通过虚拟回测验证策略表现。

**完整数据流：**

```
CSQAQ API（悠悠有品 + Buff 双边报价）
  → 扫描器每轮遍历 2000+ 商品
    → 价格/销量/价差过滤
      → 多因子策略评分（动量 + 价差 + 平台对 + 关键词）
        → BUY 信号写入 CSV + 数据库记录持仓
          → 钉钉即时推送 BUY 提醒
          → 定时回测引擎读取信号，用实时价格模拟卖出
            → 生成收益/胜率/夏普比率等指标
              → 钉钉推送回测报告
```

---

## 核心功能一览

| 功能 | 说明 |
|------|------|
| 实时扫描 | VPS 24h 运行，每轮遍历 2000+ CS2 皮肤，获取悠悠有品买入价 + Buff 卖出价 |
| 多因子策略 | 动量（斜率/效率比/Hurst 指数/价格变化频率）+ 跨平台价差 + 平台对权重 + 关键词权重 + 价格区间 |
| 持仓管理 | 自动开仓、止盈/止损/超时平仓，记录完整交易流水 |
| 信号评估 | 追踪每个 BUY 信号在 24h/72h/168h 后的实际收益，计算策略真实命中率 |
| 定时回测 | 每天 22:00 自动用 API 实时价格回测历史 BUY 信号，计算真实盈亏 |
| 参数自调优 | 每周日自动搜索更优策略参数，8 天后自动应用（确保稳定性） |
| 钉钉通知 | BUY 信号即时推送 + 每轮扫描报告 + 回测报告 + 异常告警 |
| 状态监控 | HTTP API 暴露实时扫描状态（端口 8199），支持健康检查 |
| Docker 部署 | scanner + scheduler 双容器，共享数据卷，一键部署 |

---

## 策略详情

### 评分模型

每个通过初筛的商品会得到两个分数：

**Score1（动量分，权重 0.65）：**
- 价格斜率（10 期线性回归斜率）
- 效率比（总变化 / 波动之和，越高趋势越纯）
- Hurst 指数（R/S 分析法，衡量价格持续性）
- 价格变化频率（过高 = 噪声，过低 = 停滞）

**Score2（综合分，权重 1.0）：**
- 动量分 × 0.65
- 跨平台价差分 × 1.15（5% 以上开始得分，8% 以上高分）
- 平台对分 × 0.75（悠悠→Buff 最优，C5→HaloSkins 最差）
- 价格区间分 × 0.35（低价品加分，高价品减分）
- 关键词分 × 0.6（MAC-10/Knife 加分，Gloves/USP 减分）

### 信号判断

| 信号 | 条件 |
|------|------|
| **BUY** | 安全垫（扣除双边手续费后净收益率）≥ 阈值 且 综合分 ≥ 28 |
| **SELL** | 当前价跌破 MA10（持仓中） |
| **HOLD** | 安全垫不足或综合分不够，继续观察 |
| **WAIT** | 历史数据不足 15 条，积累中 |
| **SKIP** | 板块趋势低迷，跳过 |
| **WAIT** | C5/HaloSkins 等弱平台对需要更高利润才放行 |

### 风控规则

- C5 → HaloSkins：净利润需 ≥ 3%
- C5 → Buff：净利润需 ≥ 2%
- 高价品（≥ ¥1500）：净利润需 ≥ 8%
- 价格变化频率 ≥ 7 且净利润 < 0：暂缓
- 同一商品 120 分钟冷却期
- 每小时最多 15 个 BUY 信号

---

## 持仓管理与信号评估

### 持仓生命周期

```
BUY 信号 → 开仓（记录入场价/时间）
  → 每轮扫描时 mark_price（更新最新价格）
    → 触发条件之一则平仓：
      ├── 止盈：净收益率 ≥ 8%
      ├── 止损：净收益率 ≤ -5%
      └── 超时：持仓 ≥ 72 小时
```

所有交易（开仓/平仓）记录到 `signal_events` 和 `executions` 表，可追溯完整交易历史。

### 信号命中率评估

系统自动追踪每个 BUY 信号在 24h / 72h / 168h 后的实际市场表现：
- 对比信号产生时的买入价与当前最新价
- 计算实际收益率和期间最高收益
- 评估结果写入数据库，回测报告中展示因子命中率

---

## 回测系统

### 回测流程

1. 读取 `shared_data/opportunities.csv` 中所有 BUY 信号记录
2. 按 72h 时间窗口过滤（无数据则使用全部历史）
3. **通过 CSQAQ API 批量获取所有商品的当前 Buff 卖出价**（实时价格）
4. 虚拟账户模拟买入（扣除 2.5% 手续费）→ 卖出（扣除 2.5% 手续费）
5. 计算收益/胜率/最大回撤/夏普比率等指标
6. 生成图表（收益曲线/收益分布/回撤曲线/累计收益）
7. 导出 JSON 报告 + 钉钉推送

### 卖出价来源优先级

| 优先级 | 来源 | 标记 | 说明 |
|--------|------|------|------|
| 1 | CSQAQ API 实时 Buff 卖价 | 🟢 live | 当前真实市场价格，最准确 |
| 2 | CSV 中信号时刻的卖出价 | 📄 csv | API 不可用时的回退 |
| 3 | 买入价 × 1.03 保守估计 | 📝 est | 兜底方案 |

### 回测指标

| 指标 | 说明 |
|------|------|
| 总收益/收益率 | 所有交易的净利润总和 |
| 胜率 | 盈利交易占比 |
| 最大回撤 | 账户价值从峰值到谷值的最大跌幅 |
| 夏普比率 | 风险调整后收益（年化） |
| 平均收益率 | 单笔交易的平均收益率 |
| 因子命中率 | 按动量分组/综合分分组的 72h 实际收益统计 |

### 参数自调优（AutoTuner）

- 每周日 03:30 自动执行参数搜索
- 搜索空间：价差阈值/安全垫/买入分数线/止盈/止损
- 随机搜索 + Bayesian（可选，依赖 scikit-optimize）
- 新参数标记为 pending，8 天后自动应用（验证稳定性）

---

## 通知系统

### 钉钉通知类型

| 类型 | 触发条件 | 内容 |
|------|---------|------|
| BUY 信号 | 策略产生 BUY | 商品名/买入价/卖出价/价差/安全垫/综合分 |
| 扫描报告 | 每轮扫描结束 | 扫描状态/过滤统计/信号统计/近期 BUY 明细 |
| 回测报告 | 每天 22:00 定时回测 | 收益率/胜率/回撤/夏普/交易明细/因子命中率 |
| 异常告警 | 扫描出错 | 错误信息 |

> 钉钉机器人关键词设置为 `ding`，所有通知消息均包含此关键词。

---

## 状态监控

扫描器启动后监听 HTTP 8199 端口：

```bash
curl http://<VPS_IP>:8199/          # 完整状态 JSON
curl http://<VPS_IP>:8199/health    # 健康检查
```

返回信息包括：当前轮次/批次进度/遍历商品数/各过滤阶段跳过数/BUY-WAIT-HOLD-SELL 信号统计/最近 BUY 明细/错误信息。

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
# Copy the example config and fill in your credentials
cp config/app_config.example.json config/app_config.json
```

Edit `config/app_config.json`，填入你自己的：

| 配置项 | 说明 | 申请地址 |
|--------|------|---------|
| `sdt_key` | SteamDT API Key | https://open.steamdt.com |
| `csqaq_token` | CSQAQ ApiToken | https://api.csqaq.com |
| `dingtalk_webhook` | 钉钉机器人 Webhook（可选） | 钉钉群 → 添加机器人 |

> 也可以通过环境变量 `SDT_KEY`、`CSQAQ_TOKEN` 传入，优先级高于配置文件。

### 3. Run

```bash
# 启动扫描器（需要保持运行）
python src/main_vps.py

# 另一个终端：快速回测（需要先运行一段时间产生 BUY 信号）
python scripts/backtest_quick.py quick

# 或者用 Docker 一键部署
docker compose up -d --build
```

### 4. Monitor

```bash
# 查看扫描状态
curl http://localhost:8199/

# 查看 Docker 日志
docker compose logs -f scanner
```

---

## 项目结构

```
├── config/
│   ├── config.py              # 核心配置（API key/阈值/路径）
│   └── app_config.json        # JSON 配置（策略参数/调度/钉钉 webhook）
│
├── src/
│   ├── main_vps.py            # VPS 扫描器入口（CSQAQ 单数据源）
│   ├── main.py                # 完整扫描器入口（SteamDT + CSQAQ）
│   ├── api_client.py          # CSQAQ / SteamDT API 封装
│   ├── strategy.py            # QuantStrategy 多因子评分引擎
│   ├── database.py            # MarketDB（SQLite：价格历史/信号/持仓/交易）
│   ├── execution_engine.py    # 持仓管理（开仓/止盈止损/平仓）
│   ├── signal_evaluator.py    # 信号命中率评估
│   ├── scan_stats.py          # 线程安全扫描统计收集器
│   ├── status_server.py       # HTTP 状态 API（:8199）
│   ├── dingtalk_notify.py     # 钉钉通知（扫描报告/BUY 信号/异常）
│   ├── backtest_engine.py     # 回测引擎（虚拟账户/交易模拟/指标计算）
│   ├── backtest_db.py         # 回测历史数据库
│   ├── backtest_scheduler.py  # 回测调度器 + BacktestRunner
│   ├── backtest_notifier.py   # 回测钉钉通知（Markdown 格式）
│   ├── backtest_visualizer.py # Matplotlib 图表生成
│   ├── auto_tuner.py          # 参数自调优（随机搜索/Bayesian）
│   ├── refiner.py             # 扫描后二次分析工具
│   └── aihelp_vision.py       # AI 辅助工具（独立模块）
│
├── scripts/
│   ├── auto_backtest.py       # 定时回测主程序（scheduler 容器入口）
│   ├── backtest_quick.py      # 快速回测（72h/168h/自动调参）
│   ├── run_backtest.py        # 交互式完整回测系统
│   ├── auto_tune.py           # 参数调优脚本
│   └── analyze_signal_factors.py  # 因子命中率分析
│
├── data/
│   └── csqaq_id_map.json      # CSQAQ 商品名 → ID 映射表
│
├── docker-compose.yml         # 双容器编排（scanner + scheduler）
├── Dockerfile                 # Python 3.11-slim 镜像
├── entrypoint.sh              # Docker 入口脚本
├── requirements.txt           # Python 依赖
│
├── shared_data/               # Docker 共享数据卷（scanner ↔ scheduler）
│   ├── opportunities.csv      # BUY 信号记录
│   ├── cs2_quant.db           # 市场数据库
│   ├── backtest_history.db    # 回测历史数据库
│   └── low_sales_blacklist.txt # 低销量黑名单
│
└── backtest_logs/             # 回测日志和 JSON 报告
```

---

## 部署方式

### Docker 部署（推荐，生产环境）

VPS 上使用 docker compose 运行两个容器：

| 容器 | 职责 | 入口 |
|------|------|------|
| `cs2-scanner` | 实时扫描器，7×24 运行 | `src/main_vps.py` |
| `cs2-scheduler` | 定时回测 + 参数调优 | `scripts/auto_backtest.py` |

```bash
# 一键启动
docker compose up -d --build

# 查看日志
docker compose logs -f scanner
docker compose logs -f scheduler

# 查看扫描状态
curl http://localhost:8199/

# 手动触发回测
docker exec cs2-scheduler python ./scripts/backtest_quick.py quick
```

两个容器通过 `shared_data/` 目录共享数据（CSV、数据库、黑名单），scanner 写入的 BUY 信号 scheduler 可以直接读取。

### 本地运行

```bash
pip install -r requirements.txt

# 启动扫描器
python src/main_vps.py

# 快速回测
python scripts/backtest_quick.py quick

# 交互式回测
python scripts/run_backtest.py
```

---

## 配置说明

### config/app_config.json

所有配置集中在此文件，容器镜像构建时打包进去：

```json
{
  "api": {
    "sdt_key": "你的 SteamDT API Key",
    "csqaq_token": "你的 CSQAQ ApiToken"
  },
  "scheduler": {
    "mode": "daily",           // daily / hourly / interval / immediate
    "time": "22:00",           // 每日回测时间
    "interval_hours": 6        // interval 模式下的间隔
  },
  "backtest": {
    "hours_back": 72,          // 回测回溯时间窗口
    "initial_balance": 10000,  // 虚拟初始资金
    "enable_charts": true      // 是否生成图表
  },
  "notification": {
    "dingtalk_webhook": "你的钉钉机器人 Webhook URL"
  },
  "strategy": {
    "MIN_EDGE_SCORE": 0.02,         // 最低价差因子
    "MIN_NET_PROFIT_RATE": 0.0,     // 最低安全垫
    "BUY_SCORE_THRESHOLD": 28,      // 买入综合分门槛
    "TAKE_PROFIT_RATE": 0.08,       // 止盈线
    "STOP_LOSS_RATE": -0.05         // 止损线
  },
  "tuning": {
    "enabled": true,                // 是否启用自动调参
    "weekly_day": "sunday",         // 调参日
    "weekly_time": "03:30",         // 调参时间
    "apply_every_days": 8           // 新参数验证天数后自动应用
  }
}
```

### 数据库

| 数据库 | 位置 | 内容 |
|--------|------|------|
| `cs2_quant.db` | `shared_data/` | 商品价格历史（最多 60 条/商品）、系列趋势、信号事件、持仓记录、交易流水 |
| `backtest_history.db` | `shared_data/` | 回测历史记录、参数调优记录 |

### 费率模型

- 买入手续费：2.5%（`PLATFORM_FEE_RATE`）
- 卖出手续费：2.5%
- 双边合计 5%

---

## API 数据源

| 数据源 | API | 提供内容 |
|--------|-----|---------|
| CSQAQ | `api.csqaq.com` | 悠悠有品卖价 + Buff 卖价 + 24h 销量 + Steam 价格（一次调用获取多平台报价） |
| SteamDT | `open.steamdt.com` | Steam 市场价格、7 日均价（仅 `main.py` 使用） |

CSQAQ API 需要先调用 `bind_local_ip` 绑定 VPS IP 到白名单（30 秒冷却期），绑定后可正常调用价格查询接口（限频 1 次/秒）。

---

## 扫描流程详解

每一轮扫描的完整流程：

1. 加载 `data/csqaq_id_map.json` 中的目标商品列表（按热门关键词过滤）
2. 排除 Well-Worn / Battle-Scarred 磨损
3. 排除 `low_sales_blacklist.txt` 中的低销量商品
4. 按 50 个一批调用 CSQAQ API 获取报价
5. 对每个商品逐级过滤：
   - **价格过滤**：买入价 < ¥30 或 > ¥6000 → 跳过
   - **销量过滤**：Buff 24h 销量 < 40 → 跳过（极低销量加入黑名单）
   - **价差过滤**：跨平台价差率 ≤ 2% → 跳过
   - **安全垫过滤**：扣除双边手续费后净收益率 ≤ 0% → 跳过
6. 通过过滤的商品 → 写入数据库 → 获取历史数据 → 策略评分
7. BUY 信号 → 钉钉推送 + 写入 CSV + 开仓记录
8. 非 BUY 信号 → 检查是否需要平仓（止盈/止损/超时）
9. 每轮结束发送扫描统计报告到钉钉
10. 等待 50 分钟后开始下一轮

---

## 常见问题

### 钉钉收不到通知

- 检查 `app_config.json` 中 `dingtalk_webhook` 是否正确
- 确认钉钉机器人已添加到群
- 确认机器人关键词设置为 `ding`

### 回测报告显示 "找不到数据文件"

- 确认 `shared_data/opportunities.csv` 存在且有数据
- scanner 需要运行一段时间产生 BUY 信号后才有回测数据
- 检查 Docker volume 是否正确挂载（两个容器都要挂 `shared_data`）

### CSQAQ API 返回 401

- 确认 `app_config.json` 中 `csqaq_token` 正确
- VPS 容器重建后需要重新绑定 IP（自动完成，但有 30 秒冷却期）
- 检查 Docker 容器内是否通过环境变量覆盖了 token

### scanner 不产生 BUY 信号

- 当前策略门槛较低（综合分 ≥ 28），正常情况应有信号
- 检查 CSQAQ API 是否正常返回报价
- 查看日志中 items_skipped_edge / items_skipped_cushion 的数量
- 大部分商品被价差或安全垫过滤是正常的

---

## 依赖

```
pandas>=1.3.0        # 数据处理
numpy>=1.21.0        # 数值计算
matplotlib>=3.4.0    # 图表生成
schedule>=1.1.0      # 定时任务调度
requests>=2.26.0     # HTTP 请求
scikit-learn>=1.0.0  # 参数调优（可选）
scipy>=1.7.0         # 统计计算
```
