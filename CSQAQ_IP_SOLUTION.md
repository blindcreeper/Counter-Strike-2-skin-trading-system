# CSQAQ IP白名单解决方案（GitHub Actions）

## 核心问题
GitHub Actions使用动态IP，无法预先添加到CSQAQ白名单。

## 解决方案

### 方案1：使用代理服务（推荐）
部署一个有固定IP的代理API，GitHub Actions调用代理，代理再调用CSQAQ。

#### 部署选项：
1. **Azure Functions** - 免费额度，有固定出站IP
2. **AWS Lambda** - 配合VPC有固定IP
3. **云服务器** - 简单但需要维护

#### 代理代码示例：
```python
# 在代理服务中
import requests
import os

def proxy_csqaq(request):
    token = os.environ["CSQAQ_TOKEN"]
    headers = {"ApiToken": token}
    
    # 转发请求
    response = requests.post(
        "https://api.csqaq.com/api/v1/...",
        json=request.get_json(),
        headers=headers
    )
    return response.json()
```

### 方案2：使用GitHub Actions固定IP段
如果CSQAQ支持CIDR格式，添加GitHub的IP范围：
```
140.82.112.0/20
192.30.252.0/22
185.199.108.0/22
```

获取最新IP：`curl -s https://api.github.com/meta | jq .actions`

### 方案3：修改API调用方式
1. 使用服务器中转
2. 预取数据并缓存
3. 降低调用频率

## 实施步骤

### 短期方案（先让系统运行）：
1. 在CSQAQ控制台添加GitHub Actions IP范围
2. 测试API调用是否成功

### 长期方案（稳定可靠）：
1. 部署Azure Functions代理
2. 获取代理服务固定IP
3. 将代理IP添加到CSQAQ白名单
4. 修改代码调用代理

## 代码修改

修改 `src/api_client.py` 的 `MarketAPI` 类，添加代理支持：

```python
def __init__(self, sdt_key, csqaq_token, proxy_url=None):
    # ... 原有代码
    self.proxy_url = proxy_url
    
def get_batch_csqaq(self, names):
    if self.proxy_url:
        url = f"{self.proxy_url}/proxy/csqaq"
        headers = {"Content-Type": "application/json"}
    else:
        url = f"{self.csqaq_base}/api/v1/goods/getPriceByMarketHashName"
        headers = {"ApiToken": self.csqaq_token}
    # ...
```

## GitHub Actions配置

### 使用代理时：
```yaml
env:
  CSQAQ_TOKEN: ${{ secrets.CSQAQ_TOKEN }}
  PROXY_URL: ${{ secrets.PROXY_URL }}
```

### 直接使用IP范围时：
联系CSQAQ技术支持，请求添加GitHub IP段。

## 验证方法

1. 手动触发GitHub Actions工作流
2. 检查API调用是否返回200状态码
3. 查看CSQAQ API访问日志确认IP
4. 如果失败，在代理服务中添加日志调试

## 成本考虑

- **Azure Functions**: 每月100万次免费调用
- **AWS Lambda**: 每月100万次免费请求
- **云服务器**: 最低配置约$5/月
- **GitHub Actions**: 免费额度2000分钟/月

## 推荐方案

对于生产环境，建议使用：
1. **Azure Functions**（最简单，有固定IP）
2. 将函数URL添加到CSQAQ白名单
3. GitHub Actions调用函数代理

这样只需要维护一个固定IP，且Azure Functions有免费额度。

