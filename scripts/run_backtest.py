"""
完整回测系统入口 - 集成所有模块，提供简洁的运行接口
"""

import os
import sys
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backtest_engine import BacktestEngine
from backtest_db import BacktestDatabase
from backtest_visualizer import BacktestVisualizer
from backtest_notifier import BacktestNotifier
from backtest_scheduler import BacktestScheduler, BacktestRunner


class CompleteBacktestSystem:
    """完整的回测系统"""
    
    def __init__(self):
        self.engine = BacktestEngine()
        self.db = BacktestDatabase()
        self.visualizer = BacktestVisualizer()
        self.notifier = BacktestNotifier()
        self.runner = BacktestRunner(self.engine, self.notifier, self.visualizer, self.db)
        self.scheduler = BacktestScheduler(self.run_backtest)
    
    def run_backtest(self, hours_back=72, initial_balance=10000, 
                     enable_charts=True, enable_email=False, email_config=None,
                     enable_dingtalk=False, dingtalk_webhook=None):
        """执行单次回测"""
        return self.runner.run_full_backtest(
            hours_back=hours_back,
            initial_balance=initial_balance,
            enable_charts=enable_charts,
            enable_email=enable_email,
            email_config=email_config,
            enable_dingtalk=enable_dingtalk,
            dingtalk_webhook=dingtalk_webhook
        )
    
    def start_auto_backtest(self, schedule_type='daily', schedule_param=22):
        """启动自动回测"""
        if schedule_type == 'daily':
            hour = schedule_param
            self.scheduler.schedule_daily(hour=hour, minute=0)
        elif schedule_type == 'hourly':
            self.scheduler.schedule_hourly(minute=schedule_param)
        elif schedule_type == 'hours':
            self.scheduler.schedule_every_n_hours(hours=schedule_param)
        elif schedule_type == 'minutes':
            self.scheduler.schedule_every_n_minutes(minutes=schedule_param)
        
        self.scheduler.start()
    
    def stop_auto_backtest(self):
        """停止自动回测"""
        self.scheduler.stop()
    
    def view_backtest_history(self, limit=10):
        """查看回测历史"""
        history = self.db.get_backtest_history(limit=limit)
        
        if not history:
            print("❌ 没有回测历史记录")
            return
        
        print("\n" + "="*100)
        print("📊 回测历史记录（最近 {} 次）".format(len(history)).center(100))
        print("="*100)
        
        for i, record in enumerate(history, 1):
            status = "✅" if record['total_return'] > 0 else "❌"
            print(f"{status} [{i:2d}] {record['backtest_date']:<20} | "
                  f"收益: {record['total_profit']:7.2f}元 | "
                  f"收益率: {record['total_return']:7.2%} | "
                  f"胜率: {record['win_rate']:6.2%} | "
                  f"最大回撤: {record['max_drawdown']:7.2%} | "
                  f"夏普: {record['sharpe_ratio']:6.2f}")
        
        print("="*100 + "\n")
    
    def view_backtest_statistics(self, days=7):
        """查看指定天数的策略统计"""
        stats = self.db.get_statistics(days=days)
        
        if not stats:
            print(f"❌ 过去 {days} 天内没有回测记录")
            return
        
        print("\n" + "="*60)
        print(f"📈 最近 {days} 天回测统计".center(60))
        print("="*60)
        print(f"回测次数:        {stats['count']:6d}")
        print(f"平均收益率:      {stats['avg_return']:6.2%}")
        print(f"平均胜率:        {stats['avg_win_rate']:6.2%}")
        print(f"平均最大回撤:    {stats['avg_drawdown']:6.2%}")
        print(f"累计收益:        ¥{stats['total_profit']:6.2f}")
        print("="*60 + "\n")
    
    def compare_recent_backtests(self, count=5):
        """对比最近N次回测"""
        history = self.db.get_backtest_history(limit=count)
        
        if len(history) < 2:
            print("⚠️  需要至少2次回测记录进行对比")
            return
        
        import pandas as pd
        df = pd.DataFrame(history)
        
        print("\n" + "="*100)
        print(f"📊 最近 {count} 次回测对比".center(100))
        print("="*100)
        
        # 打印表格
        for _, row in df.iterrows():
            status = "✅" if row['total_return'] > 0 else "❌"
            print(f"{status} {row['backtest_date']:<20} | "
                  f"收益:{row['total_profit']:>8.2f}元 | "
                  f"收益率:{row['total_return']:>7.2%} | "
                  f"胜率:{row['win_rate']:>6.2%} | "
                  f"回撤:{row['max_drawdown']:>7.2%}")
        
        print("\n平均指标:")
        print(f"平均收益率:      {df['total_return'].mean():6.2%}")
        print(f"平均胜率:        {df['win_rate'].mean():6.2%}")
        print(f"平均最大回撤:    {df['max_drawdown'].mean():6.2%}")
        print("="*100 + "\n")


