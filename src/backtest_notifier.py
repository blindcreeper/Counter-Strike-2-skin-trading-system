"""
回测通知提醒模块 - 邮件、日志、钉钉等多渠道通知
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os


def _format_factor_section(factor_report):
    if not factor_report:
        return "- 暂无因子评估数据"
    lines = [f"- 样本数: {factor_report.get('sample_count', 0)}"]
    for label, stats in sorted((factor_report.get("edge_groups") or {}).items()):
        if not stats:
            continue
        lines.append(
            f"- Edge {label}: 命中{stats['hit_rate']:.1%} 达标{stats['target_hit_rate']:.1%} 平均72h{stats['avg_outcome_72h']:.2%}"
        )
    for label, stats in sorted((factor_report.get("score_groups") or {}).items()):
        if not stats:
            continue
        lines.append(
            f"- Score {label}: 命中{stats['hit_rate']:.1%} 达标{stats['target_hit_rate']:.1%} 平均72h{stats['avg_outcome_72h']:.2%}"
        )
    return "\n".join(lines)


class BacktestNotifier:
    """回测通知器"""
    
    def __init__(self, log_dir=None):
        self.log_dir = log_dir or "./backtest_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, f"backtest_{datetime.now().strftime('%Y%m%d')}.log")
    
    def log(self, level, message):
        """写入日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + "\n")
        
        print(log_message)
    
    def log_backtest_start(self, initial_balance, opportunities_count):
        """记录回测开始"""
        msg = f"🚀 回测开始 | 初始资金: ¥{initial_balance:.2f} | 机会数: {opportunities_count}"
        self.log("INFO", msg)
    
    def log_backtest_end(self, metrics):
        """记录回测结束"""
        msg = f"""
✅ 回测完成
   总收益: ¥{metrics['total_profit']:.2f}
   收益率: {metrics['total_return']:.2%}
   胜率: {metrics['win_rate']:.2%}
   最大回撤: {metrics['max_drawdown']:.2%}
        """
        self.log("INFO", msg)
    
    def log_trade(self, trade):
        """记录单笔交易"""
        status = "✅" if trade['profit_rate'] > 0 else "❌"
        msg = f"{status} 交易: {trade['name']} | 买:{trade['buy_price']:.2f} 卖:{trade['sell_price']:.2f} | 利率:{trade['profit_rate']:.2%}"
        self.log("TRADE", msg)
    
    def log_trade_error(self, name, error):
        """记录交易错误"""
        msg = f"⚠️  {name} 交易失败: {error}"
        self.log("ERROR", msg)
    
    def send_email(self, recipient_email, subject, body, metrics=None, smtp_config=None):
        """发送邮件通知"""
        if not smtp_config:
            self.log("WARN", "未提供SMTP配置，跳过邮件发送")
            return False
        
        try:
            # 创建邮件内容
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_config['sender']
            msg['To'] = recipient_email
            
            # HTML邮件体
            html_body = self._build_email_html(body, metrics)
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            server.starttls()
            server.login(smtp_config['sender'], smtp_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.log("INFO", f"✉️  邮件已发送到 {recipient_email}")
            return True
            
        except Exception as e:
            self.log("ERROR", f"邮件发送失败: {str(e)}")
            return False
    
    def _build_email_html(self, body, metrics):
        """构建HTML邮件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        metrics_html = ""
        if metrics:
            metrics_html = f"""
            <table style="width:100%; border-collapse: collapse; margin-top: 20px;">
                <tr style="background-color: #f0f0f0;">
                    <th style="border: 1px solid #ddd; padding: 10px;">指标</th>
                    <th style="border: 1px solid #ddd; padding: 10px;">数值</th>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 10px;">初始资金</td>
                    <td style="border: 1px solid #ddd; padding: 10px;">¥{metrics.get('initial_balance', 10000):.2f}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 10px;">最终资金</td>
                    <td style="border: 1px solid #ddd; padding: 10px;">¥{metrics['final_balance']:.2f}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 10px;">总收益</td>
                    <td style="border: 1px solid #ddd; padding: 10px;">¥{metrics['total_profit']:.2f}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 10px;">收益率</td>
                    <td style="border: 1px solid #ddd; padding: 10px; color: {'green' if metrics['total_return'] > 0 else 'red'};">
                        {metrics['total_return']:.2%}
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 10px;">胜率</td>
                    <td style="border: 1px solid #ddd; padding: 10px;">{metrics['win_rate']:.2%}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 10px;">最大回撤</td>
                    <td style="border: 1px solid #ddd; padding: 10px;">{metrics['max_drawdown']:.2%}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 10px;">夏普比率</td>
                    <td style="border: 1px solid #ddd; padding: 10px;">{metrics['sharpe_ratio']:.2f}</td>
                </tr>
            </table>
            """
        
        html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #2E86AB; color: white; padding: 20px; border-radius: 5px; }}
                    h1 {{ margin: 0; }}
                    .timestamp {{ font-size: 12px; opacity: 0.8; }}
                    .content {{ margin-top: 20px; line-height: 1.6; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 CS2 量化回测报告</h1>
                        <div class="timestamp">{timestamp}</div>
                    </div>
                    <div class="content">
                        <p>{body}</p>
                        {metrics_html}
                    </div>
                </div>
            </body>
        </html>
        """
        return html
    
    def send_dingtalk(self, webhook_url, metrics, trades=None, factor_report=None, max_retries=3, retry_delay=2):
        """发送钉钉通知（支持重试和GitHub Actions环境）
        
        Args:
            webhook_url: 钉钉webhook地址
            metrics: 回测指标字典
            trades: 交易列表
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        
        Returns:
            bool: 是否发送成功
        """
        try:
            import requests
            import time

            trades = trades or []
            
            # 检测运行环境
            is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
            run_number = os.getenv('GITHUB_RUN_NUMBER', 'N/A')
            github_ref = os.getenv('GITHUB_REF', 'main').replace('refs/heads/', '')
            github_actor = os.getenv('GITHUB_ACTOR', 'local-user')
            
            # 构建交易明细
            trade_lines = []
            for idx, trade in enumerate(trades[:10], 1):
                name = str(trade.get("name", "Unknown"))[:40]
                buy_price = float(trade.get("buy_price", 0) or 0)
                sell_price = float(trade.get("sell_price", 0) or 0)
                net_profit = float(trade.get("net_profit", 0) or 0)
                profit_rate = float(trade.get("profit_rate", 0) or 0)
                buy_time = str(trade.get("buy_time") or trade.get("timestamp") or "-")
                sell_time = str(trade.get("sell_time") or "-")
                trade_lines.append(
                    f"{idx}. {name} | 买:{buy_price:.2f} 卖:{sell_price:.2f} | "
                    f"买入:{buy_time} 卖出:{sell_time} | 利润:{net_profit:.2f} ({profit_rate:.2%})"
                )

            trade_block = "\n".join(f"- {line}" for line in trade_lines) if trade_lines else "- 无交易数据"
            if len(trades) > 10:
                trade_block += f"\n- ... 其余 {len(trades) - 10} 笔交易"
            
            # 构建环境信息
            env_info = ""
            if is_github_actions:
                env_info = f"\n\n触发者: `{github_actor}` | 分支: `{github_ref}` | 工作流 #{run_number}"
            
            # 构建评分指示
            score_indicator = self._get_score_indicator(metrics)
            factor_block = _format_factor_section(factor_report)
            
            # 构建钉钉Markdown消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"{score_indicator} CS2量化回测完成",
                    "text": f"""## {score_indicator} 虚拟回测结果

**📊 核心指标：**
- 初始资金: **¥{metrics.get('initial_balance', 10000):.2f}**
- 最终资金: **¥{metrics['final_balance']:.2f}**
- 总收益: **¥{metrics['total_profit']:.2f}** | 收益率: **{metrics['total_return']:.2%}**
- 交易笔数: {metrics['total_trades']} | 胜率: **{metrics['win_rate']:.2%}**
- 最大回撤: **{metrics['max_drawdown']:.2%}** | 夏普比率: **{metrics['sharpe_ratio']:.2f}**

**📈 风险指标：**
- 平均收益: ¥{metrics.get('avg_profit', 0):.2f}
- 最好交易: ¥{metrics.get('max_profit_trade', 0):.2f}
- 最差交易: ¥{metrics.get('max_loss_trade', 0):.2f}
- 赢家笔数: {metrics.get('winning_trades', 0)} | 输家笔数: {metrics.get('losing_trades', 0)}

**📦 交易明细（最多10笔）：**
{trade_block}

**🧠 因子命中率：**
{factor_block}

---
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{env_info}
                    """
                }
            }
            
            # 带重试的发送
            last_exception = None
            for attempt in range(max_retries):
                try:
                    response = requests.post(webhook_url, json=message, timeout=20)
                    
                    # 解析响应
                    try:
                        payload = response.json()
                    except Exception:
                        payload = None

                    # 检查钉钉API响应
                    if response.status_code == 200:
                        errcode = payload.get('errcode', 0) if isinstance(payload, dict) else 0
                        
                        if errcode == 0:
                            self.log("INFO", f"✅ 钉钉通知成功发送（第{attempt + 1}次尝试）")
                            return True
                        else:
                            errmsg = payload.get('errmsg', '未知错误') if isinstance(payload, dict) else '未知错误'
                            last_exception = f"DingTalk API错误: errcode={errcode}, errmsg={errmsg}"
                            
                            # 某些错误可重试，某些不能
                            if errcode in [40001, 40002, 45019]:  # token过期、限流等
                                if attempt < max_retries - 1:
                                    self.log("WARN", f"钉钉API错误（可重试）: {last_exception}，等待{retry_delay}秒后重试...")
                                    time.sleep(retry_delay)
                                    continue
                            
                            self.log("ERROR", f"钉钉API错误（不可重试）: {last_exception}")
                            return False
                    else:
                        last_exception = f"HTTP {response.status_code}: {response.text[:100]}"
                        if attempt < max_retries - 1:
                            self.log("WARN", f"HTTP错误（可重试）: {last_exception}，等待{retry_delay}秒后重试...")
                            time.sleep(retry_delay)
                        else:
                            self.log("ERROR", f"HTTP错误（已尝试{max_retries}次）: {last_exception}")
                            return False
                
                except requests.Timeout as e:
                    last_exception = f"请求超时: {str(e)}"
                    if attempt < max_retries - 1:
                        self.log("WARN", f"网络超时（可重试）: {last_exception}，等待{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        self.log("ERROR", f"网络超时（已尝试{max_retries}次）: {last_exception}")
                        return False
                
                except requests.ConnectionError as e:
                    last_exception = f"连接失败: {str(e)}"
                    if attempt < max_retries - 1:
                        self.log("WARN", f"连接失败（可重试）: {last_exception}，等待{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        self.log("ERROR", f"连接失败（已尝试{max_retries}次）: {last_exception}")
                        return False
            
            self.log("ERROR", f"钉钉通知最终失败: {last_exception}")
            return False
                
        except Exception as e:
            self.log("ERROR", f"钉钉通知异常: {type(e).__name__}: {str(e)}")
            return False
    
    def _get_score_indicator(self, metrics):
        """根据指标返回评分表情"""
        total_return = metrics.get('total_return', 0)
        win_rate = metrics.get('win_rate', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        
        # 基于综合指标评分
        if total_return > 0.1 and win_rate > 0.55 and sharpe > 1.5:
            return "🤑"  # 优秀
        elif total_return > 0.05 and win_rate > 0.5 and sharpe > 1.0:
            return "😊"  # 良好
        elif total_return > 0 and win_rate > 0.45:
            return "😐"  # 一般
        else:
            return "😞"  # 需改进
    
    def export_report(self, metrics, trades, filename=None):
        """导出JSON报告"""
        if filename is None:
            filename = os.path.join(self.log_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'initial_balance': metrics.get('initial_balance', 10000),
                'final_balance': metrics['final_balance'],
                'total_profit': metrics['total_profit'],
                'total_return': metrics['total_return'],
                'total_trades': metrics['total_trades'],
                'winning_trades': metrics['winning_trades'],
                'losing_trades': metrics['losing_trades'],
                'win_rate': metrics['win_rate'],
                'avg_profit': metrics['avg_profit'],
                'max_profit_trade': metrics['max_profit_trade'],
                'max_loss_trade': metrics['max_loss_trade'],
                'avg_return': metrics['avg_return'],
                'best_return': metrics['best_return'],
                'worst_return': metrics['worst_return'],
                'max_drawdown': metrics['max_drawdown'],
                'sharpe_ratio': metrics['sharpe_ratio']
            },
            'trades': trades
        }

        def _json_default(value):
            """Handle pandas/python datetime-like objects during JSON export."""
            if hasattr(value, "isoformat"):
                try:
                    return value.isoformat()
                except Exception:
                    pass
            return str(value)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=_json_default)
        
        self.log("INFO", f"📄 报告已导出到 {filename}")
        return filename
