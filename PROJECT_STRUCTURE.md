# 📁 项目结构说明

## 当前优化后的结构

```
d:\Pythonprojectcode/
├── src/                          # 核心源代码
│   ├── main.py                  # 主程序入口
│   ├── api_client.py            # API客户端
│   ├── database.py              # 数据库操作
│   ├── strategy.py              # 交易策略
│   ├── backtest_engine.py       # 回测引擎 ⭐
│   ├── backtest_db.py           # 回测数据库
│   ├── backtest_scheduler.py    # 回测调度器 ⭐
│   ├── backtest_visualizer.py   # 回测可视化 ⭐
│   ├── backtest_notifier.py     # 回测通知 ⭐
│   └── ...
│
├── config/                       # 配置文件
│   ├── __init__.py
│   ├── config.py                # 主配置
│   └── backtest_config.py       # 回测配置
│
├── scripts/                      # 脚本工具
│   ├── backtest_quick.py        # 快速回测
│   ├── run_backtest.py          # 完整回测
│   ├── auto_backtest.py         # 自动回测
│   └── ...
│
├── data/                         # 数据文件
│   ├── backtest.csv
│   ├── csqaq_id_map.json
│   ├── steam_items_database.json
│   └── low_sales_blacklist.txt
│
├── databases/                    # 数据库存储
│   ├── cs2_quant.db
│   ├── backtest_history.db
│   └── ...
│
├── output/                       # 输出结果
│   ├── backtest_results/        # 回测结果
│   └── backtest_logs/           # 回测日志
│
├── docs/                         # 文档
│   ├── BACKTEST_GUIDE_CN.md
│   ├── BACKTEST_README.md
│   └── UPGRADE_SUMMARY.md
│
├── tests/                        # 单元测试（可选）
│
├── logs/                         # 运行日志（可选）
│
├── docker-compose.yml           # Docker编排
├── Dockerfile                   # Docker镜像
├── entrypoint.sh                # 容器入口脚本
├── requirements.txt             # Python依赖
├── .env.example                 # 环境配置模板
├── README.md                    # 项目说明
├── QUICKSTART.md                # 快速开始
└── DIRECTORY_GUIDE.md           # 目录指南

```

## 删除的内容

- ❌ `versions/001/` - 旧版本已删除
- ❌ `versions/` - 版本目录已优化，现在所有代码在根目录

## 改进优势

✅ **更清晰的结构** - 一级代码直接在项目根目录  
✅ **便于开发** - 快速访问所有核心模块  
✅ **Docker友好** - 启动脚本直接在根目录  
✅ **单版本维护** - 只维护最新版本v2.0  
✅ **标准化布局** - 符合Python项目最佳实践

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 快速回测
python scripts/backtest_quick.py quick

# 3. 查看结果
# 打开 output/backtest_results/ 目录
```

## Docker部署

```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```
