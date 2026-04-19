"""
回测可视化模块 - 生成趋势图表和分析图
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import os
from datetime import datetime

# 使用中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class BacktestVisualizer:
    """回测可视化工具"""
    
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or "./backtest_charts"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def plot_account_curve(self, account_values, initial_balance=10000, filename=None):
        """绘制账户净值曲线"""
        if not account_values:
            print("⚠️  无账户数据")
            return None
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        x = range(len(account_values))
        ax.plot(x, account_values, linewidth=2, color='#2E86AB', label='账户净值')
        
        # 添加初始资金水平线
        ax.axhline(y=initial_balance, color='gray', linestyle='--', linewidth=1, label='初始资金')
        
        # 添加最高值和最低值
        max_val = max(account_values)
        min_val = min(account_values)
        ax.scatter([account_values.index(max_val)], [max_val], color='green', s=100, zorder=5, label=f'最高: ¥{max_val:.2f}')
        ax.scatter([account_values.index(min_val)], [min_val], color='red', s=100, zorder=5, label=f'最低: ¥{min_val:.2f}')
        
        ax.fill_between(x, account_values, initial_balance, alpha=0.2, color='#2E86AB')
        ax.set_xlabel('交易序列', fontsize=12)
        ax.set_ylabel('账户价值 (¥)', fontsize=12)
        ax.set_title('虚拟账户净值曲线', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # 格式化y轴为货币
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{x:.0f}'))
        
        if filename is None:
            filename = os.path.join(self.output_dir, f"account_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def plot_returns_distribution(self, returns, filename=None):
        """绘制收益率分布直方图"""
        if not returns:
            print("⚠️  无收益数据")
            return None
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 分离正负收益
        positive_returns = [r for r in returns if r > 0]
        negative_returns = [r for r in returns if r <= 0]
        
        bins = 30
        ax.hist(positive_returns, bins=bins, alpha=0.7, color='green', label=f'盈利 ({len(positive_returns)}笔)')
        ax.hist(negative_returns, bins=bins, alpha=0.7, color='red', label=f'亏损 ({len(negative_returns)}笔)')
        
        ax.set_xlabel('收益率', fontsize=12)
        ax.set_ylabel('频数', fontsize=12)
        ax.set_title('交易收益率分布', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # 格式化x轴为百分比
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        if filename is None:
            filename = os.path.join(self.output_dir, f"returns_dist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def plot_drawdown_curve(self, account_values, initial_balance=10000, filename=None):
        """绘制回撤曲线"""
        if not account_values:
            print("⚠️  无数据")
            return None
        
        import numpy as np
        
        # 计算回撤
        cumulative_max = np.maximum.accumulate(account_values)
        drawdown = (account_values - cumulative_max) / cumulative_max
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        x = range(len(drawdown))
        ax.fill_between(x, drawdown, 0, alpha=0.5, color='red')
        ax.plot(x, drawdown, linewidth=2, color='darkred')
        
        ax.set_xlabel('交易序列', fontsize=12)
        ax.set_ylabel('回撤率', fontsize=12)
        ax.set_title('账户回撤曲线', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 格式化y轴为百分比
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        if filename is None:
            filename = os.path.join(self.output_dir, f"drawdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def plot_cumulative_returns(self, returns, filename=None):
        """绘制累积收益曲线"""
        if not returns:
            print("⚠️  无数据")
            return None
        
        import numpy as np
        
        cumulative = np.cumprod(1 + np.array(returns)) - 1
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        x = range(len(cumulative))
        ax.plot(x, cumulative, linewidth=2, color='#2E86AB')
        ax.fill_between(x, cumulative, 0, alpha=0.2, color='#2E86AB')
        
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_xlabel('交易序列', fontsize=12)
        ax.set_ylabel('累积收益率', fontsize=12)
        ax.set_title('累积收益曲线', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 格式化y轴为百分比
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        if filename is None:
            filename = os.path.join(self.output_dir, f"cumulative_returns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def plot_metrics_summary(self, metrics, filename=None):
        """绘制关键指标汇总图"""
        if not metrics or metrics.get('total_trades', 0) == 0:
            print("⚠️  无交易数据，跳过指标汇总图表")
            return None
        
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
            
            # 1. 胜负比例
            win_lose = [metrics.get('winning_trades', 0), metrics.get('losing_trades', 0)]
            if sum(win_lose) > 0:  # 确保有数据
                colors_pie = ['green', 'red']
                ax1.pie(win_lose, labels=['盈利', '亏损'], autopct='%1.1f%%', 
                        startangle=90, colors=colors_pie)
            ax1.set_title('胜负交易比例', fontsize=12, fontweight='bold')
            
            # 2. 收益指标
            returns = [
                metrics.get('avg_return', 0),
                metrics.get('best_return', 0),
                metrics.get('worst_return', 0)
            ]
            labels = ['平均收益', '最佳收益', '最差收益']
            colors_bar = ['blue', 'green', 'red']
            ax2.bar(labels, returns, color=colors_bar, alpha=0.7)
            ax2.set_ylabel('收益率', fontsize=10)
            ax2.set_title('关键收益指标', fontsize=12, fontweight='bold')
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
            
            # 3. 账户变化
            account_change = [
                metrics.get('initial_balance', 10000),
                metrics.get('final_balance', 10000)
            ]
            ax3.bar(['初始资金', '最终资金'], account_change, 
                   color=['gray', 'green' if metrics.get('total_return', 0) > 0 else 'red'], 
                   alpha=0.7)
            ax3.set_ylabel('金额 (¥)', fontsize=10)
            ax3.set_title('账户资金变化', fontsize=12, fontweight='bold')
            ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{x:.0f}'))
            
            # 4. 风险指标
            risk_labels = ['最大回撤', '夏普比率']
            risk_values = [metrics.get('max_drawdown', 0), metrics.get('sharpe_ratio', 0) / 10]
            ax4.bar(risk_labels, risk_values, color=['orange', 'purple'], alpha=0.7)
            ax4.set_ylabel('数值', fontsize=10)
            ax4.set_title('风险指标', fontsize=12, fontweight='bold')
            
            plt.tight_layout()
            
            if filename is None:
                filename = os.path.join(self.output_dir, f"metrics_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            return filename
        except Exception as e:
            print(f"⚠️  指标汇总图表生成失败: {str(e)}")
            return None
    
    def plot_backtest_history(self, history_df, metric='total_return', filename=None):
        """绘制历史回测指标对比"""
        if len(history_df) == 0:
            print("⚠️  无历史数据")
            return None
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        x = range(len(history_df))
        metric_values = history_df[metric].tolist()
        
        colors = ['green' if v > 0 else 'red' for v in metric_values]
        ax.bar(x, metric_values, color=colors, alpha=0.7)
        
        ax.set_xlabel('回测次序', fontsize=12)
        ax.set_ylabel(f'{metric}', fontsize=12)
        ax.set_title(f'历史回测 - {metric}', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        if metric in ['total_return', 'avg_return', 'best_return', 'worst_return', 'win_rate']:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        if filename is None:
            filename = os.path.join(self.output_dir, f"history_{metric}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
