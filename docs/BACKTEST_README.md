# CS2 量化交易系统 - 完整虚拟回测系统

## 📊 系统功能

### 1. **虚拟资金模拟** 🏦
- 真实账户模拟：初始资金、持仓管理、成本追踪
- 三维交易模型：买入 → 持仓 → 卖出的完整生命周期
- 手续费精算：平台手续费自动计算（默认2.5%）

### 2. **详细性能指标** 📈
- **交易统计**：总笔数、获利笔数、亏损笔数、胜率
- **收益指标**：平均收益、最佳/最差收益、总收益率
- **风险指标**：最大回撤、夏普比率、单笔最大亏损
- **盈亏数据**：实现和未实现盈亏

### 3. **数据库持久化** 💾
- 保存所有回测历史记录
- 支持历史对比和趋势分析
- 可追溯每一笔模拟交易
- 长期性能跟踪

### 4. **可视化图表** 📊
- **账户净值曲线**：实时跟踪账户变化
- **收益率分布**：直观看出盈亏交易分布
- **回撤曲线**：风险可视化
- **累积收益**：策略整体表现
- **关键指标汇总**：一览表主要性能指标

### 5. **自动化运行** ⏰
- 每日定时执行：`schedule_daily(hour=22)`
- 每小时执行：`schedule_hourly(minute=0)`
- 每N小时执行：`schedule_every_n_hours(6)`
- 每N分钟执行：`schedule_every_n_minutes(30)`
- 后台线程运行，不阻塞主程序

### 6. **通知提醒** 📬
- 邮件通知：SMTP 自动发送回测报告
- 钉钉通知：实时推送关键指标
- 日志记录：详细的回测执行日志
- JSON 报告导出

---

## 🚀 快速开始

### 方式1：快速回测（推荐新手）
```bash
# 执行72小时数据回测
python backtest_quick.py quick

# 执行7天数据回测
python backtest_quick.py extended

# 查看历史回测
python backtest_quick.py history
```

### 方式2：交互式菜单
```bash
# 启动完整系统
python run_backtest.py

# 选择菜单选项：
# 1. 执行单次回测（72小时）
# 2. 执行自定义回测
# 3. 启动自动回测
# 4. 查看回测历史
# ...
```

### 方式3：编程方式
```python
from run_backtest import CompleteBacktestSystem

system = CompleteBacktestSystem()

# 执行单次回测
metrics = system.run_backtest(
    hours_back=72,              # 回溯时间（小时）
    initial_balance=10000,      # 初始资金（元）
    enable_charts=True,         # 生成图表
    enable_email=False,         # 邮件通知
    enable_dingtalk=False       # 钉钉通知
)

# 启动每日回测（22:00）
system.start_auto_backtest(schedule_type='daily', schedule_param=22)

# 查看历史
system.view_backtest_history(limit=20)

# 性能统计
system.view_backtest_statistics(days=7)
```

---

## 📁 项目结构

```
002/
├── backtest_engine.py       # 虚拟账户 + 回测引擎（核心）
├── backtest_db.py           # 数据库持久化模块
├── backtest_visualizer.py   # 图表可视化模块
├── backtest_notifier.py     # 通知提醒模块
├── backtest_scheduler.py    # 自动调度模块
├── backtest_config.py       # 回测配置文件
├── run_backtest.py          # 完整系统入口（含菜单）
├── backtest_quick.py        # 快速运行脚本
└── checker.py               # 原回测文件（已增强）

backtest_charts/            # 生成的图表存放目录
backtest_logs/              # 日志文件目录
```

---

## 🔧 配置说明

### 基础配置 (backtest_config.py)

```python
# 虚拟账户
INITIAL_BALANCE = 10000        # 初始虚拟资金

# 数据库
BACKTEST_DB = "backtest_history.db"
BACKTEST_LOG_DIR = "./backtest_logs"
BACKTEST_CHART_DIR = "./backtest_charts"

# 图表
ENABLE_CHARTS = True           # 自动生成图表
CHART_DPI = 300                # 高分辨率

# 通知
ENABLE_EMAIL = False           # 邮件通知
ENABLE_DINGTALK = False        # 钉钉通知

# 自动调度
AUTO_BACKTEST_ENABLED = False
AUTO_BACKTEST_TYPE = "daily"   # 每天执行
AUTO_BACKTEST_PARAM = 22       # 22点执行
```

### 启用邮件通知

1. 编辑 `backtest_config.py`，填写 SMTP 信息：
```python
"EMAIL_CONFIG": {
    "host": "smtp.gmail.com",
    "port": 587,
    "sender": "your_email@gmail.com",
    "password": "your_app_password",  # 应用专用密码
    "recipient": "recipient@example.com"
}
```

2. 在代码中启用：
```python
system.run_backtest(
    enable_email=True,
    email_config=CONFIG['EMAIL_CONFIG']
)
```

