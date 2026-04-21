# 📁 项目目录结构说明

## 概览

```
Pythonprojectcode/
│
├── 🔧 环境和配置
│   ├── .venv/                    # Python 虚拟环境
│   ├── requirements.txt          # Python 依赖（根目录）
│   └── README.md                 # 项目说明（根目录）
│
├── 📦 版本管理（versions/）
│   ├── 001/                      # v1.0 - 初始版本（基础Reiss理论）
│   │   ├── config.py             # API密钥配置
│   │   ├── api_client.py         # API客户端
│   │   ├── strategy.py           # 交易策略
│   │   ├── database.py           # 数据库操作
│   │   ├── main.py               # 主程序
│   │   └── ...
│   │
│   └── 002/                      # ⭐ v2.0 - 推荐版本（完整回测系统）
│       ├── src/                  # 核心代码
│       │   ├── backtest_engine.py     # 回测引擎
│       │   ├── backtest_db.py         # 数据库
│       │   ├── backtest_visualizer.py # 可视化
│       │   ├── backtest_scheduler.py  # 定时任务
│       │   ├── backtest_notifier.py   # 通知系统
│       │   ├── main.py                # 实时扫描
│       │   └── ...
│       │
│       ├── scripts/              # 可执行脚本
│       │   ├── backtest_quick.py      # 快速回测⭐
│       │   ├── run_backtest.py        # 交互式菜单
│       │   └── auto_backtest.py       # 定时任务
│       │
│       ├── config/               # 配置文件
│       │   ├── config.py              # API配置
│       │   └── backtest_config.py     # 回测配置
│       │
│       ├── data/                 # 数据文件
│       │   ├── opportunities.csv      # 交易数据
│       │   ├── backtest.csv           # 样本数据
│       │   └── csqaq_id_map.json      # 目标映射
│       │
│       ├── output/               # 输出结果
│       │   ├── backtest_results/      # 图表
│       │   └── backtest_logs/         # 日志
│       │
│       ├── docs/                 # 文档
│       │   ├── BACKTEST_README.md     # 功能说明
│       │   ├── BACKTEST_GUIDE_CN.md   # 使用指南
│       │   └── UPGRADE_SUMMARY.md     # 版本升级
│       │
│       ├── Dockerfile            # Docker配置
│       ├── docker-compose.yml    # Docker Compose
│       ├── .env.example          # 环境变量示例
│       ├── entrypoint.sh         # 启动脚本
│       └── README.md             # v2.0说明
│
├── 🔧 工具脚本（src/ - 根目录工具）
│   ├── aihelp_vision.py          # AI视觉工具
│   ├── refiner.py                # 精选报告工具
│   ├── check_db.py               # 数据库检查
│   ├── debug_test.py             # 调试测试
│   └── testchart.py              # 图表测试
│
├── 📊 数据文件（data/）
│   ├── opportunities.csv         # 交易机会
│   ├── csqaq_id_map.json         # 目标映射（~2.4MB）
│   ├── steam_items_database.json # Steam数据库（~24MB）
│   ├── data.txt                  # 原始数据（~3.7MB）
│   └── low_sales_blacklist.txt   # 黑名单（~206KB）
│
├── 💾 数据库（databases/）
│   ├── backtest_history.db       # 回测历史
│   ├── cs2_quant.db              # 量化交易DB（~1.9MB）
│   └── market_trends.db          # 市场趋势
│
├── 📁 输出结果（output/）
│   ├── backtest_charts/          # 历史图表
│   └── backtest_logs/            # 历史日志
│
└── 📚 文档（docs/ - 暂空，可存放额外文档）
```

---

## 📍 常用路径

### 立即使用（推荐新手）
```bash
cd versions/002

# 快速回测
python scripts/backtest_quick.py quick

# 查看结果
open output/backtest_results/
```

