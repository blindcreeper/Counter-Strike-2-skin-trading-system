# 工程文件夹结构说明

本文档说明当前项目根目录各文件夹/文件的作用，以及日常运行时重点关注的位置。

## 根目录总览

```text
Pythonprojectcode/
├── config/                # 全局配置
├── src/                   # 核心业务代码（扫描、策略、回测引擎）
├── scripts/               # 运行入口脚本（快速回测、定时回测等）
├── tools/temp/            # 临时测试脚本（不参与主流程）
├── data/                  # 原始与映射数据（JSON/CSV）
├── output/                # 输出目录（日志、回测产物）
├── backtest_logs/         # 本地回测报告与日志（运行时生成）
├── docs/                  # 额外文档
├── .venv/                 # Python 虚拟环境
├── opportunities.csv      # 实时扫描输出的机会数据（回测输入）
├── start_services.ps1     # 一键启动 main + auto_backtest
├── Dockerfile             # Docker 镜像构建
├── docker-compose.yml     # 容器编排
└── requirements.txt       # Python 依赖
```

## 目录说明

### `config/`
- `config.py`：主配置，包含 API、策略阈值、数据库/文件路径等。
- `app_config.json`：总配置文件，适合统一管理部署参数。
- `backtest_config.py`：回测扩展配置（与主配置合并使用）。
- 读取优先级通常为：**环境变量 > app_config.json > 默认值**。

### `src/`（核心代码）
- `main.py`：实时扫描主程序，持续抓取机会并写入 `opportunities.csv`。
- `api_client.py`：第三方平台 API 请求封装。
- `database.py`：主交易相关 SQLite 数据读写。
- `strategy.py`：机会打分与 BUY/WAIT 等动作判断。
- `backtest_engine.py`：回测加载、模拟交易、统计指标计算。
- `backtest_db.py`：回测结果入库。
- `backtest_notifier.py`：邮件/钉钉通知、报告导出。
- `backtest_scheduler.py`：回测调度执行流程。
- `backtest_visualizer.py`：回测图表输出。

### `scripts/`（运行入口）
- `backtest_quick.py`：单次快速回测（支持读取钉钉 webhook 并发送报告）。
- `run_backtest.py`：交互式回测菜单入口。
- `auto_backtest.py`：定时回测常驻进程（按 `SCHEDULE_*` 配置执行）。
- `weight_optimizer.py`：权重优化相关脚本。

### `tools/temp/`
- 存放临时调试/验证脚本，避免污染根目录与核心业务目录。
- 当前示例：
  - `test_dingtalk.py`：测试钉钉 webhook。
  - `debug_test.py`：测试 SteamDT 接口。
  - `testchart.py`：测试图表历史数据接口。

### `data/`
- 存放映射表、原始样本、辅助数据（如 `csqaq_id_map.json`）。
- 可被 `main.py` 和回测脚本读取，不建议手动改动结构。

### `output/`
- 存放运行中产生的标准化输出（如 `output/backtest_logs/`）。
- 部署到服务器或 Docker 时建议挂载持久化。

### `backtest_logs/`
- 本地回测报告 JSON、日志文件等（运行脚本后自动生成）。
- 用于排错和复盘。

## 关键运行链路

- 实时采集：`python src/main.py`
- 单次回测：`python scripts/backtest_quick.py quick`
- 定时回测：`python scripts/auto_backtest.py`
- 一键双进程：`.\start_services.ps1`

## 部署建议

- 生产环境使用环境变量管理敏感配置（API key、webhook）。
- `main.py` 与 `auto_backtest.py` 分开进程运行，互不阻塞。
- 定期备份 `opportunities.csv`、SQLite 数据库和 `output/` 目录。
