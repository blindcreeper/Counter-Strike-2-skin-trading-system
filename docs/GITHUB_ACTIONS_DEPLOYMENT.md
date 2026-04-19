# 🚀 GitHub Actions 部署完整指南

## 📖 文档导航

| 文档 | 描述 | 适合人群 |
|------|------|--------|
| [DINGTALK_QUICKSTART.md](DINGTALK_QUICKSTART.md) | 5分钟快速配置钉钉 | 急于上手的用户 |
| [GITHUB_ACTIONS_GUIDE.md](GITHUB_ACTIONS_GUIDE.md) | 详细的GitHub Actions配置 | 需要深入理解的用户 |
| 本文档 | 部署架构和完整流程 | 项目管理者 |

---

## 🏗️ 部署架构

```
┌─────────────────────────────────────────────────────┐
│          GitHub Repositories                         │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌────────────────────────────────────────────┐    │
│  │  .github/workflows/auto_backtest.yml        │    │
│  │  (GitHub Actions Workflow)                  │    │
│  └────────────────────────────────────────────┘    │
│         │                                            │
│         ├─ Daily Schedule (UTC 14:00)                │
│         └─ Manual Trigger                           │
│                                                      │
│         ↓                                            │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │  GitHub Actions Runner (ubuntu-latest)      │    │
│  │  - Setup Python 3.11                        │    │
│  │  - Install Dependencies                     │    │
│  │  - Run Backtest                             │    │
│  │  - Send DingTalk Notification               │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────┐
│          DingTalk (钉钉)                             │
├─────────────────────────────────────────────────────┤
│                                                       │
│  Webhook Endpoint: oapi.dingtalk.com                │
│  Message Format: Markdown                           │
│                                                      │
│  Notification Content:                              │
│  - ✅ Success: 详细的回测结果                       │
│  - ❌ Failure: 错误信息和日志链接                   │
│                                                      │
└─────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────┐
│          Your DingTalk Group (钉钉群)               │
├─────────────────────────────────────────────────────┤
│  - 实时接收回测通知                                 │
│  - 快速查看关键指标                                 │
│  - 点击链接查看完整日志                             │
└─────────────────────────────────────────────────────┘
```

---

## ⚡ 部署步骤

### Phase 1: 环境准备 (10分钟)

#### 1.1 本地测试

```bash
# 1. 复制配置文件
cp .env.example .env

# 2. 获取钉钉Webhook并填入 .env
# DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxxxx

# 3. 测试钉钉连接
python tools/temp/test_dingtalk.py
# 预期输出: ✅ 发送成功
```

#### 1.2 推送到GitHub

```bash
git add -A
git commit -m "chore: prepare GitHub Actions deployment"
git push origin main
```

### Phase 2: GitHub 配置 (5分钟)

#### 2.1 添加Secret

1. 打开 GitHub 仓库
2. Settings → Secrets and variables → Actions
3. New repository secret
4. 名称: `DINGTALK_WEBHOOK`
5. 值: 粘贴你的Webhook URL
6. Add secret

#### 2.2 启用Workflow

1. 仓库 → Actions
2. 左侧找 "💹 CS2 自动量化回测"
3. Enable workflow

### Phase 3: 验证部署 (5分钟)

#### 3.1 手动触发

```
Actions → Run workflow → Run workflow
等待5-15分钟...
```

#### 3.2 检查结果

```
✅ 钉钉收到消息 → 部署成功！
❌ 没有消息 → 查看故障排查章节
```

---

## 📋 配置清单

### 本地开发环境

- [ ] Python 3.11+
- [ ] 安装依赖: `pip install -r requirements.txt`
- [ ] 设置 `.env` 文件
- [ ] 测试钉钉: `python tools/temp/test_dingtalk.py`

### GitHub 配置

- [ ] 仓库已推送到GitHub
- [ ] `.github/workflows/auto_backtest.yml` 文件存在
- [ ] Secret `DINGTALK_WEBHOOK` 已添加
- [ ] Workflow 已启用

### 钉钉配置

- [ ] 创建钉钉机器人 ✅ "加签"
- [ ] Webhook URL 正确格式
- [ ] 机器人已添加到群
- [ ] 接收权限正常

---

## 🎯 工作流工作原理

### 触发方式

```yaml
# 方式1: 定时执行（推荐用于生产环境）
schedule:
  - cron: '0 14 * * *'  # 每天 UTC 14:00 (北京 22:00)

# 方式2: 手动触发（用于测试）
workflow_dispatch:
  inputs:
    hours_back:
      description: '回溯时间'
      default: '72'
    initial_balance:
      description: '初始资金'
      default: '10000'
```

### 执行步骤

| 步骤 | 操作 | 耗时 |
|------|------|------|
| 1 | 检出代码 | ~5s |
| 2 | 配置Python 3.11 | ~10s |
| 3 | 安装依赖 | ~20s |
| 4 | 执行回测 | 5-10min |
| 5 | 上传报告 | ~10s |
| 6 | 发送钉钉通知 | ~5s |
| **总计** | | **5-11 min** |

### 钉钉通知逻辑

```
回测完成
  ├─ 成功 → 发送详细结果消息
  │   ├─ 核心指标 (收益率、胜率等)
  │   ├─ 风险指标 (最大回撤、夏普比率)
  │   └─ 交易明细 (最近10笔)
  │
  └─ 失败 → 发送错误告警消息
      ├─ 运行信息 (分支、提交、执行者)
      ├─ 失败原因
      └─ 日志查看链接
```

---

## 🔧 自定义配置

### 修改执行时间

编辑 `.github/workflows/auto_backtest.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * *'  # 改这里
```

