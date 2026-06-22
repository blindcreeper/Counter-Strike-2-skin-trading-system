"""
虚拟资金模拟回测引擎 - 完整的交易环境模拟
支持：虚拟账户、交易模拟、风险指标、详细统计
"""

import csv
import pandas as pd
import numpy as np
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CONFIG

from api_client import MarketAPI


# Minimum holding period for backtest (hours)
def get_holding_period():
    return CONFIG.get("HOLDING_PERIOD_HOURS", 72)


class VirtualAccount:
    """虚拟账户 - 模拟真实交易账户"""
    
    def __init__(self, initial_balance=10000):
        self.initial_balance = initial_balance
        self.balance = initial_balance  # 当前现金
        self.positions = {}  # 持仓 {商品名: 数量}
        self.position_cost = {}  # 持仓成本 {商品名: 平均买入价}
        self.trades = []  # 已完成交易记录
        self.daily_values = []  # 每日账户价值
        self.position_buy_time = {}  # 跟踪持仓买入时间
        
    def buy(self, name, quantity, price, timestamp):
        """买入操作"""
        cost = quantity * price * (1 + CONFIG.get("FEE_RATE", 0.025))  # 加手续费
        
        if cost > self.balance:
            return False, f"余额不足：需要 ¥{cost:.2f}，现有 ¥{self.balance:.2f}"
        
        self.balance -= cost
        if name not in self.positions:
            self.positions[name] = 0
            self.position_cost[name] = 0
        
        # 更新平均成本
        old_qty = self.positions[name]
        old_cost = self.position_cost[name]
        self.positions[name] += quantity
        self.position_cost[name] = (old_qty * old_cost + quantity * price) / self.positions[name]
        
        self.trades.append({
            'type': 'BUY',
            'name': name,
            'quantity': quantity,
            'price': price,
            'cost': cost,
            'timestamp': timestamp
        })
        return True, f"✅ 买入 {quantity} 个 {name}，成本 ¥{cost:.2f}"
    
    def sell(self, name, quantity, price, timestamp):
        """卖出操作"""
        if name not in self.positions or self.positions[name] < quantity:
            return False, f"持仓不足：需要 {quantity} 个，现有 {self.positions.get(name, 0)} 个"
        
        # 检查持有时间
        buy_time_str = self.position_buy_time.get(name)
        if buy_time_str:
            try:
                buy_dt = datetime.strptime(str(buy_time_str), "%Y-%m-%d %H:%M:%S")
                sell_dt = datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S")
                holding_hours = (sell_dt - buy_dt).total_seconds() / 3600
                if holding_hours < get_holding_period():
                    return False, f"持有期不足：需 {get_holding_period()}h，当前仅 {holding_hours:.1f}h"
            except:
                pass
        
        revenue = quantity * price * (1 - CONFIG.get("FEE_RATE", 0.025))  # 扣手续费
        profit = revenue - quantity * self.position_cost[name]
        
        self.balance += revenue
        self.positions[name] -= quantity
        if self.positions[name] == 0:
            del self.positions[name]
            del self.position_cost[name]
            if name in self.position_buy_time:
                del self.position_buy_time[name]
        
        self.trades.append({
            'type': 'SELL',
            'name': name,
            'quantity': quantity,
            'price': price,
            'revenue': revenue,
            'profit': profit,
            'timestamp': timestamp
        })
        return True, f"✅ 卖出 {quantity} 个 {name}，收入 ¥{revenue:.2f}，利润 ¥{profit:.2f}"
    
    def get_total_value(self, current_prices):
        """获取账户总价值 = 现金 + 持仓时价值"""
        position_value = sum(
            self.positions[name] * current_prices.get(name, self.position_cost[name])
            for name in self.positions
        )
        return self.balance + position_value
    
    def get_unrealized_pnl(self, current_prices):
        """获取未实现盈亏"""
        pnl = 0
        for name, qty in self.positions.items():
            current_price = current_prices.get(name, self.position_cost[name])
            pnl += qty * (current_price - self.position_cost[name])
        return pnl
    
    def to_dict(self):
        """转为字典"""
        return {
            'balance': self.balance,
            'positions': self.positions.copy(),
            'position_cost': self.position_cost.copy()
        }


