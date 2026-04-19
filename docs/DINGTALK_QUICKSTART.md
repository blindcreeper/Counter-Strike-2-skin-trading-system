# GitHub Actions + 钉钉通知快速配置

## 🚀 5分钟快速配置

### Step 1: 创建钉钉机器人 (2分钟)

```
1. 打开钉钉，创建或选择一个群
2. 群设置（右上⋮） → 群机器人 → 添加机器人
3. 选择"自定义"机器人
4. 填写信息：
   - 机器人名称: CS2回测系统
   - 描述: 自动化量化回测通知
   - 勾选 ✓ 加签（获得验证码）
5. 保存后复制 Webhook URL（看起来像）：
   https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxxxxx
```

### Step 2: GitHub Secrets 配置 (2分钟)

```
1. 打开你的GitHub仓库
2. 进入 Settings → Secrets and variables → Actions
3. 点击 New repository secret
4. 输入：
   - Name: DINGTALK_WEBHOOK
   - Secret: [粘贴上面复制的Webhook URL]
5. 点击 Add secret
```

### Step 3: 启用工作流 (1分钟)

```
1. 仓库首页 → Actions
2. 左侧找 "💹 CS2 自动量化回测"
3. 点击 Enable workflow
4. 完成！每天22点自动执行
```

---

## ✅ 验证配置

### 手动测试（推荐）

```bash
# 1. 本地测试钉钉通知
python tools/temp/test_dingtalk.py

# 如果成功：
# ✅ 发送成功

# 如果失败，检查：
# - Webhook URL是否正确复制
# - 环境变量是否设置
```

### GitHub Actions 测试

```
1. 仓库 → Actions
2. 选中 "💹 CS2 自动量化回测"
3. 右上 Run workflow
4. 选择参数（默认72小时）
5. 点击 Run workflow
6. 等待5-15分钟
7. 检查钉钉是否收到消息
```

---

## 🔍 故障排查

### 1. 钉钉没收到消息

**检查清单**：

```bash
# 1️⃣ 验证 Webhook URL 是否正确
echo $DINGTALK_WEBHOOK  # 应该显示完整URL

# 2️⃣ 测试钉钉连接
python tools/temp/test_dingtalk.py

# 3️⃣ 检查GitHub Secrets是否设置
# GitHub网页 → Settings → Secrets → DINGTALK_WEBHOOK
```

**常见原因**：
- ❌ Secret名称大小写错误（应该是 DINGTALK_WEBHOOK）
- ❌ Webhook URL复制不完整
- ❌ 钉钉机器人未启用
- ❌ 钉钉群是否被禁用

### 2. 工作流执行失败

**查看日志**：

```
1. GitHub Actions → 工作流运行
2. 找到失败的运行
3. 点击 "backtest" 任务
4. 查看 "执行回测" 步骤的日志
5. 搜索 "Error" 或 "错误"
```

**常见错误**：

| 错误信息 | 原因 | 解决方案 |
|---------|------|--------|
| `ModuleNotFoundError` | 依赖未安装 | 检查 requirements.txt |
| `DINGTALK_WEBHOOK: not found` | Secret未配置 | 重新添加 Secret |
| `HTTP 500` | 钉钉服务异常 | 稍后重试 |
| `errcode=40001` | Token过期 | 重新复制Webhook URL |

### 3. 定时任务未执行

**原因排查**：

```
1. 确认工作流已启用 (Actions → Enable workflow)
2. 检查仓库是否有活动（近30天内有push）
3. 修改时间触发：
   - 编辑 .github/workflows/auto_backtest.yml
   - 修改 cron 时间表
   - 提交并push
```

---

## 📊 钉钉消息内容

### 成功通知示例

```
🤑 虚拟回测结果

📊 核心指标：
- 初始资金: ¥10000.00
- 最终资金: ¥10250.50
- 总收益: ¥250.50 | 收益率: 2.51%
- 交易笔数: 15 | 胜率: 73.33%
- 最大回撤: -3.2% | 夏普比率: 2.15

📈 风险指标：
- 平均收益: ¥16.70
- 最好交易: ¥45.00
- 最差交易: -¥12.50
- 赢家笔数: 11 | 输家笔数: 4

📦 交易明细（最多10笔）：
- 1. Dragon Lore FaZe | 买:850.00 卖:892.00 | 利润:42.00 (4.94%)
- 2. ... (其余14笔)

完成时间: 2026-04-14 22:05:30
触发者: your_username | 分支: main | 工作流 #42
```

### 失败通知示例

```
⚠️ 回测流程失败告警

运行信息：
- 分支: `develop`
- 提交: abcd123
- 执行者: `github_user`
- 工作流ID: #41

失败原因：
ModuleNotFoundError: No module named 'numpy'

排查链接：
[查看完整日志](GitHub Actions URL)
```

---

## ⏰ 自定义执行时间

编辑 `.github/workflows/auto_backtest.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * *'  # ← 修改这里
```

### Cron 时间表示例

| 需求 | Cron表达式 | 说明 |
|------|-----------|------|
| 每天22:00 (北京时) | `0 14 * * *` | UTC 14:00 = 北京 22:00 |
| 每天午夜 | `0 0 * * *` | UTC 00:00 = 北京 08:00 |
| 每6小时 | `0 */6 * * *` | 0, 6, 12, 18点 |
| 周一到周五 9点 | `0 1 * * 1-5` | UTC 1:00 (北京9点) |
| 每月1日 | `0 0 1 * *` | 月初零点 |

更多示例: https://crontab.guru

---

## 🔐 安全建议

### Do's ✅

```yaml
# ✅ 正确：使用 GitHub Secrets
env:
  DINGTALK_WEBHOOK: ${{ secrets.DINGTALK_WEBHOOK }}
```

```bash
# ✅ 正确：本地使用 .env 文件
source .env
```

### Don'ts ❌

```yaml
# ❌ 危险：硬编码在YAML文件
DINGTALK_WEBHOOK: "https://oapi.dingtalk.com/robot/send?access_token=xxxx"
```

```bash
# ❌ 危险：直接echo敏感信息
echo "DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxxx"
```

---

## 📝 常见配置错误

### 错误1：Webhook URL格式

```bash
# ❌ 错误
DINGTALK_WEBHOOK=your_token_here

# ✅ 正确
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=你的token
```

### 错误2：Secret名称大小写

```bash
# ❌ 错误（大小写不一致）
${{ secrets.DINGTALK_webhook }}
${{ secrets.dingtalk_webhook }}

# ✅ 正确
${{ secrets.DINGTALK_WEBHOOK }}
```

### 错误3：环境变量未传递

```yaml
# ❌ 错误：没有传递env
- name: 运行回测
  run: python scripts/run_backtest.py --enable-dingtalk

# ✅ 正确：显式传递webhook
- name: 运行回测
  env:
    DINGTALK_WEBHOOK: ${{ secrets.DINGTALK_WEBHOOK }}
  run: python scripts/run_backtest.py --enable-dingtalk --dingtalk-webhook "${{ secrets.DINGTALK_WEBHOOK }}"
```

---

## 📞 获取帮助

### 查看完整日志

```
1. GitHub.com → 你的仓库 → Actions
2. 点击工作流运行
3. 点击 "backtest" 任务
4. 向下滚动查看完整日志
```

### 测试钉钉连接

```bash
cd d:\Pythonprojectcode

# 设置环境变量
$env:DINGTALK_WEBHOOK="你的webhook"

# 运行测试脚本
python tools/temp/test_dingtalk.py
```

---

**最后更新**: 2026-04-14
**维护者**: GitHub Actions + CS2回测系统
