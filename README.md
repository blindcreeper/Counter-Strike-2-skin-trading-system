# 🎮 CS2 皮肤量化交易系统

> 完整的自动化量化回测框架 | 实时扫描 + 策略评估 + 云端通知 | 支持本地、Docker、GitHub Actions 部署

## ⚡ 项目概述

CS2 皮肤量化交易系统旨在通过多平台价格扫描、策略评估、历史回测与自动通知，帮助你快速验证皮肤套利策略。

核心能力包括：
- 实时套利机会发现
- 多因子策略评分
- 历史虚拟回测
- 性能指标与图表分析
- 钉钉通知与 GitHub Actions 自动化
- Docker 部署支持

---

## 🎯 核心功能

| 功能 | 说明 |
|------|------|
| 🔍 实时扫描 | 多平台皮肤价格监控，自动检测套利机会 |
| 📊 策略评估 | 基于 Reiss 理论及多因子模型评分 |
| 🏦 虚拟回测 | 历史数据回测，计算收益/最大回撤/胜率等 |
| 📈 可视化 | 自动生成收益曲线、回测图表、性能分析图 |
| 💾 数据持久化 | SQLite数据库保存历史记录与回测结果 |
| 🐳 Docker部署 | 一键容器化，适合云端长期运行 |
| ⏰ 自动化 | GitHub Actions 调度 + 钉钉通知报警 |

---

## 🚀 快速开始

### 1. 本地快速回测

```bash
cd versions/002
python scripts/backtest_quick.py quick
```

### 2. Docker 生产部署

```bash
cd versions/002
docker-compose up -d
docker-compose logs -f backtest
```

### 3. GitHub Actions 自动化

本仓库已支持 GitHub Actions 自动执行回测并发送钉钉通知。详见 `.github/workflows/auto_backtest.yml`。

---

## 🧩 支持环境

- Python 3.11+
- Docker Engine
- GitHub 仓库 + GitHub Actions
- 钉钉自定义机器人 Webhook

---

## 📦 项目结构

```
Pythonprojectcode/
├── .github/                     # GitHub Actions workflow
├── config/                      # 全局配置文件
├── data/                        # 数据源与黑名单
├── databases/                   # 持久化数据库
├── docs/                        # 文档与部署说明
├── scripts/                     # 执行入口脚本
├── src/                         # 核心业务代码
├── tools/                       # 测试脚本与辅助工具
├── versions/                    # 版本分支目录
│   ├── 001/                     # 基础版本
│   └── 002/                     # 推荐版本（完整回测）
├── Dockerfile
├── docker-compose.yml
├── README.md
└── requirements.txt
```

---

## 📥 安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🔧 配置说明

### 1. 环境变量

复制 `.env.example` 为 `.env` 并填写你的配置：

```bash
copy .env.example .env
```

### 2. 关键配置项

- `DINGTALK_WEBHOOK`：钉钉机器人 Webhook URL
- `ENABLE_DINGTALK`：是否启用钉钉通知
- `INITIAL_BALANCE`：回测初始资金
- `HOURS_BACK`：回测回溯时间（小时）

> 推荐在 GitHub Actions 中通过 Secrets 管理 `DINGTALK_WEBHOOK`，避免在仓库中暴露敏感信息。

---

## 🧪 运行回测

### 1. 单次回测

```bash
cd versions/002
python scripts/run_backtest.py
```

按照交互提示选择回测配置，即可生成回测日志与图表。

### 2. 快速回测

```bash
cd versions/002
python scripts/backtest_quick.py quick
```

### 3. 发送钉钉通知

如果已启用钉钉通知，回测完成后会自动向你配置的钉钉机器人发送结果消息。

---

## 🚀 GitHub Actions 部署

仓库已配置 GitHub Actions 工作流：
- `.github/workflows/auto_backtest.yml`

该工作流支持：
- 定时触发（每天北京时间22:00）
- 手动触发
- 结果构件上传
- 回测失败时发送钉钉告警

### 1. 添加 Secret

在 GitHub 仓库设置中添加：
- `DINGTALK_WEBHOOK`

### 2. 启用 Workflow

进入 `Actions` 页面，启用 `💹 CS2 自动量化回测` 工作流。

### 3. 手动触发

进入 `Actions` → `Run workflow`。

---

## 🔔 钉钉通知说明

钉钉通知支持：
- 回测成功结果推送
- 回测失败告警
- GitHub Actions 触发信息（分支、执行者、工作流编号）

消息中会包含关键指标：
- 初始资金
- 最终资金
- 总收益
- 收益率
- 胜率
- 最大回撤
- 夏普比率
- 最近交易明细

> 注意：如果你的钉钉机器人启用了“关键词检测”，请确保消息中包含 `ding`，否则机器人可能不会发送。

---

## 🛠️ 详细部署步骤

### 本地调试

```bash
cd versions/002
python scripts/run_backtest.py
```

### Docker 部署

```bash
cd versions/002
docker-compose up -d
```

### GitHub Actions 部署

```bash
git add .
git commit -m "feat: add GitHub Actions and DingTalk notification"
git push origin main
```

---

## 📚 参考文档

- `docs/GITHUB_ACTIONS_GUIDE.md` - GitHub Actions 详细配置
- `docs/DINGTALK_QUICKSTART.md` - 钉钉快速配置
- `docs/GITHUB_ACTIONS_DEPLOYMENT.md` - 完整部署指南
- `docs/BACKTEST_GUIDE_CN.md` - 回测使用说明

---

## ❗ 常见问题

### 1. 钉钉消息没有收到

- 检查 `DINGTALK_WEBHOOK` 是否正确
- 确认机器人是否已添加到群
- 如果机器人启用了关键词检测，消息必须包含 `ding`
- 查看 `Actions` 日志或本地脚本输出

### 2. GitHub Actions 工作流未触发

- 检查 workflow 是否启用
- 确认仓库最近有活动提交
- 如果需要调整时间，修改 `.github/workflows/auto_backtest.yml` 中的 `cron`

### 3. 依赖安装失败

```bash
pip install -r requirements.txt
```

如果仍失败，先升级 pip：

```bash
python -m pip install --upgrade pip
```

---

## 📌 备注

- 建议使用 `versions/002` 作为主线版本。
- 生产环境推荐通过 Docker 或 GitHub Actions 运行。
- 关键配置请使用环境变量和 GitHub Secrets 进行保护。

---

## ✨ 贡献

欢迎提交 PR、问题和建议。

---

## 📄 版权与许可证

请根据仓库实际情况补充项目许可证信息。