class BacktestEngine:
    """回测引擎 - 核心仿真和统计"""
    
    def __init__(self, initial_balance=10000, csv_path=None):
        self.account = VirtualAccount(initial_balance)
        self.api = MarketAPI(CONFIG["SDT_KEY"], CONFIG["CSQAQ_TOKEN"])
        self.csv_path = csv_path or CONFIG.get("LOG_FILE")
        self.backtest_results = []
        
    def load_opportunities(self, hours_back=72):
        """加载回测数据并标准化时间字段"""
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"找不到数据文件: {self.csv_path}")

        rows = []
        with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for line_num, row in enumerate(reader, start=2):
                if not row:
                    continue
                try:
                    # DictReader 对于超出列头的字段会放到 None 键，直接忽略
                    cleaned = {k: (v if v is not None else "") for k, v in row.items() if k is not None}
                    rows.append(cleaned)
                except Exception as e:
                    print(f"⚠️  第 {line_num} 行解析失败: {str(e)[:50]}")
                    continue

        if not rows:
            print("⚠️  CSV 文件为空")
            return []

        df = pd.DataFrame(rows)

        if "time" not in df.columns:
            print("⚠️  CSV 缺少 time 列，无法进行时间过滤")
            return []

        # 标准化 time 列为 datetime，再统一为字符串
        current_year = datetime.now().year
        df["time"] = df["time"].astype(str).str.strip().apply(
            lambda x: f"{current_year}-{x}" if x and not x.startswith("20") else x
        )
        df["time"] = pd.to_datetime(df["time"], format="mixed", errors="coerce")
        df = df[df["time"].notna()].copy()

        if df.empty:
            print("⚠️  没有可解析的时间数据")
            return []

        # 按时间过滤
        now = datetime.now()
        start_time = now - timedelta(hours=hours_back)
        samples = df[df["time"] >= start_time].copy()

        if samples.empty:
            # 如果符合时间条件的数据为空，使用全部数据进行回测
            print(f"⚠️  暂无 {hours_back} 小时内的数据，使用全部历史数据进行回测")
            samples = df.copy()

        if samples.empty:
            print("⚠️  没有可用的回测数据")
            return []

        samples = samples.sort_values("time").copy()
        samples["time"] = samples["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return samples.to_dict("records")
    
    def _get_historical_sell_price(self, name, sell_dt):
        """从 price_history 表获取 sell_dt 附近的历史价格。
        数据库保留最近 240 个采样点（约 200 小时），覆盖 7 天锁仓期的回测。
        """
        try:
            from database import MarketDB
            db_path = CONFIG.get("DB_NAME", "cs2_quant.db")
            db = MarketDB(db_path)
            target_ts = int(sell_dt.timestamp())
            price, actual_ts = db.get_price_near_time(name, target_ts, window_seconds=7200)
            if price is not None and price > 0:
                hours_diff = (actual_ts - target_ts) / 3600 if actual_ts else 999
                if abs(hours_diff) < 24:  # 只接受卖点 ±24 小时内的价格
                    return price
        except Exception:
            pass
        return None

    def _resolve_sell_price(self, name, buy_price, csv_sell_price_str, latest_sell_prices, sell_dt):
        """确定卖出价格，优先级：
        1. CSQAQ 实时 API（模拟"当前卖出"场景）→ 🟢 live
        2. 数据库历史价格（买入后锁仓期附近的价格）→ 🗄️ hist
        3. CSV 记录的卖出参考价（BUY 当天 Buff 价）→ 📄 csv
        4. buy_price × 1.03 估算 → 📝 est
        """
        # 1. 实时 API
        if name in latest_sell_prices:
            return float(latest_sell_prices[name]), "live"

        # 2. 数据库历史价格
        hist_price = self._get_historical_sell_price(name, sell_dt)
        if hist_price is not None and hist_price > 0:
            return hist_price, "hist"

        # 3. CSV 卖出参考价
        if csv_sell_price_str and str(csv_sell_price_str).strip() not in ['', 'None']:
            try:
                return float(str(csv_sell_price_str).replace('%', '')), "csv"
            except (ValueError, TypeError):
                pass

        # 4. 估算
        return buy_price * 1.03, "est"

    def _get_price_series_for_window(self, name, start_dt, end_dt):
        """从 price_history 表获取 [start_dt, end_dt] 区间内的价格快照，按时间升序。
        返回 [(timestamp, price), ...]，可能为空。
        """
        try:
            from database import MarketDB
            db_path = CONFIG.get("DB_NAME", "cs2_quant.db")
            db = MarketDB(db_path)
            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.timestamp())
            return db.get_price_series_in_range(name, start_ts, end_ts)
        except Exception:
            return []

    def _simulate_position(self, name, buy_price, buy_dt, latest_sell_prices, csv_sell_str):
        """模拟单笔持仓的全生命周期：买入 → 逐日盯市 → 止盈/止损/超时卖出。
        锁仓期内（< MIN_HOLDING_HOURS）不触发止盈/止损，必须持有至少 72h。
        返回 (sell_price, sell_dt, sell_reason, reason_detail) 或 None。
        """
        fee_rate = CONFIG.get("FEE_RATE", 0.025)
        take_profit_rate = CONFIG.get("TAKE_PROFIT_RATE", 0.08)
        stop_loss_rate = CONFIG.get("STOP_LOSS_RATE", -0.05)
        max_hours = get_holding_period()
        min_hours = CONFIG.get("MIN_HOLDING_HOURS", 72)  # 最低锁仓 72h
        max_sell_dt = buy_dt + timedelta(hours=max_hours)
        unlock_dt = buy_dt + timedelta(hours=min_hours)   # 锁仓解禁时间

        # 1. 获取持仓期间的 DB 历史价格
        db_prices = self._get_price_series_for_window(name, buy_dt, max_sell_dt)

        # 2. 逐条检查止盈/止损（跳过锁仓期内的价格点）
        if db_prices:
            for ts, price in db_prices:
                if price <= 0:
                    continue
                check_dt = datetime.fromtimestamp(ts)
                # 锁仓期内不检查止盈/止损
                if check_dt < unlock_dt:
                    continue

                gross_return = (price - buy_price) / buy_price
                net_return = gross_return - 2 * fee_rate

                if net_return >= take_profit_rate:
                    return (price, check_dt, "take_profit",
                            f"止盈 {check_dt.strftime('%m-%d %H:%M')}")
                if net_return <= stop_loss_rate:
                    return (price, check_dt, "stop_loss",
                            f"止损 {check_dt.strftime('%m-%d %H:%M')}")

        # 3. 未触发 → 超时卖出，用 DB 最新价或 API 价
        sell_dt = max_sell_dt
        if db_prices:
            # 取区间内最后一个价格作为超时卖出价
            sell_price = float(db_prices[-1][1])
            price_source = "hist"
            reason_detail = f"超时 {sell_dt.strftime('%m-%d %H:%M')}"
        else:
            sell_price, price_source = self._resolve_sell_price(
                name, buy_price, csv_sell_str, latest_sell_prices, sell_dt
            )
            reason_detail = f"超时(无历史) {sell_dt.strftime('%m-%d %H:%M')}"

        if sell_price <= 0:
            return None

        return (sell_price, sell_dt, "timeout", reason_detail)

    def run_simulation(self, opportunities, initial_balance=10000):
        """运行完整的虚拟交易模拟，含止盈/止损/超时。"""
        self.account = VirtualAccount(initial_balance)
        self.backtest_results = []
        holding_hours = get_holding_period()
        take_profit_rate = CONFIG.get("TAKE_PROFIT_RATE", 0.08)
        stop_loss_rate = CONFIG.get("STOP_LOSS_RATE", -0.05)

        print(f"\n🚀 开始虚拟交易模拟")
        print(f"   初始资金: ¥{initial_balance:.2f}  锁仓上限: {holding_hours}h")
        print(f"   止盈: ≥{take_profit_rate:+.0%}  止损: ≤{stop_loss_rate:+.0%}")
        print(f"   模拟交易数: {len(opportunities)}\n")

        # Batch-fetch current sell prices (用于没有 DB 历史的 fallback)
        unique_names = list({opp.get('name', '') for opp in opportunities if opp.get('name')})
        latest_sell_prices = {}
        if unique_names:
            print(f"📡 获取 {len(unique_names)} 个商品的最新卖出价...")
            for batch_start in range(0, len(unique_names), 50):
                batch = unique_names[batch_start:batch_start + 50]
                try:
                    prices = self.api.get_batch_csqaq(batch)
                    if isinstance(prices, dict):
                        for n, info in prices.items():
                            if isinstance(info, dict):
                                sp = info.get("buffSellPrice") or 0
                                if sp:
                                    latest_sell_prices[n] = float(sp)
                except Exception as e:
                    print(f"⚠️  批量获取价格失败: {e}")
            print(f"   成功获取 {len(latest_sell_prices)} 个商品的当前卖出价\n")

        stats = {"take_profit": 0, "stop_loss": 0, "timeout": 0, "skipped": 0}

        for i, opp in enumerate(opportunities, 1):
            try:
                name = opp.get('name', '')
                buy_price = float(str(opp.get('price', opp.get('buy_price', 0))).replace('%', ''))
                buy_time_str = str(opp.get("time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                try:
                    buy_dt = datetime.strptime(buy_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    buy_dt = datetime.now()
                    buy_time_str = buy_dt.strftime("%Y-%m-%d %H:%M:%S")

                if buy_price <= 0:
                    continue

                # 最低价格过滤（< ¥30 的低价品流动性差、手续费占比高）
                min_price = CONFIG.get("MIN_PRICE", 30)
                if buy_price < min_price:
                    stats["skipped"] += 1
                    continue

                # 模拟持仓生命周期（含止盈/止损/超时）
                csv_sell_str = opp.get('sell_price', '')
                result = self._simulate_position(
                    name, buy_price, buy_dt, latest_sell_prices, csv_sell_str
                )
                if result is None:
                    stats["skipped"] += 1
                    continue

                sell_price, sell_dt, reason, reason_detail = result
                sell_time_str = sell_dt.strftime("%Y-%m-%d %H:%M:%S")

                # 固定仓位：每笔投入约 ¥POSITION_SIZE，按价格取整
                position_size = CONFIG.get("POSITION_SIZE", 500)
                qty = max(1, round(position_size / buy_price))

                buy_success, msg = self.account.buy(name, quantity=qty, price=buy_price, timestamp=buy_time_str)
                if not buy_success:
                    continue

                sell_success, msg = self.account.sell(name, quantity=qty, price=sell_price, timestamp=sell_time_str)
                if not sell_success:
                    print(f"⚠️  {name[:30]} 卖出失败: {msg}")
                    continue

                fee_cost = buy_price * CONFIG.get("FEE_RATE", 0.025)
                fee_rev = sell_price * CONFIG.get("FEE_RATE", 0.025)
                net_profit = (sell_price - buy_price) - fee_cost - fee_rev  # per unit
                profit_rate = net_profit / buy_price if buy_price > 0 else 0
                total_profit = net_profit * qty  # 整笔交易总利润
                actual_hold_h = round((sell_dt - buy_dt).total_seconds() / 3600, 1)

                # 价格来源标注
                if reason == "timeout" and "无历史" in reason_detail:
                    price_source = self._resolve_sell_price(
                        name, buy_price, csv_sell_str, latest_sell_prices, sell_dt
                    )[1]
                elif reason == "timeout":
                    price_source = "hist"
                else:
                    price_source = "hist"  # 止盈/止损都来自 DB 历史价格

                self.backtest_results.append({
                    'name': name,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'net_profit': total_profit,      # 整笔总利润
                    'profit_rate': profit_rate,       # 单单位收益率
                    'quantity': qty,
                    'timestamp': buy_time_str,
                    'buy_time': buy_time_str,
                    'sell_time': sell_time_str,
                    'holding_hours': actual_hold_h,
                    'account_balance': self.account.balance,
                    'price_source': price_source,
                    'close_reason': reason,
                })

                stats[reason] = stats.get(reason, 0) + 1

                src_tag = {"live": "🟢", "hist": "🗄️", "csv": "📄", "est": "📝"}.get(price_source, "?")
                emoji = {"take_profit": "🟢", "stop_loss": "🔴", "timeout": "⏰"}.get(reason, "?")
                print(f"{emoji} [{i:3d}] {name[:22]:<22} | ×{qty} 买{buy_price:7.2f}→卖{sell_price:7.2f} {src_tag} | "
                      f"持{actual_hold_h:5.0f}h | {profit_rate:+.1%} ¥{total_profit:+.1f} | {reason_detail}")

            except Exception as e:
                print(f"⚠️  {opp.get('name', 'Unknown')[:30]} 模拟失败: {str(e)[:50]}")
                continue

        # Summary statistics
        traded = stats["take_profit"] + stats["stop_loss"] + stats["timeout"]
        skipped = stats.get("skipped", 0)
        if traded > 0:
            print(f"\n📊 平仓统计: 🟢止盈{stats['take_profit']} 🔴止损{stats['stop_loss']} "
                  f"⏰超时{stats['timeout']} | 共{traded}笔"
                  + (f" | 跳过{skipped}笔(价格<¥{CONFIG.get('MIN_PRICE', 30):.0f}或无数据)" if skipped else ""))

        return self._calculate_metrics()
    
    def _calculate_metrics(self):
        """计算关键性能指标"""
        if not self.backtest_results:
            # 即使没有交易也返回完整的指标字典
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'avg_profit': 0,
                'max_profit_trade': 0,
                'max_loss_trade': 0,
                'avg_return': 0,
                'best_return': 0,
                'worst_return': 0,
                'final_balance': self.account.initial_balance,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'account_values': [],
                'initial_balance': self.account.initial_balance
            }
        
        df = pd.DataFrame(self.backtest_results)
        
        # 基础指标
        total_trades = len(df)
        winning_trades = (df['profit_rate'] > 0).sum()
        losing_trades = (df['profit_rate'] <= 0).sum()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 盈亏指标
        total_profit = df['net_profit'].sum()
        avg_profit = df['net_profit'].mean()
        max_profit_trade = df['net_profit'].max()
        max_loss_trade = df['net_profit'].min()
        
        # 收益率指标
        avg_return = df['profit_rate'].mean()
        best_return = df['profit_rate'].max()
        worst_return = df['profit_rate'].min()
        
        # 账户曲线：account_balance 已包含逐笔盈亏，无需再加 cumsum
        df['account_value'] = df['account_balance']
        account_values = df['account_value'].fillna(self.account.initial_balance).tolist()
        
        # 确保所有值都是有效的数字
        account_values = [v if pd.notna(v) and v > 0 else self.account.initial_balance for v in account_values]
        final_balance = account_values[-1] if account_values else self.account.initial_balance
        
        # 最大回撤
        try:
            cumulative_max = np.maximum.accumulate(account_values) if account_values else [self.account.initial_balance]
            max_drawdown = min(
                (val - peak) / peak if peak > 0 else 0 
                for val, peak in zip(account_values, cumulative_max)
            ) if account_values else 0
        except Exception as e:
            print(f"⚠️  回撤计算错误: {str(e)}")
            max_drawdown = 0
        
        # 夏普比率 (假设每日交易)
        daily_returns = df['profit_rate'].values if len(df) > 0 else []
        if len(daily_returns) > 1:
            daily_std = np.std(daily_returns)
            sharpe_ratio = np.mean(daily_returns) / daily_std * np.sqrt(252) if daily_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 收益率
        total_return = (final_balance - self.account.initial_balance) / self.account.initial_balance if self.account.initial_balance > 0 else 0
        
        # 确保所有数值都是有效的（处理 NaN 和 Inf）
        def safe_float(val, default=0):
            try:
                if pd.isna(val) or np.isinf(val):
                    return default
                return float(val)
            except:
                return default
        
        metrics = {
            'total_trades': int(total_trades),
            'winning_trades': int(winning_trades),
            'losing_trades': int(losing_trades),
            'win_rate': safe_float(win_rate, 0),
            'total_profit': safe_float(total_profit, 0),
            'avg_profit': safe_float(avg_profit, 0),
            'max_profit_trade': safe_float(max_profit_trade, 0),
            'max_loss_trade': safe_float(max_loss_trade, 0),
            'avg_return': safe_float(avg_return, 0),
            'best_return': safe_float(best_return, 0),
            'worst_return': safe_float(worst_return, 0),
            'final_balance': safe_float(final_balance, self.account.initial_balance),
            'total_return': safe_float(total_return, 0),
            'max_drawdown': safe_float(max_drawdown, 0),
            'sharpe_ratio': safe_float(sharpe_ratio, 0),
            'account_values': account_values,
            'initial_balance': safe_float(self.account.initial_balance, 10000)
        }
        
        return metrics
    
    def print_report(self, metrics):
        """打印详细回测报告"""
        if not metrics:
            print("❌ 无回测数据")
            return
        
        try:
            print("\n" + "="*70)
            print("📊 虚拟回测最终报告".center(70))
            print("="*70)
            
            print(f"\n💼 账户指标:")
            print(f"   初始资金:        ¥{float(metrics.get('initial_balance', 10000)):>12.2f}")
            print(f"   最终资金:        ¥{float(metrics.get('final_balance', 10000)):>12.2f}")
            print(f"   总收益:          ¥{float(metrics.get('total_profit', 0)):>12.2f}")
            print(f"   收益率:          {float(metrics.get('total_return', 0)):>12.2%}")
            
            print(f"\n📈 交易指标:")
            print(f"   总交易数:        {int(metrics.get('total_trades', 0)):>12}")
            print(f"   获利笔数:        {int(metrics.get('winning_trades', 0)):>12}")
            print(f"   亏损笔数:        {int(metrics.get('losing_trades', 0)):>12}")
            print(f"   胜率:            {float(metrics.get('win_rate', 0)):>12.2%}")
            
            print(f"\n💰 盈亏指标:")
            print(f"   平均单笔利润:    ¥{float(metrics.get('avg_profit', 0)):>12.2f}")
            print(f"   最大单笔利润:    ¥{float(metrics.get('max_profit_trade', 0)):>12.2f}")
            print(f"   最大单笔亏损:    ¥{float(metrics.get('max_loss_trade', 0)):>12.2f}")
            
            print(f"\n📊 收益率指标:")
            print(f"   平均收益率:      {float(metrics.get('avg_return', 0)):>12.2%}")
            print(f"   最佳收益率:      {float(metrics.get('best_return', 0)):>12.2%}")
            print(f"   最差收益率:      {float(metrics.get('worst_return', 0)):>12.2%}")
            
            print(f"\n⚠️  风险指标:")
            print(f"   最大回撤:        {float(metrics.get('max_drawdown', 0)):>12.2%}")
            print(f"   夏普比率:        {float(metrics.get('sharpe_ratio', 0)):>12.2f}")
            
            print("\n" + "="*70)
        except Exception as e:
            print(f"⚠️  报告打印出错: {str(e)}")
            print("但回测数据已成功保存到数据库")
