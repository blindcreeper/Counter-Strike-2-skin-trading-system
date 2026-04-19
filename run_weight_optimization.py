#!/usr/bin/env python3
"""
权重优化运行脚本
运行命令: python run_weight_optimization.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.weight_optimizer import WeightOptimizer

def main():
    """主函数"""
    # 指定正确的CSV数据文件路径
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'opportunities.csv')
    optimizer = WeightOptimizer(csv_path=csv_path)

    # 运行优化（默认使用SciPy全局优化，最先进）
    result = optimizer.optimize_weights(method='scipy', max_evaluations=100)

    if result:
        print("\n🎉 权重优化完成！")
        print("建议在 strategy.py 中应用这些权重")
    else:
        print("\n❌ 权重优化失败")

if __name__ == "__main__":
    print("🎯 CS2 量化交易策略权重优化工具")
    print("=" * 50)
    main()