### 修改回测参数

在workflow中传递参数：

```yaml
- name: 🚀 执行回测
  env:
    DINGTALK_WEBHOOK: ${{ secrets.DINGTALK_WEBHOOK }}
  run: |
    python scripts/run_backtest.py \
      --hours-back 168 \        # 回溯7天
      --initial-balance 50000 \ # 初始资金5万
      --enable-charts \
      --enable-dingtalk
```

### 添加额外通知

支持扩展钉钉通知功能：

```python
# 在 src/backtest_notifier.py 中
def send_dingtalk_advanced(self, webhook_url, metrics, trades):
    # 添加自定义逻辑
    # 例如：根据收益率自动调整策略参数
    pass
```

---

## 📊 监控和维护

### 日常检查

```
每周检查一次：
1. GitHub Actions → 工作流运行历史
2. 查看成功/失败的执行情况
3. 核实钉钉消息是否持续接收
```

### 日志分析

```bash
# 查看工作流日志
GitHub Actions → 工作流运行 → backtest → 查看步骤日志

# 关键词搜索
- ✅: 成功操作
- ❌: 失败操作
- ⚠️: 警告信息
```

### 性能优化

```yaml
# 缓存依赖加快执行速度
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # 缓存pip依赖
```

---

## 🚨 故障排查

### 问题1: 钉钉无法收到消息

**症状**: 工作流成功执行，但钉钉群没有消息

**排查步骤**:
```bash
1. 检查 Secret: GitHub Settings → Secrets → DINGTALK_WEBHOOK
2. 验证 Webhook 格式是否正确
3. 测试本地连接: python tools/temp/test_dingtalk.py
4. 查看工作流日志中的通知部分
```

**解决方案**:
- [ ] 重新复制钉钉Webhook URL
- [ ] 更新GitHub Secret
- [ ] 重新运行工作流

### 问题2: 工作流执行超时

**症状**: 工作流运行超过30分钟未完成

**排查步骤**:
```
1. 检查回测数据量（HOURS_BACK）
2. 查看系统资源使用情况
3. 检查是否有死循环
```

**解决方案**:
- [ ] 减少 `hours_back` 参数 (改为24h)
- [ ] 优化回测引擎性能
- [ ] 检查数据库锁定情况

### 问题3: Python依赖冲突

**症状**: 错误: `ModuleNotFoundError` 或 `VersionConflict`

**排查步骤**:
```
1. 检查 requirements.txt 中的版本
2. 查看GitHub Actions日志中的pip install步骤
```

**解决方案**:
```bash
# 更新 requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "update: pin dependency versions"
git push
```

---

## 📈 性能基准

### 典型执行时间

| 操作 | 耗时 | 说明 |
|------|------|------|
| Python Setup | ~10s | 包括缓存检查 |
| 依赖安装 | ~20s | 使用pip缓存 |
| 回测执行 | 5-10min | 取决于数据量 |
| 通知发送 | ~2s | 包括重试 |
| **总计** | 5-11 min | 平均8分钟 |

### 资源消耗

| 资源 | 使用量 | 限制 |
|------|--------|------|
| CPU | ~2 cores | GitHub提供4 cores |
| 内存 | ~500MB | GitHub提供7GB |
| 存储 | ~100MB | GitHub提供空间足够 |
| API 调用 | ~50/回测 | 一般不超限制 |

---

## 🔒 安全考虑

### Secret 管理

```yaml
# ✅ 安全做法
env:
  DINGTALK_WEBHOOK: ${{ secrets.DINGTALK_WEBHOOK }}

# ❌ 不安全做法
env:
  DINGTALK_WEBHOOK: https://oapi.dingtalk.com/robot/send?access_token=xxxx
```

### 权限控制

```
Settings → Actions → General
- Workflow permissions 设置为 "Read and write"（默认）
- Fork pull request workflows from outside collaborators: 可选
```

### 日志安全

- GitHub Actions 日志中会屏蔽 Secret 内容
- 构件（报告）仅保留30天
- 可手动删除日志

---

## 📚 相关文档

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [钉钉机器人开发文档](https://open.dingtalk.com/document/robots/custom-bot-send-message)
- [Cron 表达式速查表](https://crontab.guru)
- [Python 部署最佳实践](https://docs.python.org/3/distributing/index.html)

---

## 💡 最佳实践

### 1. 定期备份报告

```bash
# 定期下载GitHub Actions构件
# Actions → 工作流运行 → 下载 backtest-report
```

### 2. 监控告警

```
钉钉群设置 → 机器人 → 启用消息通知
确保重要消息及时提醒
```

### 3. 版本控制

```bash
# 跟踪配置和脚本的变更
git log --oneline .github/workflows/
git log --oneline scripts/run_backtest.py
```

### 4. 定期审查

```
每月回顾一次：
1. 工作流执行成功率
2. 回测策略有效性
3. 钉钉通知及时性
4. 系统性能指标
```

---

## ❓ 常见问题

**Q: 我的仓库是私有的可以吗？**  
A: 可以，GitHub Actions 对私有仓库也支持（包括免费账号）。

**Q: 钉钉通知频率太高可以改吗？**  
A: 可以，修改 `cron` 时间表从每天改为每周或每月。

**Q: 能同时发送多个通知吗？**  
A: 可以，修改 workflow 中的 `run_backtest.py` 调用，支持钉钉、邮件、Slack等。

**Q: 工作流执行会产生费用吗？**  
A: 免费账号每月有 2000 分钟免费额度（足够每天运行一次）。

---

**文档版本**: v2.0 (2026-04-14)  
**维护者**: CS2量化交易系统项目组
