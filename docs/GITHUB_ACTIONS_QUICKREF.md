# 📱 GitHub Actions 部署 - 快速参考卡

> 一页纸快速参考，完整部署流程从这开始

---

## 🎯 3分钟快速部署

### 第一步：获取钉钉Webhook (1分钟)

```
手机打开钉钉 → 任意群 → 群设置(⋮) → 群机器人 → 添加机器人

① 选择"自定义"
② 名称：CS2回测系统  
③ ✓ 勾选"加签"
④ 保存并复制 Webhook URL
```

**示例**: `https://oapi.dingtalk.com/robot/send?access_token=xxxxx`

### 第二步：GitHub Secret 配置 (1分钟)

```
GitHub仓库 → Settings → Secrets and variables → Actions
→ New repository secret

Name: DINGTALK_WEBHOOK
Secret: 粘贴上面复制的URL

✓ Add secret
```

### 第三步：启用工作流 (1分钟)

```
仓库 → Actions → 左侧找"💹 CS2"
→ Enable workflow
```

**完成！每天22点自动执行回测**

---

## ✅ 验证配置

```bash
# 立即手动测试（GitHub网页）
Actions → Run workflow → Run

等待 5-15 分钟...

✓ 钉钉群收到消息 = 部署成功！
✗ 没收到消息 = 查看下方故障排查
```

---

## 🔍 故障排查 (5分钟内解决)

### 问题: 钉钉无消息

| 症状 | 解决 | 验证 |
|------|------|------|
| Secret未设置 | Settings → Secrets → 重新添加 DINGTALK_WEBHOOK | Actions日志搜索"Secret" |
| URL格式错误 | 复制完整URL（以`access_token=`开头） | 本地 `python tools/temp/test_dingtalk.py` |
| 机器人未启用 | 钉钉群 → 机器人 → 确认启用 | 钉钉群是否能@机器人 |
| 工作流未启用 | Actions → Enable workflow | Actions中看到"enabled" |

### 问题: 工作流执行失败

```
Actions → 工作流运行 → backtest → 查看日志

搜索关键词：
❌ ERROR: 找到错误位置
⚠️  WARNING: 可能的问题
✅ INFO: 成功的步骤

常见错误修复：
- ModuleNotFoundError → pip install -r requirements.txt
- DINGTALK_WEBHOOK not found → 检查 Secret 是否正确
- HTTP 500 → 钉钉服务异常，稍后重试
```

---

## 📅 修改执行时间

编辑 `.github/workflows/auto_backtest.yml`:

```yaml
schedule:
  - cron: '0 14 * * *'  # ← 改这一行
```

### 常用时间表

```
'0 14 * * *'   = 每天 14:00 UTC (北京 22:00) ⭐ 推荐
'0 0 * * *'    = 每天 00:00 UTC (北京 08:00)
'0 */6 * * *'  = 每6小时
'0 10 * * 1,3,5' = 周一三五 10:00 UTC (北京18:00)
'0 0 1 * *'    = 每月1号
```

更多: https://crontab.guru

---

## 📊 钉钉消息格式

### ✅ 成功消息包含

```
🤑 虚拟回测结果

核心指标：
  收益率 | 胜率 | 夏普比率 | 最大回撤

风险指标：
  最好交易 | 最差交易 | 平均收益

交易明细：
  皮肤名称 | 买入价 | 卖出价 | 利润

完成时间 | 触发者 | 分支 | 工作流ID
```

### ❌ 失败消息包含

```
⚠️ 回测流程失败告警

运行信息：
  分支 | 提交 | 执行者 | 工作流ID

失败原因：[错误信息]

查看日志：[GitHub Actions链接]
```

---

## 🔐 安全提示

```bash
# ✅ DO: 使用 GitHub Secrets
${{ secrets.DINGTALK_WEBHOOK }}

# ❌ DON'T: 硬编码在代码里
WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxxxx
```

---

## 📱 本地测试

```bash
# 1. 设置环境变量
$env:DINGTALK_WEBHOOK="你的webhook"

# 2. 运行测试脚本
python tools/temp/test_dingtalk.py

# 预期输出
✅ 发送成功
```

---

## 💡 高级用法

### 手动选择参数运行

```
Actions → 工作流 → Run workflow

参数选项：
  hours_back: 24/72/168 小时
  initial_balance: 初始资金
  
✓ Run workflow
```

### 修改执行参数

编辑 `.github/workflows/auto_backtest.yml`:

```yaml
- name: 🚀 执行回测
  run: |
    python scripts/run_backtest.py \
      --hours-back 168 \           # 7天数据
      --initial-balance 50000 \    # 5万资金
      --enable-dingtalk            # 发送钉钉通知
```

### 查看完整报告

```
Actions → 工作流运行 → Artifacts

下载：backtest-report.zip

包含：
  📄 JSON 详细指标
  📊 收益曲线图
  📈 性能分析
```

---

## 📞 常见问题

| 问题 | 答案 |
|------|------|
| 免费账号能用吗？ | ✅ 可以，每月2000分钟免费额度 |
| 私有仓库能用吗？ | ✅ 可以 |
| 能改执行时间吗？ | ✅ 改 cron 表达式即可 |
| 会产生费用吗？ | ✓ 免费用户不会 |
| 通知能改成邮件吗？ | ✅ 可以，扩展代码支持 |

---

## 🚀 部署完成清单

- [ ] 创建钉钉机器人
- [ ] 复制 Webhook URL
- [ ] GitHub Settings → 添加 Secret `DINGTALK_WEBHOOK`
- [ ] 启用工作流
- [ ] 手动运行一次验证
- [ ] 钉钉群收到测试消息
- [ ] 配置执行时间 (可选)
- [ ] 检查首次自动执行结果

---

## 📚 详细文档

- 快速开始: [`DINGTALK_QUICKSTART.md`](DINGTALK_QUICKSTART.md)
- 详细配置: [`GITHUB_ACTIONS_GUIDE.md`](GITHUB_ACTIONS_GUIDE.md)  
- 完整部署: [`GITHUB_ACTIONS_DEPLOYMENT.md`](GITHUB_ACTIONS_DEPLOYMENT.md)

---

**最后更新**: 2026-04-14  
**预计部署时间**: 3-5 分钟  
**首次执行**: 手动运行后 5-15 分钟  
**定时执行**: 每天 22:00 (UTC 14:00)
