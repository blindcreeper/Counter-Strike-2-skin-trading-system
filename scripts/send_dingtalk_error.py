"""
GitHub Actions 钉钉失败通知脚本
"""

import os
import sys
import json
import requests
from datetime import datetime

def send_error_notification(webhook_url, error_message):
    """发送错误通知到钉钉"""
    
    if not webhook_url:
        print("❌ 钉钉 Webhook 未配置")
        return False
    
    try:
        # 获取运行环境信息
        github_run_id = os.getenv('GITHUB_RUN_ID', 'N/A')
        github_run_number = os.getenv('GITHUB_RUN_NUMBER', 'N/A')
        github_sha = os.getenv('GITHUB_SHA', 'N/A')[:7]
        github_ref = os.getenv('GITHUB_REF', 'N/A').replace('refs/heads/', '')
        github_actor = os.getenv('GITHUB_ACTOR', 'Unknown')
        github_server_url = os.getenv('GITHUB_SERVER_URL', 'https://github.com')
        github_repository = os.getenv('GITHUB_REPOSITORY', '')
        
        # 构建钉钉消息
        md_text = f"""## ⚠️ CS2回测失败告警

**运行信息：**
- 分支: `{github_ref}`
- 提交: [{github_sha}]({github_server_url}/{github_repository}/commit/{os.getenv('GITHUB_SHA', '')})
- 执行者: `{github_actor}`
- 工作流ID: #{github_run_number}

**失败原因：**
```
{error_message}
```

**排查链接：**
[查看完整日志]({github_server_url}/{github_repository}/actions/runs/{github_run_id})

---
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
"""
        
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": "⚠️ 回测流程失败告警",
                "text": md_text
            }
        }
        
        # 发送请求
        response = requests.post(webhook_url, json=message, timeout=20)
        
        payload = None
        try:
            payload = response.json()
        except:
            pass
        
        # 检查响应
        if response.status_code == 200:
            if isinstance(payload, dict) and payload.get("errcode", 0) == 0:
                print("✅ 错误通知已发送到钉钉")
                return True
            else:
                err_code = payload.get('errcode', 'Unknown') if payload else 'Unknown'
                err_msg = payload.get('errmsg', 'Unknown') if payload else 'Unknown'
                print(f"❌ 钉钉API错误: {err_code} - {err_msg}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发送通知异常: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='发送GitHub Actions回测失败通知')
    parser.add_argument('--webhook', required=True, help='钉钉Webhook URL')
    parser.add_argument('--error', default='回测流程执行失败，请查看日志获取详情', help='错误信息')
    
    args = parser.parse_args()
    
    success = send_error_notification(args.webhook, args.error)
    sys.exit(0 if success else 1)
