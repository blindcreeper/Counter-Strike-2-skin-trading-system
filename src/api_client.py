import requests
import time

class MarketAPI:
    
    def __init__(self, sdt_key, csqaq_token):
        # 1. SteamDT配置
        self.sdt_base = "https://open.steamdt.com"
        self.sdt_headers = {
            "Authorization": f"Bearer {sdt_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # 2. CSQAQ配置
        self.csqaq_base = "https://api.csqaq.com"
        self.csqaq_token = csqaq_token
        self.last_bind_time = 0  # 上次绑定时间戳
        self.ip_bound = False    # 是否已成功绑定IP
        
    def bind_local_ip(self):
        """
        绑定本机IP到CSQAQ白名单
        频率限制：30秒/次
        """
        current_time = time.time()
        
        # 检查频率限制
        if current_time - self.last_bind_time < 30:
            print(f"? 绑定IP频率限制，等待 {30 - int(current_time - self.last_bind_time)} 秒")
            return False
        
        url = f"{self.csqaq_base}/api/v1/sys/bind_local_ip"
        headers = {
            "ApiToken": self.csqaq_token,
            "Content-Type": "application/json",
            "User-Agent": "CS2-Quant-Trading/2.0"
        }
        
        try:
            print(f"? 正在绑定本机IP到CSQAQ白名单...")
            response = requests.post(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    self.last_bind_time = current_time
                    print(f"? {data.get('data', '绑定成功')}")
                    return True
                else:
                    print(f"? 绑定失败: {data.get('msg', '未知错误')}")
            elif response.status_code == 429:
                print(f"? 绑定频率过快，请等待30秒再试")
                self.last_bind_time = current_time
            else:
                print(f"? 绑定请求失败，状态码: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"? 绑定IP请求超时")
        except Exception as e:
            print(f"? 绑定IP时发生错误: {str(e)}")
            
        return False
    
    def ensure_ip_bound(self):\n        """确保IP已绑定（只绑一次）"""\n        if self.ip_bound:\n            return True\n        success = self.bind_local_ip()\n        if success:\n            self.ip_bound = True\n        return success
    
    def get_series_list(self):
        """[CSQAQ] 获取热门系列列表（用于趋势分析）"""
        # 确保IP已绑定
        self.ensure_ip_bound()
        
        url = f"{self.csqaq_base}/api/v1/info/get_series_list"
        headers = {"ApiToken": self.csqaq_token}
        try:
            res = requests.post(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("code") == 200:
                    return data.get("data", [])
        except Exception as e:
            print(f"? 获取热门系列列表失败: {e}")
        return []
    
    def get_7d_avg_price(self, name):
        """[SteamDT] 查询7天均价"""
        url = f"{self.sdt_base}/open/cs2/v1/price/avg"
        params = {"marketHashName": name}
        try:
            res = requests.get(url, params=params, headers=self.sdt_headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("success"):
                    return data["data"].get("avgPrice", 0)
        except: pass
        return 0

    def get_batch_sdt(self, names):
        """[SteamDT] 批量获取当前最低价"""
        url = f"{self.sdt_base}/open/cs2/v1/price/batch"
        payload = {"marketHashNames": names}
        try:
            res = requests.post(url, json=payload, headers=self.sdt_headers, timeout=20)
            data = res.json()
            return data.get("data", []) if data.get("success") else []
        except: return []

    def get_batch_csqaq(self, names):
        """
        [CSQAQ] 批量获取参考价（严格对标规范）
        API功能：批量获取饰品价格和在售数据
        """
        # 确保IP已绑定
        if not self.ensure_ip_bound():
            print("? 警告: IP绑定失败，CSQAQ API调用可能被拒绝")
        
        url = f"{self.csqaq_base}/api/v1/goods/getPriceByMarketHashName"
        
        # 规范要求: ApiToken 必须放在 Header 中
        headers = {
            "ApiToken": self.csqaq_token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # 规范要求: 字段名为 marketHashNameList
        payload = {"marketHashNameList": names}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    # 返回规范中的 success 字典（包含各平台在售价）
                    return data.get("data", {}).get("success", {})
            elif response.status_code == 401:
                print("? CSQAQ 授权失败: 请确认ApiToken是否正确")
            else:
                print(f"?? CSQAQ 返回异常状态码: {response.status_code}")
        except Exception as e:
            print(f"? CSQAQ 请求异常: {e}")
        return {}
