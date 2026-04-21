# 🚀 快速开始指南

## ⚡ 最快 5 分钟开始

### 步骤 1：进入最新版本
```bash
cd versions/002
```

### 步骤 2：运行快速回测
```bash
python scripts/backtest_quick.py quick
```

### 步骤 3：查看结果
```bash
# 自动打开结果目录（或手动打开）
open output/backtest_results/
```

✅ 完成！你会看到：
- 📈 账户资金曲线图
- 📊 胜负交易分布
- 📉 最大回撤分析
- 💾 完整的性能指标

---

## 🎯 下一步

### 如果你想...

| 目标 | 操作 |
|------|------|
| **了解详细用法** | `cat versions/002/docs/BACKTEST_GUIDE_CN.md` |
| **自定义参数** | `python scripts/run_backtest.py` 选择选项 3 |
| **在服务器上运行** | 参考 `versions/002/README_DOCKER.md` |
| **采集新数据** | `python src/main.py`（等待 5-60 分钟） |
| **查看历史结果** | `ls versions/002/output/backtest_results/` |

---

## 📂 重要文件位置

```
根目录/
├── README.md                          ← 项目说明（看这个）
├── DIRECTORY_GUIDE.md                 ← 目录结构说明
├── versions/002/                      ← ⭐ 推荐版本
│   ├── docs/BACKTEST_GUIDE_CN.md     ← 📚 完整指南
│   ├── README_DOCKER.md              ← Docker 部署
│   └── scripts/backtest_quick.py     ← 快速回测
└── data/opportunities.csv             ← 交易数据
```

---

## ❓ 常见错误

### 错误 1：找不到模块
```
ModuleNotFoundError: No module named 'pandas'
```
**解决**：确保在正确的目录
```bash
cd versions/002
```

### 错误 2：数据为空导致 0 笔交易
```
✅ 回测完成，但 total_trades = 0
```
**解决**：先采集数据
```bash
python src/main.py
# 让它运行几分钟，会生成 opportunities.csv
# 然后再运行回测
```

### 错误 3：权限错误（Windows）
```
Permission denied: 'output/backtest_logs'
```
**解决**：
1. 确保没有其他程序占用文件
2. 右键"以管理员身份运行" PowerShell

---

## 🐳 用 Docker（推荐生产环境）

```bash
# 进入版本目录
cd versions/002

# 启动容器
docker-compose up -d

# 查看运行日志
docker-compose logs -f

# 完成后停止
docker-compose stop
```

结果会自动保存到 `output/` 目录。

---

## 📊 理解回测结果

回测完成后，你会看到一个报告，像这样：

```
📈 回测摘要 (初始资金: ¥10000)
───────────────────────────────────
交易统计    | 总笔数: 1542 | 获利: 856 | 亏损: 686
盈亏情况    | 总利润: ¥2,345.67 | ROI: 23.45%
风险指标    | 最大回撤: -8.34% | 夏普比率: 1.23
账户情况    | 初始: ¥10000 | 最终: ¥12,345.67
───────────────────────────────────
```

### 指标说明

- **总笔数**：做了多少笔虚拟交易
- **获利笔数**：其中多少笔赚钱了（所以 856/1542 = 胜率 55.5%）
- **总利润**：赚了多少钱（¥2,345.67）
- **ROI**：投资回报率（初始 ¥10000 增长 23.45%）
- **最大回撤**：账户最大下跌幅度（风险指标，-8.34% 说明可控）
- **夏普比率**：风险调整后的收益（> 1.0 为好）

---

## 🔗 更多资源

- **主 README**：[README.md](README.md)
- **目录说明**：[DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md)
- **完整指南**：[versions/002/docs/BACKTEST_GUIDE_CN.md](versions/002/docs/BACKTEST_GUIDE_CN.md)
- **Docker 指南**：[versions/002/README_DOCKER.md](versions/002/README_DOCKER.md)
- **代码示例**：[versions/002/docs/QUICKSTART.py](versions/002/docs/QUICKSTART.py)

---

## 💡 小贴士

1. **第一次使用**：直接运行 `quick` 模式，5 分钟内看到结果
2. **没有数据**：运行 `python src/main.py` 采集数据（需要有效的 API 密钥）
3. **想要自动化**：使用 Docker 或设置定时任务（见 [完整指南](versions/002/docs/BACKTEST_GUIDE_CN.md)）
4. **部署到云端**：参考 [Docker 部署指南](versions/002/README_DOCKER.md)
5. **遇到问题**：查看 `versions/002/output/backtest_logs/` 中的日志文件

---

## ✅ 检查清单

- [ ] 已进入 `versions/002` 目录
- [ ] 已运行 `python scripts/backtest_quick.py quick`
- [ ] 已查看生成的图表
- [ ] 已理解关键性能指标
- [ ] 已阅读 [完整指南](versions/002/docs/BACKTEST_GUIDE_CN.md)
- [ ] 准备好进行深度分析或部署

---

**准备好了？开始你的第一次回测！** 🚀

```bash
cd versions/002
python scripts/backtest_quick.py quick
```

祝交易顺利！🎉