### 启用钉钉通知

1. 创建钉钉群，获取 webhook URL
2. 编辑 `backtest_config.py`：
```python
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxxxx"
ENABLE_DINGTALK = True
```

3. 在代码中启用：
```python
system.run_backtest(
    enable_dingtalk=True,
    dingtalk_webhook=CONFIG['DINGTALK_WEBHOOK']
)
```

---

## 📊 回测报告示例

```
======================================================================
                        📊 虚拟回测最终报告
======================================================================

💼 账户指标:
   初始资金:             ¥10,000.00
   最终资金:             ¥10,523.45
   总收益:               ¥523.45
   收益率:               5.23%

📈 交易指标:
   总交易数:             48
   获利笔数:             30
   亏损笔数:             18
   胜率:                 62.50%

💰 盈亏指标:
   平均单笔利润:         ¥10.91
   最大单笔利润:         ¥45.50
   最大单笔亏损:         ¥-32.20

📊 收益率指标:
   平均收益率:           1.25%
   最佳收益率:           6.50%
   最差收益率:           -4.20%

⚠️  风险指标:
   最大回撤:             -8.50%
   夏普比率:             1.42

======================================================================
```

---

## 📈 性能指标解释

| 指标 | 解释 | 好的范围 |
|------|------|---------|
| **胜率** | 盈利交易占比 | > 55% |
| **收益率** | 总收益 / 初始资金 | > 5% |
| **最大回撤** | 账户从高点到低点的最大跌幅 | < -20% |
| **夏普比率** | 风险调整后的收益率 | > 1.0 |
| **平均收益** | 平均每笔交易的利润 | > 0 |
| **最大单笔利润** | 单笔最好的交易 | 越大越好 |
| **最大单笔亏损** | 单笔最差的交易 | > -50% |

---

## 🔍 数据分析与对比

### 查看单次回测详情
```python
system.view_backtest_history(limit=10)
```

### 查看统计摘要（N天内）
```python
system.view_backtest_statistics(days=7)
```

### 对比多次回测
```python
system.compare_recent_backtests(count=5)
```

---

## 📝 日志文件

- **日志位置**：`backtest_logs/backtest_YYYYMMDD.log`
- **内容包括**：
  - 回测开始/结束时间
  - 每笔交易的详细记录
  - 错误和警告信息
  - 性能指标

### 示例日志
```
[2026-04-03 10:15:30] [INFO] 🚀 回测开始 | 初始资金: ¥10000.00 | 机会数: 48
[2026-04-03 10:15:31] [TRADE] ✅ 交易: USP-S | Black Lotus | 买:1050.00 卖:1090.00 | 利率:3.81%
[2026-04-03 10:15:32] [TRADE] ❌ 交易: MAC-10 | Neon Rider | 买:450.00 卖:420.00 | 利率:-6.67%
...
[2026-04-03 10:15:45] [INFO] ✅ 回测完成
   总收益: ¥523.45
   收益率: 5.23%
   胜率: 62.50%
```

---

## 🔄 自动化工作流

### 每天22:00自动回测 + 生成报告
```python
from run_backtest import CompleteBacktestSystem

system = CompleteBacktestSystem()
system.start_auto_backtest(schedule_type='daily', schedule_param=22)

# 运行程序，每天22:00自动执行回测
# 输出：
# - backtest_charts/ 目录中的图表
# - backtest_logs/ 目录中的日志
# - 数据库中的历史记录
# - 邮件通知（如已配置）
```

### 每小时基于最新数据回测
```python
system.start_auto_backtest(schedule_type='minutes', schedule_param=30)
# 每30分钟执行一次回测
```

---

## 💡 使用建议

1. **初期调试**：先运行 `backtest_quick.py quick` 测试系统是否正常
2. **数据积累**：连续运行7天以上，获得足够的统计数据
3. **纵向对比**：观察同一策略在不同时期的表现变化
4. **参数优化**：如发现胜率不理想，可调整 `config.py` 中的阈值
5. **实盘前验证**：回测胜率连续 > 60% 方可考虑实盘

---

## ⚙️ 故障排查

### 问题：导入错误
```
ModuleNotFoundError: No module named 'schedule'
```
**解决**：安装依赖
```bash
pip install pandas numpy matplotlib schedule requests
```

### 问题：数据库锁定
```
sqlite3.OperationalError: database is locked
```
**解决**：确保没有多个程序同时访问同一数据库文件

### 问题：API 超时
```
ConnectionTimeout: API request timeout
```
**解决**：检查网络连接，增加超时时间

---

## 📞 支持和反馈

- 所有日志保存在 `backtest_logs/` 目录
- 所有图表保存在 `backtest_charts/` 目录
- 数据库文件：`backtest_history.db`

---

**版本**：v2.0  
**更新日期**：2026-04-03  
**作者**：AI 辅助开发
