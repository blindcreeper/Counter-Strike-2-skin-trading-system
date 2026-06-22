"""
回测自动调度模块 - 定时自动执行回测
"""

import schedule
import time
from datetime import datetime
import threading
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
from analyze_signal_factors import analyze_signal_factors


class BacktestScheduler:
    """回测调度器 - 支持定时和循环运行"""
    
    def __init__(self, backtest_func):
        self.backtest_func = backtest_func
        self.is_running = False
        self.thread = None
    
    def schedule_daily(self, hour=22, minute=0):
        """每天定时执行回测"""
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.backtest_func)
        print(f"✅ 已设置每天 {hour:02d}:{minute:02d} 自动执行回测")
    
    def schedule_hourly(self, minute=0):
        """每小时执行回测"""
        schedule.every().hour.at(f":{minute:02d}").do(self.backtest_func)
        print(f"✅ 已设置每小时第 {minute:02d} 分钟执行回测")
    
    def schedule_every_n_hours(self, hours=6):
        """每N小时执行回测"""
        schedule.every(hours).hours.do(self.backtest_func)
        print(f"✅ 已设置每 {hours} 小时执行回测")
    
    def schedule_every_n_minutes(self, minutes=30):
        """每N分钟执行回测"""
        schedule.every(minutes).minutes.do(self.backtest_func)
        print(f"✅ 已设置每 {minutes} 分钟执行回测")
    
    def schedule_interval_during_market_hours(self, interval_minutes=30):
        """
        交易时段内每N分钟执行回测
        CS2市场基本上24小时交易，这里简单演示
        """
        schedule.every(interval_minutes).minutes.do(self.backtest_func)
        print(f"✅ 已设置市场时段内每 {interval_minutes} 分钟执行回测")
    
    def start(self):
        """启动调度线程"""
        if self.is_running:
            print("⚠️  调度器已在运行")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        print("🚀 回测调度器已启动（后台运行）")
    
    def _run_scheduler(self):
        """调度循环"""
        print(f"⏰ 调度器启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                print(f"❌ 调度执行出错: {str(e)}")
                time.sleep(60)
    
    def stop(self):
        """停止调度"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("⏹️  回测调度已停止")
    
    def get_next_run_time(self):
        """获取下一次运行时间"""
        if schedule.idle_seconds() is None:
            return "未设置任何任务"
        
        next_run = schedule.next_run()
        if next_run:
            return next_run.strftime("%Y-%m-%d %H:%M:%S")
        return "无下一次任务"
    
    def get_job_count(self):
        """获取任务数量"""
        return len(schedule.jobs)
    
    def clear_all(self):
        """清除所有任务"""
        schedule.clear()
        print("✅ 已清除所有定时任务")


class BacktestRunner:
    """回测运行器 - 便利函数"""
    
    def __init__(self, engine, notifier, visualizer, db):
        self.engine = engine
        self.notifier = notifier
        self.visualizer = visualizer
        self.db = db
    
    def run_full_backtest(self, hours_back=72, initial_balance=10000, 
                         enable_charts=True, enable_email=False, email_config=None,
                         enable_dingtalk=False, dingtalk_webhook=None):
        """执行完整回测流程"""
        
        try:
            self.notifier.log_backtest_start(initial_balance, 0)
            
            # 1. 加载机会数据
            opportunities = self.engine.load_opportunities(hours_back=hours_back)
            
            self.notifier.log("INFO", f"📊 加载了 {len(opportunities)} 个交易机会")
            
            # 2. 运行模拟
            metrics = self.engine.run_simulation(opportunities, initial_balance=initial_balance)
            
            # 3. 保存到数据库
            backtest_id = self.db.save_backtest(
                metrics,
                self.engine.backtest_results,
                metrics.get('account_values', [])
            )
            self.notifier.log("INFO", f"💾 回测数据已保存 (ID: {backtest_id})")
            
            # 4. 打印详细报告
            self.engine.print_report(metrics)
            
            # 5. 生成图表
            if enable_charts:
                self.notifier.log("INFO", "📈 正在生成图表...")
                
                account_values = metrics.get('account_values', [])
                returns = [t['profit_rate'] for t in self.engine.backtest_results]
                
                self.visualizer.plot_account_curve(account_values, initial_balance)
                self.visualizer.plot_returns_distribution(returns)
                self.visualizer.plot_drawdown_curve(account_values, initial_balance)
                self.visualizer.plot_cumulative_returns(returns)
                self.visualizer.plot_metrics_summary(metrics)
                
                self.notifier.log("INFO", f"✅ 图表已生成到 {self.visualizer.output_dir}")
            
            # 6. 发送邮件通知
            if enable_email and email_config:
                self.notifier.send_email(
                    email_config['recipient'],
                    "CS2量化回测完成",
                    f"本次回测共执行 {metrics['total_trades']} 笔交易",
                    metrics,
                    email_config['smtp']
                )
            
            # 7. 生成 HTML 回测报告 & 获取历史趋势
            recent = self.db.get_backtest_history(limit=6)[1:]  # 跳过本次
            html_url = ""
            try:
                from backtest_report import generate_html, save_report
                html = generate_html(
                    metrics,
                    trades=self.engine.backtest_results,
                    history=recent,
                )
                _, latest_path = save_report(html)
                status_port = 8199
                html_url = f"http://38.207.171.210:{status_port}/backtest"
                self.notifier.log("INFO", f"📄 HTML 报告: {html_url}")
            except Exception as e:
                self.notifier.log("WARN", f"HTML 报告生成失败: {e}")

            # 8. 发送钉钉通知
            if enable_dingtalk and dingtalk_webhook:
                factor_report = analyze_signal_factors(days=max(7, int(hours_back / 24)))
                self.notifier.send_dingtalk(
                    dingtalk_webhook,
                    metrics,
                    trades=self.engine.backtest_results,
                    factor_report=factor_report,
                    recent_history=recent,
                    report_url=html_url,
                )
            
            # 8. 导出报告
            self.notifier.export_report(metrics, self.engine.backtest_results)
            
            self.notifier.log_backtest_end(metrics)
            
            return metrics
            
        except Exception as e:
            self.notifier.log("ERROR", f"❌ 回测执行失败: {str(e)}")
            raise
