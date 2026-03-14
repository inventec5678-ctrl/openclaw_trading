#!/usr/bin/env python3
"""
Louie 策略 - 30個 3個月滾動式回測
計算統計上有效的真實勝率
"""
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 股票列表
SYMBOLS = [
    "0050.TW", "2330.TW", "2317.TW", "2454.TW", "2603.TW",
    "2303.TW", "2379.TW", "2382.TW", "2409.TW", "2474.TW",
    "2316.TW", "2633.TW", "2881.TW", "2884.TW", "2885.TW",
    "2891.TW", "2912.TW", "3008.TW", "3034.TW", "2002.TW"
]

# 滾動回測參數
NUM_PERIODS = 30  # 30個滾動區間
MONTHS_PER_PERIOD = 3  # 每個區間3個月的OOS

def calculate_indicators(df):
    """計算技術指標"""
    df = df.copy()
    
    # MA
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Histogram'] = df['MACD'] - df['Signal']
    
    # KDJ
    low14 = df['Low'].rolling(14).min()
    high14 = df['High'].rolling(14).max()
    df['K'] = 100 * (df['Close'] - low14) / (high14 - low14)
    df['D'] = df['K'].rolling(3).mean()
    
    # 成交量均線
    df['Volume_MA20'] = df['Volume'].rolling(20).mean()
    
    # 布林通道
    df['BB_Middle'] = df['Close'].rolling(20).mean()
    df['BB_Std'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
    
    return df

def generate_signal(df, i):
    """根據信號邏輯生成交易信號"""
    if i < 60:
        return None
    
    row = df.iloc[i]
    
    # 檢查必要數據
    if pd.isna(row['RSI']) or pd.isna(row['MACD']) or pd.isna(row['K']):
        return None
    
    score = 0
    
    # RSI (權重 20%)
    if 30 < row['RSI'] < 70:
        score += 10
    elif row['RSI'] < 30:
        score += 15
    elif row['RSI'] > 70:
        score -= 10
    
    # MACD (權重 25%)
    if row['MACD'] > row['Signal']:
        score += 15
        if row['Histogram'] > 0:
            score += 10
    else:
        score -= 10
    
    # KDJ (權重 15%)
    if row['K'] > row['D']:
        score += 10
        if row['K'] < 20:
            score += 5
    else:
        score -= 5
    
    # MA趨勢 (權重 20%)
    if row['Close'] > row['MA20']:
        score += 10
    if row['MA20'] > row['MA60']:
        score += 10
    
    # 成交量 (權重 10%)
    if row['Volume'] > row['Volume_MA20']:
        score += 10
    
    # 布林通道 (權重 10%)
    if row['Close'] < row['BB_Lower']:
        score += 10
    
    return {
        'score': score,
        'price': row['Close']
    }

def run_rolling_backtest():
    """運行 30 個 3 個月滾動式回測"""
    print("=" * 70)
    print("Louie 策略 - 30個 3個月滾動式回測")
    print("計算統計上有效的真實勝率")
    print("=" * 70)
    
    # 結束日期
    end_date = datetime.now()
    
    # 每個滾動區間: 6個月數據 (3個月IS + 3個月OOS)
    # 30個區間需要往回大約 6*30 = 180 個月 = 15年
    days_per_window = 180  # 6個月
    days_shift = 90  # 每個區間往回移3個月
    
    start_date = end_date - timedelta(days=days_per_window + days_shift * (NUM_PERIODS - 1))
    
    print(f"\n數據期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"滾動區間數: {NUM_PERIODS}")
    print(f"每區間長度: {days_per_window} 天 (約 6 個月)")
    print(f"每區間移動: {days_shift} 天 (約 3 個月)")
    
    # 預先獲取所有股票的完整數據
    print("\n預先獲取股票數據...")
    stock_data = {}
    for symbol in SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            if df is not None and len(df) > 60:
                stock_data[symbol] = calculate_indicators(df)
                print(f"  ✓ {symbol}: {len(df)} 天數據")
            else:
                print(f"  ✗ {symbol}: 數據不足")
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")
    
    # 收集所有區間的結果
    all_period_results = []
    total_wins = 0
    total_losses = 0
    total_trades = 0
    
    # IS: 60天, OOS: 120天 (足夠的信號生成和持有期)
    is_length = 60
    oos_length = 90  # 3個月
    
    for period_idx in range(NUM_PERIODS):
        # 計算這個區間的時間範圍
        period_end_offset = days_shift * (NUM_PERIODS - 1 - period_idx)
        period_end = end_date - timedelta(days=period_end_offset)
        period_start = period_end - timedelta(days=days_per_window)
        
        # 轉換為日期索引
        period_start_str = period_start.strftime('%Y-%m-%d')
        period_end_str = period_end.strftime('%Y-%m-%d')
        
        print(f"\n--- 區間 {period_idx + 1}/{NUM_PERIODS}: {period_start_str} ~ {period_end_str} ---")
        
        period_wins = 0
        period_losses = 0
        period_trades = 0
        
        for symbol, df_full in stock_data.items():
            try:
                # 篩選這個區間的數據
                df = df_full[(df_full.index >= period_start_str) & (df_full.index < period_end_str)]
                
                if df is None or len(df) < is_length + 10:
                    continue
                
                # 在這個區間內的信號 (只在OOS部分)
                for i in range(is_length, len(df) - 10):
                    signal = generate_signal(df, i)
                    
                    if signal and signal['score'] >= 60:
                        entry_price = signal['price']
                        
                        # 持有約30天或到OOS結束
                        exit_idx = min(i + 30, len(df) - 1)
                        exit_price = df.iloc[exit_idx]['Close']
                        
                        # 止損止盈
                        stop_loss = entry_price * 0.92  # 8% 止損
                        take_profit = entry_price * 1.15  # 15% 止盈
                        
                        actual_exit = min(exit_price, take_profit)
                        actual_exit = max(actual_exit, stop_loss)
                        
                        final_return = (actual_exit - entry_price) / entry_price
                        
                        is_win = final_return > 0
                        
                        if is_win:
                            period_wins += 1
                            total_wins += 1
                        else:
                            period_losses += 1
                            total_losses += 1
                        
                        period_trades += 1
                        total_trades += 1
                        
            except Exception as e:
                continue
        
        if period_trades > 0:
            period_win_rate = period_wins / period_trades * 100
            print(f"  區間 {period_idx + 1}: 交易次數: {period_trades}, 勝率: {period_win_rate:.2f}%")
            all_period_results.append({
                'period': period_idx + 1,
                'start': period_start_str,
                'end': period_end_str,
                'trades': period_trades,
                'wins': period_wins,
                'losses': period_losses,
                'win_rate': round(period_win_rate, 2)
            })
        else:
            print(f"  區間 {period_idx + 1}: 無交易")
            all_period_results.append({
                'period': period_idx + 1,
                'start': period_start_str,
                'end': period_end_str,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0
            })
    
    # 匯總結果
    print("\n" + "=" * 70)
    print("回測結果匯總 (30個 3個月滾動區間)")
    print("=" * 70)
    
    if total_trades > 0:
        overall_win_rate = total_wins / total_trades * 100
        
        # 計算區間勝率的統計
        period_win_rates = [r['win_rate'] for r in all_period_results if r['trades'] > 0]
        
        if period_win_rates:
            mean_win_rate = np.mean(period_win_rates)
            std_win_rate = np.std(period_win_rates)
            median_win_rate = np.median(period_win_rates)
            min_win_rate = np.min(period_win_rates)
            max_win_rate = np.max(period_win_rates)
            
            # 95% 信賴區間
            ci_95 = 1.96 * std_win_rate / np.sqrt(len(period_win_rates))
        
        print(f"\n📊 總交易次數: {total_trades}")
        print(f"   獲勝次數: {total_wins}")
        print(f"   失敗次數: {total_losses}")
        
        print(f"\n🎯 整體真實勝率: {overall_win_rate:.2f}%")
        
        if period_win_rates:
            print(f"\n📈 區間勝率統計:")
            print(f"   平均值: {mean_win_rate:.2f}%")
            print(f"   中位數: {median_win_rate:.2f}%")
            print(f"   標準差: {std_win_rate:.2f}%")
            print(f"   最小值: {min_win_rate:.2f}%")
            print(f"   最大值: {max_win_rate:.2f}%")
            print(f"   95% 信賴區間: {mean_win_rate - ci_95:.2f}% ~ {mean_win_rate + ci_95:.2f}%")
        
        # 保存結果
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backtest_type": f"{NUM_PERIODS}個{MONTHS_PER_PERIOD}個月滾動式回測",
            "data_period": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            "total_trades": total_trades,
            "winning_trades": total_wins,
            "losing_trades": total_losses,
            "overall_win_rate": round(overall_win_rate, 2),
            "period_statistics": {
                "mean_win_rate": round(mean_win_rate, 2) if period_win_rates else 0,
                "median_win_rate": round(median_win_rate, 2) if period_win_rates else 0,
                "std_win_rate": round(std_win_rate, 2) if period_win_rates else 0,
                "min_win_rate": round(min_win_rate, 2) if period_win_rates else 0,
                "max_win_rate": round(max_win_rate, 2) if period_win_rates else 0,
                "ci_95_lower": round(mean_win_rate - ci_95, 2) if period_win_rates else 0,
                "ci_95_upper": round(mean_win_rate + ci_95, 2) if period_win_rates else 0,
            },
            "period_results": all_period_results
        }
        
        with open("/Users/changrunlin/.openclaw/workspace/louie_backtest_result.json", "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 結果已保存至: louie_backtest_result.json")
        
    else:
        print("⚠ 沒有產生任何交易信號")

if __name__ == "__main__":
    run_rolling_backtest()