def main():
    """主程序"""
    print("""
╔════════════════════════════════════════════════════════════╗
║     CS2 量化交易系统 - 完整虚拟回测系统 v2.0               ║
║                                                            ║
║  功能：                                                    ║
║  ✓ 虚拟资金模拟       - 真实交易环境模拟                   ║
║  ✓ 详细性能指标       - 胜率、回撤、夏普比等              ║
║  ✓ 数据库持久化       - 保存历史回测记录                   ║
║  ✓ 可视化图表展示     - 收益曲线、风险指标等              ║
║  ✓ 邮件/通知提醒      - 关键指标自动通知                   ║
║  ✓ 自动化定时运行     - 支持多种调度方式                   ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    system = CompleteBacktestSystem()
    
    while True:
        print("\n主菜单 - 选择操作:")
        print("1. 执行单次回测（72小时机会数据）")
        print("2. 执行自定义回测（指定时间范围和初始资金）")
        print("3. 启动自动每日回测（每天22:00）")
        print("4. 启动自动每小时回测")
        print("5. 查看回测历史")
        print("6. 查看回测统计（7天）")
        print("7. 对比最近5次回测")
        print("8. 停止自动回测")
        print("9. 退出程序")
        
        choice = input("\n请选择 (1-9): ").strip()
        
        try:
            if choice == '1':
                print("\n▶️  开始执行单次回测...")
                system.run_backtest(hours_back=72, initial_balance=10000, enable_charts=True)
                
            elif choice == '2':
                hours = int(input("请输入时间范围（小时，默认72）: ") or "72")
                balance = float(input("请输入初始资金（默认10000元）: ") or "10000")
                print(f"\n▶️  开始执行回测 (时间范围: {hours}h, 初始资金: ¥{balance})")
                system.run_backtest(hours_back=hours, initial_balance=balance, enable_charts=True)
                
            elif choice == '3':
                hour = int(input("请输入每天执行时间（小时，0-23，默认22）: ") or "22")
                print(f"\n✅ 已设置每天 {hour:02d}:00 自动执行回测")
                system.start_auto_backtest(schedule_type='daily', schedule_param=hour)
                print("🚀 自动回测已启动（按 Ctrl+C 停止）")
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    system.stop_auto_backtest()
                
            elif choice == '4':
                interval = int(input("请输入间隔时间（分钟，默认30）: ") or "30")
                print(f"\n✅ 已设置每 {interval} 分钟自动执行回测")
                system.start_auto_backtest(schedule_type='minutes', schedule_param=interval)
                print("🚀 自动回测已启动（按 Ctrl+C 停止）")
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    system.stop_auto_backtest()
                
            elif choice == '5':
                limit = int(input("查看最近N次回测（默认10）: ") or "10")
                system.view_backtest_history(limit=limit)
                
            elif choice == '6':
                days = int(input("查看最近N天的统计（默认7）: ") or "7")
                system.view_backtest_statistics(days=days)
                
            elif choice == '7':
                count = int(input("对比最近N次回测（默认5）: ") or "5")
                system.compare_recent_backtests(count=count)
                
            elif choice == '8':
                system.stop_auto_backtest()
                
            elif choice == '9':
                print("\n👋 感谢使用，再见！")
                break
                
            else:
                print("❌ 无效选择，请重试")
                
        except KeyboardInterrupt:
            print("\n⏹️  操作已取消")
        except Exception as e:
            print(f"❌ 出错: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
