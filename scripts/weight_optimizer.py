"""
权重优化脚本 - 通过回测自动调整策略权重
使用网格搜索或优化算法找到最佳权重组合
"""

import pandas as pd
import numpy as np
import itertools
import os
import sys
from datetime import datetime
from sklearn.model_selection import ParameterGrid
from scipy.optimize import differential_evolution

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from config import CONFIG
from backtest_engine import BacktestEngine
from strategy import QuantStrategy
from database import MarketDB


class WeightOptimizer:
    """权重优化器 - 自动寻找最佳权重组合"""

    def __init__(self, csv_path=None):
        self.csv_path = csv_path or CONFIG.get("LOG_FILE")
        self.base_config = CONFIG.copy()
        self.db = MarketDB(CONFIG.get("DB_NAME"))  # 添加数据库连接

        # 定义权重搜索空间（连续范围，用于scipy优化）
        self.weight_bounds = [
            (0.4, 0.9),   # momentum_weight: 动量因子权重
            (0.8, 1.6),   # spread_weight: 价差权重
            (0.3, 1.0),   # pair_weight: 平台对权重
            (0.2, 0.6),   # price_weight: 价格区间权重
            (0.4, 0.8),   # keyword_weight: 关键词权重
        ]

        # 权重名称映射
        self.weight_names = [
            'momentum_weight', 'spread_weight', 'pair_weight',
            'price_weight', 'keyword_weight'
        ]

        # 离散搜索空间（用于网格和随机搜索的备选方案）
        self.discrete_weight_ranges = {
            'momentum_weight': [0.5, 0.6, 0.7, 0.8],  # 动量因子权重
            'spread_weight': [1.0, 1.2, 1.4],          # 价差权重
            'pair_weight': [0.5, 0.7, 0.9],            # 平台对权重
            'price_weight': [0.3, 0.4, 0.5],           # 价格区间权重
            'keyword_weight': [0.5, 0.6, 0.7],         # 关键词权重
        }

        # 固定权重（暂时不优化）
        self.fixed_weights = {
            'keyword_weights': {
                "MAC-10": 6, "KNIFE": 6, "AWP": 4, "M4A1-S": 3,
                "USP-S": -7, "GLOVES": -8, "AK-47": -3, "GLOCK-18": -2,
            },
            'pair_weights': {
                ("C5", "HALOSKINS"): -16, ("C5", "BUFF"): -11,
                ("HALOSKINS", "YOUPIN"): -9, ("YOUPIN", "BUFF"): 10,
                ("BUFF", "YOUPIN"): 7, ("BUFF", "HALOSKINS"): 6,
                ("YOUPIN", "HALOSKINS"): 5, ("C5", "YOUPIN"): 8,
            }
        }

    def create_strategy_with_weights(self, weights):
        """创建带有指定权重的策略实例"""
        # 创建临时配置
        temp_config = self.base_config.copy()
        temp_config.update(weights)
        temp_config.update(self.fixed_weights)

        # 创建策略实例
        strategy = QuantStrategy(temp_config)

        # 手动设置权重（因为QuantStrategy的__init__中权重是硬编码的）
        strategy.momentum_weight = weights.get('momentum_weight', 0.65)
        strategy.spread_weight = weights.get('spread_weight', 1.15)
        strategy.pair_weight = weights.get('pair_weight', 0.75)
        strategy.price_weight = weights.get('price_weight', 0.35)
        strategy.keyword_weight = weights.get('keyword_weight', 0.6)

        return strategy

    def evaluate_weights(self, weights, opportunities):
        """评估一组权重的性能 - 使用真实的历史数据"""
        try:
            # 创建带权重的策略
            strategy = self.create_strategy_with_weights(weights)

            # 模拟决策过程
            decisions = []
            for opp in opportunities:
                name = opp.get('name', '')

                # 获取真实的历史数据
                item_data = self.db.get_item_analysis_data(name)

                if not item_data or not item_data.get('prices'):
                    # 如果没有历史数据，跳过这个机会
                    continue

                # 准备交易上下文
                trade_ctx = {
                    'name': name,
                    'buy_price': float(opp.get('buy_price', 0)),
                    'sell_price': float(opp.get('sell_price', 0)),
                    'buy_from': opp.get('buy_from', ''),
                    'sell_to': opp.get('sell_to', ''),
                    'net_profit_rate': float(opp.get('profit', '0%').strip('%')) / 100,
                }

                # 分析决策
                result = strategy.analyze(item_data, trade_ctx)
                decisions.append({
                    'opportunity': opp,
                    'decision': result.get('action', 'HOLD'),
                    'score': result.get('score', 0),
                    'profit_rate': trade_ctx['net_profit_rate']
                })

            # 计算性能指标
            buy_decisions = [d for d in decisions if d['decision'] == 'BUY']
            if not buy_decisions:
                return {
                    'total_opportunities': len(decisions),
                    'buy_decisions': 0,
                    'win_rate': 0,
                    'avg_profit': 0,
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'score': -1  # 没有交易的权重给负分
                }

            profits = [d['profit_rate'] for d in buy_decisions]
            win_rate = sum(1 for p in profits if p > 0) / len(profits) if profits else 0
            avg_profit = np.mean(profits) if profits else 0
            total_return = sum(profits) if profits else 0

            # 计算夏普比率（年化）
            if len(profits) > 1:
                returns_std = np.std(profits)
                sharpe_ratio = (np.mean(profits) / returns_std) * np.sqrt(252) if returns_std > 0 else 0
            else:
                sharpe_ratio = 0

            # 计算最大回撤
            cumulative_returns = np.cumsum(profits)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = running_max - cumulative_returns
            max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0

            # 改进的综合评分：使用夏普比率作为主要指标
            # 避免量纲问题和鼓励高频交易的问题
            score = (
                sharpe_ratio * 0.6 +           # 夏普比率权重最高
                total_return * 0.3 +           # 总收益率
                (1 - max_drawdown) * 0.1       # 回撤惩罚（回撤越小分数越高）
            )

            return {
                'total_opportunities': len(decisions),
                'buy_decisions': len(buy_decisions),
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'score': score
            }

        except Exception as e:
            print(f"⚠️  权重评估失败: {weights} | {str(e)}")
            return {'score': -1, 'error': str(e)}

    def grid_search(self, opportunities, max_evaluations=100):
        """网格搜索最佳权重"""
        print(f"\n🔍 开始网格搜索权重优化")
        print(f"   搜索空间大小: {len(list(itertools.product(*self.weight_ranges.values())))}")
        print(f"   最大评估次数: {max_evaluations}")

        # 生成参数网格
        param_grid = list(itertools.product(*self.discrete_weight_ranges.values()))
        param_names = list(self.discrete_weight_ranges.keys())

        results = []
        best_result = None
        best_score = -np.inf

        for i, params in enumerate(param_grid[:max_evaluations]):
            weights = dict(zip(param_names, params))

            print(f"📊 [{i+1:3d}] 测试权重: {weights}")

            # 评估权重
            result = self.evaluate_weights(weights, opportunities)

            if result['score'] > best_score:
                best_score = result['score']
                best_result = {
                    'weights': weights,
                    'metrics': result
                }

            results.append({
                'weights': weights,
                'metrics': result
            })

            # 打印进度
            if (i + 1) % 10 == 0:
                print(f"   进度: {i+1}/{min(len(param_grid), max_evaluations)} | 当前最佳分数: {best_score:.4f}")

        return best_result, results

    def random_search(self, opportunities, max_evaluations=50):
        """随机搜索 - 更高效的优化方法"""
        print(f"\n🎲 开始随机搜索权重优化")
        print(f"   最大评估次数: {max_evaluations}")

        results = []
        best_result = None
        best_score = -np.inf

        for i in range(max_evaluations):
            # 随机生成权重组合
            weights = {}
            for param, values in self.discrete_weight_ranges.items():
                weights[param] = np.random.choice(values)

            print(f"🎯 [{i+1:3d}] 测试权重: {weights}")

            # 评估权重
            result = self.evaluate_weights(weights, opportunities)

            if result['score'] > best_score:
                best_score = result['score']
                best_result = {
                    'weights': weights,
                    'metrics': result
                }

            results.append({
                'weights': weights,
                'metrics': result
            })

            # 打印进度
            if (i + 1) % 10 == 0:
                print(f"   进度: {i+1}/{max_evaluations} | 当前最佳分数: {best_score:.4f}")

        return best_result, results

    def scipy_optimize(self, opportunities, max_evaluations=100):
        """使用scipy.optimize进行全局优化"""
        print(f"\n🧬 开始SciPy全局优化")
        print(f"   最大函数评估次数: {max_evaluations}")

        # 目标函数（最小化负评分）
        def objective_function(weight_array):
            weights = dict(zip(self.weight_names, weight_array))
            result = self.evaluate_weights(weights, opportunities)
            return -result['score']  # 最小化负评分 = 最大化评分

        # 使用差分进化算法进行全局优化
        result = differential_evolution(
            objective_function,
            bounds=self.weight_bounds,
            maxiter=50,  # 最大迭代次数
            popsize=15,  # 种群大小
            mutation=(0.5, 1.0),  # 变异参数
            recombination=0.7,    # 重组参数
            seed=42,  # 随机种子，确保结果可重现
            disp=True,  # 显示优化过程
            polish=True,  # 最终局部优化
        )

        # 提取最优结果
        best_weights = dict(zip(self.weight_names, result.x))
        best_metrics = self.evaluate_weights(best_weights, opportunities)

        print(f"\n🏆 SciPy优化完成")
        print(f"   最优权重: {best_weights}")
        print(f"   最终评分: {best_metrics['score']:.4f}")
        print(f"   函数评估次数: {result.nfev}")

        return {
            'weights': best_weights,
            'metrics': best_metrics,
            'optimizer_result': result
        }, None  # scipy优化不返回所有结果列表

    def optimize_weights(self, method='scipy', max_evaluations=100):
        """主优化函数"""
        print("🚀 开始权重优化流程")
        print(f"   优化方法: {method}")
        print(f"   最大评估次数: {max_evaluations}")

        # 加载历史数据
        engine = BacktestEngine(csv_path=self.csv_path)
        opportunities = engine.load_opportunities(hours_back=168)  # 使用一周数据

        if not opportunities:
            print("❌ 没有足够的回测数据")
            return None

        print(f"✅ 加载到 {len(opportunities)} 个历史机会")

        # 执行优化
        if method == 'grid':
            best_result, all_results = self.grid_search(opportunities, max_evaluations)
        elif method == 'random':
            best_result, all_results = self.random_search(opportunities, max_evaluations)
        elif method == 'scipy':
            best_result, all_results = self.scipy_optimize(opportunities, max_evaluations)
        else:
            print(f"❌ 不支持的优化方法: {method}")
            print("支持的方法: grid, random, scipy")
            return None

        # 输出结果
        if best_result:
            print("\n" + "="*60)
            print("🏆 最佳权重组合")
            print("="*60)
            print(f"权重配置: {best_result['weights']}")
            print(f"性能指标: {best_result['metrics']}")
            print("="*60)

            # 保存到配置文件
            self.save_optimal_weights(best_result['weights'])

        return best_result

    def save_optimal_weights(self, weights):
        """保存最优权重到配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.py')

        # 读取现有配置
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 转换 numpy 类型为普通 Python 类型
        clean_weights = {}
        for key, value in weights.items():
            if hasattr(value, 'item'):  # numpy 类型
                clean_weights[key] = value.item()
            else:
                clean_weights[key] = value

        # 添加权重配置
        weight_config = f"""
# 优化后的权重配置 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
OPTIMIZED_WEIGHTS = {clean_weights}
"""

        # 在文件末尾添加
        if 'OPTIMIZED_WEIGHTS' not in content:
            content += '\n\n' + weight_config

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ 最优权重已保存到 {config_path}")
        else:
            print("ℹ️  配置文件已包含权重配置，请手动更新")


def main():
    """主函数"""
    optimizer = WeightOptimizer()

    # 运行优化（默认使用SciPy全局优化，最先进）
    result = optimizer.optimize_weights(method='scipy', max_evaluations=100)

    if result:
        print("\n🎉 权重优化完成！")
        print("建议在 strategy.py 中应用这些权重")
    else:
        print("\n❌ 权重优化失败")


if __name__ == "__main__":
    main()