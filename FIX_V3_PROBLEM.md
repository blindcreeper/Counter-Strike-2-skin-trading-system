# 完全解决GitHub Actions v3弃用问题

## 问题根源
GitHub仓库中可能仍有旧的、包含`actions/upload-artifact@v3`的工作流文件。

## 解决方案：手动完全清除

### 步骤1：删除GitHub上的所有工作流文件
1. 访问你的GitHub仓库：
   ```
   https://github.com/blindcreeper/Counter-Strike-2-skin-trading-system
   ```

2. 导航到工作流目录：
   - 点击 `.github` 文件夹
   - 点击 `workflows` 文件夹

3. 删除所有文件：
   - 点击每个文件右侧的垃圾桶图标
   - 确认删除

### 步骤2：上传全新的工作流文件
1. **下载我的ZIP文件**：`D:\Pythonprojectcode\cs2-quant-system.zip`
2. **解压到桌面**
3. **只上传工作流文件**：
   - 导航到 `.github/workflows/simple.yml`
   - 点击 "Add file" → "Upload files"
   - 拖拽 `simple.yml` 文件
   - 提交信息：`fix: replace all v3 workflows with clean v4 version`

### 步骤3：验证工作流
1. 进入仓库的 **Actions** 页面
2. 点击 **simple.yml** 工作流
3. 点击 **"Enable workflow"**
4. 点击 **"Run workflow"** 测试

## 备用方案：使用GitHub Web界面创建
如果上传失败，直接在GitHub上创建：

1. 在 `.github/workflows/` 目录中点击 **"Create new file"**
2. 文件名输入：`cs2-backtest.yml`
3. 粘贴以下内容：
```yaml
name: CS2 Quantitative Backtest

on:
  schedule:
    - cron: "0 14 * * *"
  workflow_dispatch:
    inputs:
      hours_back:
        description: "Hours back"
        default: "72"
      initial_balance:
        description: "Initial balance"
        default: "10000"

jobs:
  backtest:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Run CS2 backtest
        run: |
          python scripts/run_backtest.py
          
      - name: Save results
        if: success()
        uses: actions/upload-artifact@v4
        with:
          name: cs2-backtest-output
          path: |
            backtest_logs/
            backtest_charts/
```

## 验证步骤

### 确认v3已完全清除
1. 检查GitHub仓库中的所有`.yml`文件
2. 搜索 `v3` 或 `upload-artifact@v3`
3. 确保只有 `upload-artifact@v4`

### 测试工作流
1. 手动触发工作流
2. 检查运行日志
3. 确认没有v3错误

## 故障排除

### 如果错误仍然出现
1. **清除GitHub Actions缓存**：
   - 仓库设置 → Actions → General
   - 滚动到 "Actions cache"
   - 点击 "Delete all caches"

2. **禁用再启用工作流**：
   - Actions页面 → 点击工作流
   - 点击 "Disable workflow"
   - 等待几分钟，然后 "Enable workflow"

### 如果无法删除文件
1. 使用GitHub Desktop工具
2. 克隆仓库到本地
3. 手动删除`.github/workflows/`目录
4. 推送更改

## 关键验证点
✅ 确保 `.github/workflows/` 目录中只有使用 `@v4` 的文件
✅ 确认工作流可以手动运行
✅ 检查日志中无v3错误

## 联系支持
如果所有方法都失败，联系GitHub支持：
1. 描述 `actions/upload-artifact@v3` 弃用问题
2. 请求清除仓库中所有v3引用
3. 提供仓库URL