### 数据文件位置
```
根目录/data/
├── opportunities.csv           # 当前回测用数据
├── steam_items_database.json   # Steam数据库
├── csqaq_id_map.json           # 目标ID映射
└── low_sales_blacklist.txt     # 低销量黑名单
```

### 回测结果位置
```
versions/002/output/
├── backtest_results/           # 图表文件
│   ├── account_curve_*.png
│   ├── win_lose_*.png
│   ├── drawdown_*.png
│   ├── cumulative_*.png
│   ├── metrics_summary_*.png
│   └── backtest_results.db
└── backtest_logs/              # 执行日志
    └── backtest_*.log
```

---

## 🔗 目录说明

### versions/ 版本管理
- **001/** - 第一版本，使用 Reiss 理论
- **002/** - 第二版本（推荐），功能完整的企业级系统

### src/ 工具脚本（根目录）
这些是与 002 版本配合的实用工具：
- `aihelp_vision.py` - AI 视觉识别辅助
- `refiner.py` - 精选交易报告
- `check_db.py` - 检查数据库完整性
- `debug_test.py` - 调试与测试

### data/ 数据文件
存储所有外部数据：
- **opportunities.csv** - 主要数据源
- **steam_items_database.json** - 完整物料库（大文件）
- **csqaq_id_map.json** - 国内平台目标映射
- **low_sales_blacklist.txt** - 售量低的物品黑名单

### databases/ 数据库
所有 SQLite 数据库文件：
- `cs2_quant.db` - 量化系统主数据库
- `backtest_history.db` - 回测历史记录
- `market_trends.db` - 市场趋势分析

### output/ 输出结果
所有执行结果存储位置：
- 已完成的图表和日志

---

## 💡 使用建议

### 第一次使用
```bash
cd versions/002
python scripts/backtest_quick.py quick
```

### 修改配置
```bash
# 编辑回测参数
nano versions/002/config/backtest_config.py

# 重新运行
python versions/002/scripts/backtest_quick.py quick
```

### Docker 部署
```bash
cd versions/002
docker-compose up -d
```

### 访问数据
```bash
# 查看交易数据
cat data/opportunities.csv

# 查看已完成的回测
sqlite3 databases/backtest_history.db "SELECT * FROM backtest_records;"
```

---

## 📦 磁盘使用量

| 目录 | 大小 | 说明 |
|------|------|------|
| `.venv/` | ~500MB | Python虚拟环境 |
| `data/` | ~34MB | 数据文件 |
| `databases/` | ~2.5MB | 数据库 |
| `versions/002/` | ~5-10MB | 代码和文档 |
| `output/` | 动态增长 | 回测结果 |
| **总计** | ~550MB | 不含虚拟环境 |

---

## 🎯 快速导航

| 任务 | 路径 |
|------|------|
| 快速回测 | `versions/002/scripts/backtest_quick.py` |
| 完整菜单 | `versions/002/scripts/run_backtest.py` |
| 实时扫描 | `versions/002/src/main.py` |
| 配置修改 | `versions/002/config/` |
| 查看结果 | `versions/002/output/backtest_results/` |
| Docker部署 | `versions/002/Dockerfile` |
| 使用文档 | `versions/002/docs/BACKTEST_GUIDE_CN.md` |
| 数据源 | `data/opportunities.csv` |

---

## 🔧 维护提示

### 定期清理
```bash
# 清理旧的回测结果
rm -rf versions/002/output/backtest_results/*.png
rm -rf versions/002/output/backtest_logs/*.log

# 清理 Python 缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 备份重要文件
```bash
# 备份数据库和配置
cp -r databases/ backups/databases_$(date +%Y%m%d)/
cp -r versions/002/config/ backups/config_$(date +%Y%m%d)/
```

### 更新数据
```bash
# 定期运行扫描器更新 opportunities.csv
cd versions/002
python src/main.py  # 让它跑几分钟/几小时
```

---

**项目整理完成！结构清晰，使用方便。🎉**

最后更新：2026-04-04
