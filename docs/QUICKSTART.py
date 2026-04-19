"""
一分钟快速开始指南
"""

# ============================================================================
# ✨ 5种最常用的使用方法
# ============================================================================

# 方法1️⃣：最简单 - 直接运行快速脚本（推荐新手）
# 命令行执行：
#   python backtest_quick.py quick
# 
# 输出：
# ✅ 完整的虚拟回测报告
# 📊 5张专业图表（自动保存到 backtest_charts/）
# 📄 回测数据保存到数据库


# 方法2️⃣：交互菜单 - 适合需要定制的用户
# 命令行执行：
#   python run_backtest.py
#
# 然后选择：
# 1 = 单次回测
# 3 = 启动每日自动回测
# 5 = 查看历史记录


# 方法3️⃣：编码方式 - 适合集成到其他项目
if __name__ == "__main__":
    from run_backtest import CompleteBacktestSystem
    
    system = CompleteBacktestSystem()
    
    # 运行一次完整回测（72小时数据）
    metrics = system.run_backtest(
        hours_back=72,          # 回溯72小时
        initial_balance=10000,  # 虚拟资金10000元
        enable_charts=True      # 生成图表
    )
    
    # 查看历史
    system.view_backtest_history(limit=20)


# 方法4️⃣：启动自动每日回测
if __name__ == "__main__":
    from run_backtest import CompleteBacktestSystem
    import time
    
    system = CompleteBacktestSystem()
    
    # 每天22:00自动运行回测
    system.start_auto_backtest(schedule_type='daily', schedule_param=22)
    
    # 程序保持运行
    print("✅ 后台自动回测已启动（每天22:00运行）")
    print("🔔 按 Ctrl+C 停止")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        system.stop_auto_backtest()


# 方法5️⃣：查看数据和对比
if __name__ == "__main__":
    from run_backtest import CompleteBacktestSystem
    
    system = CompleteBacktestSystem()
    
    # 查看最近10次回测
    print("📊 最近10次回测：")
    system.view_backtest_history(limit=10)
    
    # 查看最近7天的整体统计
    print("\n📈 最近7天统计：")
    system.view_backtest_statistics(days=7)
    
    # 对比最近5次回测
    print("\n📉 对比最近5次回测：")
    system.compare_recent_backtests(count=5)


# ============================================================================
# 📊 输出目录结构
# ============================================================================

"""
执行回测后会生成以下文件：

002/
├── backtest_charts/              ← 所有图表（5种）
│   ├── account_curve_*.png       ← 账户净值曲线
│   ├── returns_dist_*.png        ← 收益率分布
│   ├── drawdown_*.png            ← 回撤曲线
│   ├── cumulative_returns_*.png  ← 累积收益
│   └── metrics_summary_*.png     ← 指标汇总
│
├── backtest_logs/                ← 所有日志
│   └── backtest_20260403.log     ← 当日日志
│
├── backtest_history.db           ← SQLite数据库（历史记录）
│
└── *.json                         ← JSON格式报告
"""


# ============================================================================
# 🔑 关键性能指标解释
# ============================================================================

"""
💡 回测报告中的关键指标：

账户指标:
  • 初始资金 10,000 元 → 最终资金 10,523 元
  • 总收益 523 元，收益率 5.23%

交易指标:
  • 总交易数 48 笔
  • 胜率 62.50%（获利30笔，亏损18笔）

性能指标:
  • 平均单笔利润 ¥10.91 元
  • 最佳单笔 +6.50%
  • 最差单笔 -4.20%

风险指标:
  • 最大回撤 -8.50%（账户最大下跌幅度）
  • 夏普比率 1.42（风险调整后收益）

✅ 好的回测结果标准：
  • 胜率 > 55%
  • 收益率 > 5%
  • 最大回撤 < -20%
  • 夏普比率 > 1.0
"""


# ============================================================================
# ⚡ 常用命令速查
# ============================================================================

"""
# 快速回测
python backtest_quick.py quick

# 7天回测
python backtest_quick.py extended

# 查看历史
python backtest_quick.py history

# 完整菜单
python run_backtest.py

# Python 编码调用
python
>>> from run_backtest import CompleteBacktestSystem
>>> s = CompleteBacktestSystem()
>>> s.run_backtest()
"""


# ============================================================================
# 🛠️ 依赖安装
# ============================================================================

"""
首次使用需要安装依赖：

pip install -r requirements.txt

或者单独安装：

pip install pandas numpy matplotlib schedule
"""


# ============================================================================
# 📞 如果出现问题
# ============================================================================

"""
❌ ImportError: pandas/numpy/matplotlib

解决：pip install pandas numpy matplotlib schedule

❌ ModuleNotFoundError: config

解决：确保在 002/ 目录下运行脚本
cd 002/
python backtest_quick.py quick

❌ No such file: opportunities.csv

解决：需要先运行主程序产生交易数据
python main.py

❌ database is locked

解决：关闭其他访问数据库的程序

✅ 更多帮助：
查看 BACKTEST_README.md 获取完整文档
"""


print("""

╔════════════════════════════════════════════════════════════╗
║                     🚀 快速开始要点                        ║
╚════════════════════════════════════════════════════════════╝

1️⃣  最快上手：
    python backtest_quick.py quick

2️⃣  查看历史：
    python backtest_quick.py history

3️⃣  每日自动：
    python run_backtest.py
    选择菜单 3

4️⃣  编程使用：
    from run_backtest import CompleteBacktestSystem
    s = CompleteBacktestSystem()
    s.run_backtest(hours_back=72)

📊 输出：
    ✅ 详细性能报告
    📈 5张专业图表
    💾 回测数据库
    📝 执行日志

📖 完整文档：BACKTEST_README.md

""")
