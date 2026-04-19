#!/bin/bash

# CS2 皮肤量化回测系统 - Docker 入口脚本
# 用法: ./entrypoint.sh [quick|full|scheduler|main]

set -e  # 任何命令失败都退出

# 设置日志文件
LOG_DIR="/app/output/backtest_logs"
LOG_FILE="$LOG_DIR/backtest_$(date +%Y%m%d_%H%M%S).log"

# 确保输出目录存在
mkdir -p "$LOG_DIR"
mkdir -p "/app/output/backtest_results"

# 导出 Python 路径
export PYTHONPATH="${PYTHONPATH:-/app/src}"

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 错误处理
error_exit() {
    log "❌ 错误: $1"
    exit 1
}

log "🚀 CS2 皮肤量化回测系统 - Docker 启动"
log "工作目录: $(pwd)"
log "Python 版本: $(python --version)"

# 获取从命令行传递的参数
MODE="${1:-quick}"

case "$MODE" in
    quick)
        log "📊 执行快速回测模式..."
        cd /app
        python ./scripts/backtest_quick.py quick 2>&1 | tee -a "$LOG_FILE"
        log "✅ 快速回测完成"
        ;;
    
    full)
        log "📊 执行完整回测模式..."
        cd /app
        python ./scripts/run_backtest.py 2>&1 | tee -a "$LOG_FILE"
        log "✅ 完整回测完成"
        ;;
    
    scheduler)
        log "⏰ 启动定时任务模式（后台运行）..."
        cd /app
        log "🔄 每天 22:00 自动执行回测"
        log "按 Ctrl+C 停止..."
        python -c "
import sys
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app/scripts')

try:
    from auto_backtest import main
    main()
except ImportError:
    print('⚠️  auto_backtest.py 未找到，请确保文件存在')
    print('创建一个简单的定时任务...')
    import schedule
    import time
    from datetime import datetime
    from backtest_quick import run_quick_backtest
    
    schedule.every().day.at('22:00').do(run_quick_backtest)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
" 2>&1 | tee -a "$LOG_FILE"
        ;;
    
    main)
        log "🎯 运行实时扫描器（main.py）..."
        cd /app
        python ./src/main.py 2>&1 | tee -a "$LOG_FILE"
        log "✅ 扫描器运行完成"
        ;;
    
    bash)
        log "📝 进入交互式 Bash..."
        /bin/bash
        ;;
    
    *)
        log "❌ 未知模式: $MODE"
        log "支持的模式:"
        log "  quick      - 快速回测（72小时数据）"
        log "  full       - 完整交互式回测"
        log "  scheduler  - 自动定时任务"
        log "  main       - 实时市场扫描"
        log "  bash       - 交互式 Shell"
        exit 1
        ;;
esac

log "✅ 执行完成！"
