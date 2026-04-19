# 📊 CS2 皮肤量化回测系统 - 完整使用指南

## 📑 目录
1. [系统概述](#系统概述)
2. [前置准备](#前置准备)
3. [快速开始](#快速开始)
4. [详细步骤](#详细步骤)
5. [配置说明](#配置说明)
6. [结果解析](#结果解析)
7. [常见问题](#常见问题)
8. [文件说明](#文件说明)

---

## 系统概述

### 🎯 这个系统能做什么？

**回测系统**是一个完整的虚拟交易模拟框架，帮助你：

| 功能 | 说明 |
|------|------|
| 📈 **虚拟交易模拟** | 用历史数据模拟买卖，看策略在过去表现如何 |
| 💰 **账户资金管理** | 模拟真实的买入→持仓→卖出的交易全过程 |
| 📊 **性能指标计算** | 自动计算 15 种关键性能指标（胜率、收益率、最大回撤等） |
| 📉 **可视化图表** | 生成 5 种专业图表查看回测结果 |
| 💾 **数据持久化** | 所有回测记录存储到数据库，支持历史对比 |
| ⏰ **自动定时运行** | 设置后自动每天/每小时运行回测 |
| 📬 **智能通知** | 重要结果通过邮件/钉钉推送 |

### 🏗️ 系统架构

```
opportunities.csv (数据源)
          ↓
    backtest_engine.py (核心回测引擎)
          ↓
    ├─ backtest_db.py (保存数据库)
    ├─ backtest_visualizer.py (生成图表)
    ├─ backtest_config.py (读取配置)
    └─ backtest_notifier.py (发送通知)
          ↓
    backtest_logs/ (输出日志)
    backtest_results.db (历史数据)
    *.png (图表文件)
```

---

## 前置准备

### ✅ 必要条件

1. **Python 环境**：Python 3.9+（已有虚拟环境）
   ```bash
   # 验证 Python 版本
   python --version
   ```

2. **依赖包**：已安装以下软件包
   - pandas >= 1.3.0（数据处理）
   - numpy >= 1.21.0（数值计算）
   - matplotlib >= 3.4.0（绘图）
   - schedule >= 1.1.0（定时任务）
   - requests >= 2.26.0（HTTP 请求）

   验证方法：
   ```bash
   pip list | grep -E "pandas|numpy|matplotlib"
   ```

3. **数据文件**：`opportunities.csv` 包含待回测的交易数据
   - 路径：`d:\Pythonprojectcode\opportunities.csv`
   - 格式：CSV 文件，包含以下列：
     ```
     time, name, price, buy_price, sell_price, 
     buy_from, sell_to, profit, slope, hurst, er, changes, score1, score2
     ```
   - 如果没有也没关系，系统会自动适配

### ⚙️ 配置文件

编辑 `backtest_config.py` 或 `config.py`：

```python
CONFIG = {
    # 回测参数
    "INITIAL_BALANCE": 10000,        # 初始资金（元）
    "FEE_RATE": 0.025,               # 平台手续费比例（2.5%）
    "MIN_PROFIT_RATE": 0.03,         # 最小目标收益率（3%）
    
    # 数据源配置
    "DATA_SOURCE": "opportunities.csv",
    "HOURS_BACK": 72,                # 回测最近 72 小时的数据
    
    # 输出配置
    "OUTPUT_DIR": "./backtest_results",
    "DB_NAME": "backtest_results.db",
    "LOG_DIR": "./backtest_logs",
}
```

---

## 快速开始

### 🟢 方式1：一键快速回测（推荐新手）

**用途**：快速看一遍系统能否正常运行，大约 2-5 分钟

```bash
# 进入项目目录
cd D:\Pythonprojectcode\002

# 执行快速回测
python backtest_quick.py quick
```

**预期结果**：
```
✅ 回测开始，加载 CSV 数据...
📊 已加载 1652 条交易机会
🔄 正在执行 1652 笔虚拟交易...
✅ 交易完成，成功 1542 笔，失败 110 笔

📈 性能指标：
   总交易数: 1542
   获利笔数: 856 (55.5%)
   亏损笔数: 686 (44.5%)
   总收益: ¥2,345.67 (23.45% ROI)
   最大回撤: -8.34%
   夏普比率: 1.23

📉 图表已保存到: backtest_results/
   - account_curve_20260403_235959.png
   - win_lose_20260403_235959.png
   - ...

✅ 回测完成！
```

---

### 🟡 方式2：交互式完整回测（推荐深度分析）

**用途**：手动选择回测参数，进行完整分析

```bash
# 进入项目目录
cd D:\Pythonprojectcode\002

# 启动交互式菜单
python run_backtest.py
```

**菜单选项**：
```
╔════════════════════════════════════════╗
║   CS2 皮肤量化回测系统 - 主菜单        ║
╠════════════════════════════════════════╣
║ 1. 快速回测（短时间数据）             ║
║ 2. 完整回测（长时间数据）             ║
║ 3. 自定义回测（选择参数）             ║
║ 4. 查看历史回测结果                   ║
║ 5. 设置自动定时回测                   ║
║ 6. 查看性能对标                       ║
║ 7. 导出报告                           ║
║ 0. 退出                               ║
╚════════════════════════════════════════╝

请选择 (0-7): 
```

选择 **1** → 快速回测：
- 使用最近 72 小时数据
- 回测结果立即显示
- 自动生成图表

选择 **3** → 自定义回测：
```
请输入初始资金 (默认¥10000): 50000
请输入回测时长 (小时，默认72): 168
请输入最小目标收益 (默认3%): 5
请输入手续费率 (默认2.5%): 2.5

🔄 正在执行回测...
```

---

## 详细步骤

### 📋 完整工作流程

#### **第1步：准备数据**

1. **方案A** - 使用 main.py 采集最新数据（推荐）
   ```bash
   cd D:\Pythonprojectcode\002
   python main.py
   ```
   - 程序会持续扫描市场
   - 找到符合条件的交易机会自动记录到 `opportunities.csv`
   - 包含完整的买卖价、平台信息、技术指标等

2. **方案B** - 使用现有的 opportunities.csv
   - 如果已经有数据文件，直接使用即可
   - 系统会自动读取并进行回测

#### **第2步：启动回测**

```bash
# 确保在 002/ 目录下
cd D:\Pythonprojectcode\002

# 选择执行方式
python backtest_quick.py quick        # 快速（推荐）
# 或
python run_backtest.py                # 交互式
```

#### **第3步：查看结果**

回测完成后会生成：

1. **控制台输出**：立即显示关键指标
   ```
   📊 回测摘要 (初始资金: ¥10000)
   ═══════════════════════════════════════════════
   交易统计    | 总笔数: 1542 | 获利: 856 | 亏损: 686
   盈亏情况    | 总利润: ¥2,345.67 | ROI: 23.45%
   风险指标    | 最大回撤: -8.34% | 夏普比率: 1.23
   账户情况    | 初始: ¥10000 | 最终: ¥12,345.67
   ═══════════════════════════════════════════════
   ```

2. **图表文件**：保存到 `backtest_results/` 文件夹
   - `account_curve_*.png` - 账户资金曲线
   - `win_lose_*.png` - 胜负交易分布
   - `drawdown_*.png` - 最大回撤曲线
   - `cumulative_*.png` - 累积收益
   - `metrics_summary_*.png` - 指标汇总面板

3. **数据库记录**：保存到 `backtest_results.db`
   - 可用于后续对比分析
   - 支持历史查询

4. **详细日志**：保存到 `backtest_logs/`
   - `backtest_20260403.log` 完整执行记录
   - 便于调试和深度分析

#### **第4步：分析结果**

| 指标 | 含义 | 评价标准 |
|------|------|---------|
| **胜率** | 获利交易数 ÷ 总交易数 | > 50% 为好 |
| **总收益率 (ROI)** | (最终资金 - 初始资金) ÷ 初始资金 | > 10% 为好 |
| **最大回撤** | 账户最大下跌幅度 | < -10% 为可控 |
| **夏普比率** | 风险调整后的收益 | > 1.0 为好 |
| **平均收益** | 单笔交易平均获利 | 越高越好 |

---

## 配置说明

### 📝 关键参数详解

#### backtest_config.py

```python
{
    # ═══ 交易参数 ═══
    "INITIAL_BALANCE": 10000,          # 初始资金（元）
                                        # 模拟用越多钱，分散风险越好
                                        
    "FEE_RATE": 0.025,                 # 手续费比例（2.5%）
                                        # BUFF 平台 2.5%，其他 3%
                                        
    "MIN_PROFIT_RATE": 0.03,           # 最小目标收益率（3%）
                                        # 只记录高于此收益的交易
    
    "MIN_HOLDING_HOURS": 1,            # 最少持仓时间（小时）
                                        # 防止过度交易
    
    # ═══ 数据参数 ═══
    "DATA_SOURCE": "opportunities.csv", # 数据文件路径
    "HOURS_BACK": 72,                  # 回测最近几小时数据
                                        # 72 = 3 天，168 = 1 周
    
    # ═══ 输出参数 ═══
    "OUTPUT_DIR": "./backtest_results", # 结果输出目录
    "DB_NAME": "backtest_results.db",   # 数据库文件名
    "LOG_DIR": "./backtest_logs",       # 日志目录
    
    # ═══ API 参数 ═══（可选）
    "SDT_KEY": "your_key",              # SteamDT API 密钥
    "CSQAQ_TOKEN": "your_token",        # CSQAQ API 令牌
}
```

### 🔧 常用配置组合

**场景1：保守策略（风险小，收益低）**
```python
"INITIAL_BALANCE": 20000,       # 用更多钱来分散风险
"FEE_RATE": 0.03,               # 保守手续费
"MIN_PROFIT_RATE": 0.05,        # 只做 5% 以上的机会
"HOURS_BACK": 168,              # 用 1 周数据
```

**场景2：激进策略（风险大，收益高）**
```python
"INITIAL_BALANCE": 5000,        # 用少钱来测试高风险策略
"FEE_RATE": 0.025,              # 低手续费
"MIN_PROFIT_RATE": 0.01,        # 即使 1% 也做
"HOURS_BACK": 24,               # 只用 1 天最新数据
```

**场景3：平衡策略（现在推荐）**
```python
"INITIAL_BALANCE": 10000,       # 标准资金
"FEE_RATE": 0.025,              # 标准手续费
"MIN_PROFIT_RATE": 0.03,        # 3% 目标
"HOURS_BACK": 72,               # 3 天数据
```

---

## 结果解析

### 📊 理解 15 个性能指标

回测完成后会显示这些指标：

#### 📈 交易统计
```
总交易数 (total_trades): 1542
├─ 获利交易 (winning_trades): 856
├─ 亏损交易 (losing_trades): 686
└─ 胜率 (win_rate): 55.5%
```
**解读**：在这次回测中，1542 笔虚拟交易中有 856 笔赚钱了（55.5% 胜率）

#### 💰 收益指标
```
总利润 (total_profit): ¥2,345.67       // 赚了这么多钱
├─ 平均每笔 (avg_profit): ¥1.52
├─ 最好的一笔 (max_profit_trade): ¥125.50
├─ 最差的一笔 (max_loss_trade): -¥85.30
└─ 总收益率 (total_return): 23.45%    // 初始资金增长了这个百分比
```
**解读**：平均每笔交易赚 ¥1.52，如果都按这个速度，初始 ¥10000 会变成 ¥12,345.67

#### 📊 收益率详解
```
平均收益率 (avg_return): 1.52%         // 单笔平均收益
最佳收益率 (best_return): 12.35%       // 最好交易的收益率
最差收益率 (worst_return): -5.23%      // 最差交易的亏损率
```

#### ⚠️ 风险指标
```
最大回撤 (max_drawdown): -8.34%
└─ 意思：在这次回测中，账户最多下跌了 8.34%
   例：¥10000 → 最低点 ¥9,166 → 恢复到 ¥12,345

夏普比率 (sharpe_ratio): 1.23
└─ 意思：高于 1.0 说明风险调整后的收益不错
   值越高说明在承受风险的同时获得更好回报
```

#### 🏦 账户情况
```
初始资金 (initial_balance): ¥10,000
最终资金 (final_balance): ¥12,345.67
最高资金 (peak_balance): ¥13,500.00   // 账户的最高点
```

---

## 常见问题

### ❓ Q: 为什么回测结果只有 0 笔交易？

**A**：可能的原因：

1. **CSV 文件为空或不存在**
   ```bash
   # 检查文件
   ls -la opportunities.csv
   head -5 opportunities.csv
   ```
   → 需要先运行 `main.py` 采集数据

2. **CSV 格式有问题**
   - 检查是否有 `buy_price` 和 `sell_price` 列
   - 如果没有，系统会用 `price` 列和 1.03 倍计算

3. **过滤条件太严格**
   ```python
   # 在 config.py 中降低这些参数
   "MIN_PROFIT_RATE": 0.01,  # 改低这个
   "MIN_HOLDINGS_HOURS": 0,   # 改为 0
   ```

---

### ❓ Q: 图表生成失败是什么问题？

**A**：通常是这些原因：

1. **matplotlib 没装或版本过低**
   ```bash
   pip install --upgrade matplotlib
   ```

2. **输出目录不存在**
   ```bash
   mkdir -p backtest_results
   ```

3. **权限问题**
   - 确保有写入权限
   - Windows 可能需要以管理员身份运行

---

### ❓ Q: 现在的 3% 利润估计准不准？

**A**：当前状态：

- ✅ 如果 CSV 有 `sell_price` 列 → 用真实价格
- ⚠️ 如果 CSV 没有 `sell_price` 列 → 用 buy_price × 1.03 估计

**建议**：
1. 运行 `main.py` 采集新数据（包含真实 sell_price）
2. 然后再做回测（结果会更准确）

---

### ❓ Q: 如何定时自动回测？

**A**：使用 `backtest_scheduler.py`：

```python
from backtest_scheduler import BacktestScheduler

scheduler = BacktestScheduler()

# 每天晚上10点回测一次
scheduler.schedule_daily(hour=22, minute=0)

# 或每 6 小时回测一次
scheduler.schedule_every_n_hours(6)

# 或每小时的 0 分执行
scheduler.schedule_hourly(minute=0)

# 启动后台运行
scheduler.start()

# 程序可以做其他事，回测会后台自动运行
while True:
    time.sleep(1)
```

---

### ❓ Q: 如何导出结果或发送通知？

**A**：系统包含通知功能：

```bash
# 查看 backtest_notifier.py 配置邮件和钉钉
# 编辑 config.py 中的邮件参数
"SMTP_SERVER": "smtp.qq.com",
"SMTP_USER": "your@qq.com",
"SMTP_PASS": "xxxxx",
"NOTIFY_EMAIL": "alert@example.com",
```

---

## 文件说明

### 📁 项目结构

```
002/
├── backtest_engine.py         ← 核心回测引擎
│   ├─ VirtualAccount         虚拟账户类
│   └─ BacktestEngine          回测主逻辑
│
├── backtest_db.py             ← 数据库操作
│   └─ BacktestDatabase        3表数据库模型
│
├── backtest_visualizer.py     ← 图表生成
│   └─ BacktestVisualizer      5种图表类型
│
├── backtest_config.py         ← 配置参数
├── backtest_scheduler.py      ← 定时任务
├── backtest_notifier.py       ← 邮件/钉钉通知
│
├── backtest_quick.py          ← 快速回测脚本 ⭐ 推荐
├── run_backtest.py            ← 交互式菜单
│
├── config.py                  ← API 密钥配置
├── api_client.py              ← API 调用
├── strategy.py                ← 交易策略
├── database.py                ← 市场数据库
│
├── main.py                    ← 实时扫描程序 🔴 后台运行
├── opportunities.csv          ← 交易数据源
│
├── backtest_results/          ← 💾 输出目录
│   ├─ account_curve_*.png
│   ├─ win_lose_*.png
│   ├─ drawdown_*.png
│   ├─ cumulative_*.png
│   ├─ metrics_summary_*.png
│   └─ backtest_results.db
│
└── backtest_logs/             ← 📋 回测日志
    └─ backtest_20260403.log
```

---

## 🎬 完整使用场景示例

### 场景：新手第一次使用

**时间**：5分钟

```bash
# 1️⃣ 进入目录
cd D:\Pythonprojectcode\002

# 2️⃣ 快速回测（直接跑不需要改配置）
python backtest_quick.py quick

# 3️⃣ 等待完成，查看结果
# ✅ 回测完成！
# 📊 性能指标已输出
# 📉 图表已保存到 backtest_results/

# 4️⃣ 打开图表文件查看
start backtest_results/
```

---

### 场景：深度分析回测结果

**时间**：15分钟

```bash
# 1️⃣ 启动交互式菜单
python run_backtest.py

# 2️⃣ 选择 3. 自定义回测
# 按提示输入参数：
#   初始资金: 50000
#   回测时长: 168 (1周)
#   最小收益: 5%
#   手续费: 2.5%

# 3️⃣ 等待回测完成
# 🔄 正在执行... (可能需要1-2分钟)
# ✅ 完成！

# 4️⃣ 选择 4. 查看历史回测结果
# 对比不同参数的回测效果

# 5️⃣ 选择 7. 导出报告
# 生成 PDF/Excel 汇总报告
```

---

### 场景：设置自动化回测

**时间**：5分钟配置，然后自动运行

```bash
# 编辑自动化脚本
cat > auto_backtest.py << 'EOF'
from backtest_scheduler import BacktestScheduler
from backtest_notifier import BacktestNotifier
import time

scheduler = BacktestScheduler()
notifier = BacktestNotifier()

# 每天晚上 22:00 执行回测
scheduler.schedule_daily(hour=22, minute=0, callback=notifier.send_email)

print("✅ 自动化回测已启动")
print("   每天 22:00 自动运行")
print("   结果会通过邮件推送")

scheduler.start()

# 保持程序运行
while True:
    time.sleep(1)
EOF

# 后台运行此脚本
python auto_backtest.py &
```

---

## 📞 需要帮助？

**常见问题排查步骤**：

1. 检查日志文件
   ```bash
   tail -f backtest_logs/backtest_*.log
   ```

2. 验证依赖
   ```bash
   pip list | grep -E "pandas|matplotlib|numpy"
   ```

3. 检查数据文件
   ```bash
   wc -l opportunities.csv
   head -3 opportunities.csv
   ```

4. 运行诊断脚本
   ```bash
   python debug_test.py
   ```

---

**祝你回测顺利！🚀**

有问题欢迎反馈！
