import pandas as pd
from datetime import datetime, timedelta
import os
import numpy as np

def refine_opportunities():
    file_path = "opportunities.csv"
    if not os.path.exists(file_path): 
        print(f"❌ 找不到文件: {file_path}")
        return

    try:
        # 1. 读取原始数据
        df = pd.read_csv(file_path)
        
        # --- 强化数据清洗：处理 'HALOSKINS' 等字符串干扰 ---
        # 强制转换核心列，无法转换的（如字符串 'HALOSKINS'）会变成 NaN
        numeric_cols = ['price', 'score2', 'hurst', 'er', 'changes']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 处理 slope 列：先转字符串，统一去掉 %，再转数字
        df['slope_val'] = pd.to_numeric(
            df['slope'].astype(str).str.replace('%', '', regex=False), 
            errors='coerce'
        ) / 100

        # 剔除任何含有 NaN 的行（这样就把包含 'HALOSKINS' 的脏数据彻底过滤了）
        initial_count = len(df)
        df = df.dropna(subset=['price', 'slope_val', 'score2'])
        clean_count = len(df)
        
        if initial_count > clean_count:
            print(f"🧹 已自动过滤 {initial_count - clean_count} 条脏数据 (包含非数字字符)")

        # 2. 时间处理
        def parse_smart_time(t_str):
            try:
                return pd.to_datetime(t_str)
            except:
                try:
                    t = pd.to_datetime(t_str).time()
                    return datetime.combine(datetime.now().date(), t)
                except:
                    return datetime.now() # 保底逻辑

        df['dt_object'] = df['time'].apply(parse_smart_time)
        latest_time = df['dt_object'].max()
        df_24h = df[df['dt_object'] >= (latest_time - timedelta(hours=24))].copy()

    except Exception as e:
        print(f"❌ 数据初始化失败: {e}")
        return

    # 3. 核心算法分析
    stats = []
    FEE_RATE = 0.05  # 平台手续费
    
    grouped = df_24h.groupby('name')

    for name, group in grouped:
        if any(kw in str(name) for kw in ["★", "Gloves", "Wraps"]): continue
        
        item_data = group.sort_values('dt_object')
        latest = item_data.iloc[-1]
        first_p = item_data['price'].iloc[0]
        last_p = latest['price']
        
        change_24h = ((last_p - first_p) / first_p) if first_p != 0 else 0
        real_margin = (latest['score2'] / 100) - FEE_RATE 
        v_eff = (abs(latest['slope_val']) / latest['changes']) if latest['changes'] > 0 else 0

        # 信号逻辑
        status = "观察中"
        win_rate = (latest['er'] * 35) + (latest['hurst'] * 45) + (real_margin * 100 * 2.5)

        if abs(latest['slope_val']) < 0.03 and latest['er'] > 0.80 and real_margin > 0.08:
            status = "💎 潜伏起涨"
            win_rate += 20
        elif 0.03 <= latest['slope_val'] < 0.12 and v_eff > 0.005 and latest['hurst'] > 0.45:
            status = "🚀 趋势确认"
            win_rate += 15
        elif latest['hurst'] < 0.35 or real_margin < 0.02:
            status = "🔥 避雷预警"
            win_rate -= 40

        stats.append({
            'name': name,
            'count': len(item_data),
            'last_price': last_p,
            'change': change_24h * 100,
            'real_profit': real_margin * 100,
            'hurst': latest['hurst'],
            'er': latest['er'],
            'win_rate': win_rate,
            'status': status
        })

    stats.sort(key=lambda x: x['win_rate'], reverse=True)

    # 4. 输出
    print("\n" + " CS2 量化精选报告 (已过滤异常数据) ".center(105, "="))
    print(f"{'饰品名称':<35} | {'频次':<4} | {'当前价':<8} | {'24H涨幅':<7} | {'实得净利':<7} | {'Hurst':<5} | {'ER':<4} | {'结论'}")
    print("-" * 115)

    for s in stats[:20]:
        print(f"{s['name'][:35]:<35} | {s['count']:^6} | {s['last_price']:>8.2f} | {s['change']:>+6.1f}% | {s['real_profit']:>7.1f}% | {s['hurst']:>5.2f} | {s['er']:>4.2f} | {s['status']}")
    
    print("=" * 105)

if __name__ == "__main__":
    refine_opportunities()