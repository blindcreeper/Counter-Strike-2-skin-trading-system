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
        self.last_bind_time = 0
        self.ip_bound = False
        self.last_csqaq_request_time = 0

    def _respect_csqaq_rate_limit(self):
        """CSQAQ public API limit: 1 request per second per IP."""
        now_ts = time.time()
        wait_sec = 1.05 - (now_ts - self.last_csqaq_request_time)
        if wait_sec > 0:
            time.sleep(wait_sec)
        self.last_csqaq_request_time = time.time()
        
    def bind_local_ip(self):
        """
        绑定本机IP到CSQAQ白名单
        频率限制：30秒/次
        """
        current_time = time.time()
        
        if current_time - self.last_bind_time < 30:
            print(f"[!] 绑定IP频率限制，等待 {30 - int(current_time - self.last_bind_time)} 秒")
            return False
        
        url = f"{self.csqaq_base}/api/v1/sys/bind_local_ip"
        headers = {
            "ApiToken": self.csqaq_token,
            "Content-Type": "application/json",
            "User-Agent": "CS2-Quant-Trading/2.0"
        }
        
        try:
            print(f"[*] 正在绑定本机IP到CSQAQ白名单...")
            response = requests.post(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    self.last_bind_time = current_time
                    print(f"[OK] {data.get('data', '绑定成功')}")
                    return True
                else:
                    print(f"[X] 绑定失败: {data.get('msg', '未知错误')}")
            elif response.status_code == 429:
                print(f"[!] 绑定频率过快，请等待30秒再试")
                self.last_bind_time = current_time
            else:
                print(f"[X] 绑定请求失败，状态码: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"[!] 绑定IP请求超时")
        except Exception as e:
            print(f"[!] 绑定IP时发生错误: {str(e)}")
        
        return False
    
    def ensure_ip_bound(self):
        """确保IP已绑定（只绑一次）"""
        if self.ip_bound:
            return True
        success = self.bind_local_ip()
        if success:
            self.ip_bound = True
        return success
    
    def get_series_list(self):
        """[CSQAQ] 获取热门系列列表"""
        self.ensure_ip_bound()
        self._respect_csqaq_rate_limit()
        
        url = f"{self.csqaq_base}/api/v1/info/get_series_list"
        headers = {"ApiToken": self.csqaq_token}
        try:
            res = requests.post(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("code") == 200:
                    return data.get("data", [])
        except Exception as e:
            print(f"[!] 获取热门系列列表失败: {e}")
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
        except Exception:
            pass
        return 0

    def get_kline(self, name, kline_type=2):
        """
        [SteamDT] 获取K线历史数据
        kline_type: 1=时K, 2=日K, 3=周K
        Returns: list of [timestamp, close, open, high, low]
        Rate limit: 120/min
        """
        url = f"{self.sdt_base}/open/cs2/item/v1/kline"
        payload = {"marketHashName": name, "type": kline_type}
        try:
            res = requests.post(url, json=payload, headers=self.sdt_headers, timeout=15)
            data = res.json()
            if data.get("success"):
                return data.get("data", [])
        except Exception as e:
            print(f"[!] kline请求失败 {name[:30]}: {e}")
        return []

    def get_batch_sdt(self, names):
        """[SteamDT] 批量获取当前最低价"""
        url = f"{self.sdt_base}/open/cs2/v1/price/batch"
        payload = {"marketHashNames": names}
        try:
            res = requests.post(url, json=payload, headers=self.sdt_headers, timeout=20)
            data = res.json()
            return data.get("data", []) if data.get("success") else []
        except Exception:
            return []

    def get_batch_csqaq(self, names):
        """[CSQAQ] 批量获取参考价"""
        if not self.ensure_ip_bound():
            print("[!] 警告: IP绑定失败，CSQAQ API调用可能被拒绝")
        
        url = f"{self.csqaq_base}/api/v1/goods/getPriceByMarketHashName"
        headers = {
            "ApiToken": self.csqaq_token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        payload = {"marketHashNameList": names}
        
        for attempt in range(3):
            try:
                self._respect_csqaq_rate_limit()
                response = requests.post(url, json=payload, headers=headers, timeout=20)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        result = data.get("data", {})
                        if isinstance(result, dict):
                            return result.get("success", result)
                elif response.status_code == 401:
                    print("[X] CSQAQ 授权失败: 请确认ApiToken是否正确")
                    return {}
                elif response.status_code in (429, 503):
                    wait_sec = min(2 + attempt, 5)
                    print(f"[!] CSQAQ 限流/网关繁忙({response.status_code})，{wait_sec}s 后重试")
                    time.sleep(wait_sec)
                    continue
                else:
                    print(f"[?] CSQAQ 返回异常状态码: {response.status_code}")
            except Exception as e:
                print(f"[!] CSQAQ 请求异常: {e}")
                if attempt < 2:
                    time.sleep(2 + attempt)
                    continue
        return {}
