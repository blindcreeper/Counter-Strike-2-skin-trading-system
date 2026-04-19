import requests

class MarketAPI:

    def get_series_list(self):
        """[CSQAQ] 获取热门系列列表 (用于宏观趋势分析)"""
        url = f"{self.csqaq_base}/api/v1/info/get_series_list"
        headers = {"ApiToken": self.csqaq_token}
        try:
            res = requests.post(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("code") == 200:
                    return data.get("data", [])
        except Exception as e:
            print(f"❌ 获取热门系列失败: {e}")
        return []
    
    def __init__(self, sdt_key, csqaq_token):
        # 1. SteamDT 配置 (已验证成功)
        self.sdt_base = "https://open.steamdt.com"
        self.sdt_headers = {
            "Authorization": f"Bearer {sdt_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # 2. CSQAQ 配置 (根据最新规范修复)
        self.csqaq_base = "https://api.csqaq.com"
        self.csqaq_token = csqaq_token

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
        [CSQAQ] 批量获取参考价 (严格对标规范)
        API 功能: 批量获取饰品价格和在售数据
        """
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
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("code") == 200:
                    # 返回规范中的 success 字典 (包含各平台在售价格)
                    return data.get("data", {}).get("success", {})
            elif res.status_code == 401:
                print("❌ CSQAQ 鉴权失败: 请确认 ApiToken 是否正确")
            else:
                print(f"⚠️ CSQAQ 返回异常状态码: {res.status_code}")
        except Exception as e:
            print(f"❌ CSQAQ 请求异常: {e}")
        return {}