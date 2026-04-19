# GitHub Actions 部署指南

## 📋 快速开始（3步）

### 第一步：获取钉钉Webhook

1. 自行创建钉钉群组（如没有）
2. 在钉钉群中添加机器人：
   - 群设置 → 群机器人 → 添加机器人
   - 选择"自定义"机器人
   - 设名称为"CS2回测系统"
   - **勾选** "加签"（推荐安全）
   - 复制 Webhook URL

### 第二步：配置GitHub Secrets

在你的仓库中设置Secret（用来存储敏感信息）：

1. 进入仓库 → Settings → Secrets and variables → **Actions**
2. 点击 **New repository secret**
3. 创建以下Secret：

| Secret名称 | 值 | 说明 |
|-----------|-----|------|
| `DINGTALK_WEBHOOK` | `https://oapi.dingtalk.com/robot/send?access_token=xxxxx` | 钉钉机器人Webhook URL |

> ⚠️ **安全提示**：不要把webhook URL提交到代码仓库，使用GitHub Secrets存储！

### 第三步：启用工作流

1. 进仓库 → **Actions** 标签
2. 左侧选择 "💹 CS2 自动量化回测"
3. 点击 **Enable workflow** 

---

## ⏰ 工作流触发方式

### 方式1：定时自动执行（推荐）
```yaml
schedule:
  - cron: '0 14 * * *'  # 每天UTC 14:00（北京时间22:00）
```

修改时间（Linux cron格式）:
- `0 14 * * *` → 每天 14:00 UTC (北京22:00)
- `0 */6 * * *` → 每6小时执行一次
- `0 2 * * 1` → 每周一 2:00 UTC

### 方式2：手动触发
1. Actions → 💹 CS2 自动量化回测
2. Run workflow 按钮
3. 选择参数后点击 **Run workflow**

---

## 📊 配置参数说明

### 工作流参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `hours_back` | `72` | 回溯历史数据时间（小时）：24/72/168 |
| `initial_balance` | `10000` | 虚拟账户初始资金（元） |

**手动触发时可选择参数**：
```
hours_back: 24/72/168 小时
initial_balance: 自定义金额
```

---

## ✅ 钉钉通知内容

### 成功时的消息格式

```
🤑 虚拟回测结果

📊 核心指标：
- 初始资金: ¥10000.00
- 最终资金: ¥10123.45
- 总收益: ¥123.45 | 收益率: 1.23%
- 交易笔数: 12 | 胜率: 70%
- 最大回撤: -2.5% | 夏普比率: 1.89

📈 风险指标：
- 平均收益: ¥10.29
- 最好交易: ¥25.50
- 最差交易: -¥8.00
- 赢家笔数: 8 | 输家笔数: 4

📦 交易明细（最多10笔）：
- 1. 皮肤名称 | 买:100.00 卖:105.00 | ...
- 2. ...

完成时间: 2026-04-14 22:05:30
触发者: github_username | 分支: main | 工作流 #123
```

### 失败时的通知

包含：
- 错误原因
- GitHub Actions运行日志链接
- 快速诊断信息

---

## 🔍 查看运行日志

1. 进入仓库 → **Actions**
2. 点击最新的工作流运行
3. 点击 **backtest** 任务查看详细日志
4. 下载 **backtest-report** 制品（包含详细报告）

---

## 🛠️ 常见问题排查

### Q：钉钉没收到通知？

**检查清单**：
- [ ] 确认 `DINGTALK_WEBHOOK` Secret已正确设置
- [ ] 检查钉钉机器人是否启用
- [ ] 查看工作流日志的钉钉通知部分
- [ ] 尝试手动运行工作流 (Actions → Run workflow)

**日志中查找**：
```
✅ 钉钉通知已发送
或
❌ 钉钉通知失败: [错误信息]
```

### Q：工作流未按时执行？

**可能原因**：
- GitHub Actions需要仓库有活动（至少30天内有push）
- 检查仓库 Settings → Actions → General → 是否禁用workflow

**解决方案**：
```bash
# 推送一个无意义的commit来激活
git commit --allow-empty -m "trigger workflow"
git push
```

### Q：如何修改执行时间？

编辑文件 `.github/workflows/auto_backtest.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * *'  # 修改这一行
```

常用时间表：
```
'0 14 * * *'   # 每天 14:00 UTC (8小时+北京)
'0 0 * * *'    # 每天 00:00 UTC (8小时+北京)  
'0 */6 * * *'  # 每6小时
'0 10 * * 1,3,5' # 周一三五 10:00
```

---

## 🔐 安全最佳实践

1. **使用GitHub Secrets**
   - ✅ DO: `${{ secrets.DINGTALK_WEBHOOK }}`
   - ❌ DON'T: 直接在YAML中写明文

2. **限制工作流权限**
   - Settings → Actions → General
   - 设置合适的权限范围

3. **定期审查日志**
   - 检查是否有异常失败
   - 确保钉钉通知正常

---

## 📈 下一步优化

### 可选配置

1. **邮件通知**（Email SMTP）
   - 在 `config/backtest_config.py` 中配置SMTP
   - 创建 `EMAIL_CONFIG` Secret

2. **Slack通知**
   - 添加 Slack Webhook
   - 修改 `backtest_notifier.py` 支持Slack

3. **定制回测参数**
   - 修改 `scripts/run_backtest.py` 中的参数
   - 提交PR时可指定不同的回溯期

### 扩展建议

```yaml
# 可以添加的触发方式
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'config/**'
  pull_request:
    types: [opened, synchronize]
```

---

## 📞 获取构件（回测报告）

回测完成后，GitHub Actions会自动保存报告：

1. 进入工作流运行页面
2. 向下滚动找到 **Artifacts**
3. 下载 **backtest-report** (包含日志和图表)

报告包含：
- 📄 JSON格式的详细指标
- 📊 收益曲线图表
- 📈 性能分析图表（如启用）

---

## 验证部署成功

运行一次手动工作流验证：

```
1. GitHub Actions 标签
2. 💹 CS2 自动量化回测
3. Run workflow
4. 等待5-15分钟
5. 查看钉钉是否收到消息 ✅
```

---

**文档最后更新**：2026-04-14
