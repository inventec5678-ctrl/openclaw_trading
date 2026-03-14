#!/usr/bin/env python3
"""
Louie 策略 - 滾動式回測 (優化參數版本)
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

# 優化後的參數
OPTIMIZED_PARAMS = {
    'score_threshold': 50,
    'stop_loss': 0.92,
    'take_profit': 1.12,
    'oos_length': 40,
    'is_length': 60,
}

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
    prev_row = df.iloc[i-1]
    
    # 檢查必要數據
    if pd.isna(row['RSI']) or pd.isna(row['MACD']) or pd.isna(row['K']):
        return None
    
    score = 0
    reasons = []
    
    # RSI (權重 20%)
    if 30 < row['RSI'] < 70:
        score += 10
    elif row['RSI'] < 30:
        score += 15
        reasons.append("RSI超賣")
    elif row['RSI'] > 70:
        score -= 10
        reasons.append("RSI超買")
    
    # MACD (權重 25%)
    if row['MACD'] > row['Signal']:
        score += 15
        if row['Histogram'] > 0:
            score += 10
            reasons.append("MACD黃金交叉")
    else:
        score -= 10
    
    # KDJ (權重 15%)
    if row['K'] > row['D']:
        score += 10
        if row['K'] < 20:
            score += 5
            reasons.append("KDJ超賣反彈")
    else:
        score -= 5
    
    # MA趨勢 (權重 20%)
    if row['Close'] > row['MA20']:
        score += 10
    if row['MA20'] > row['MA60']:
        score += 10
        reasons.append("MA多頭排列")
    
    # 成交量 (權重 10%)
    if row['Volume'] > row['Volume_MA20']:
        score += 10
    
    # 布林通道 (權重 10%)
    if row['Close'] < row['BB_Lower']:
        score += 10
        reasons.append("觸及布林下軌")
    
    return {
        'score': score,
        'reasons': reasons,
        'price': row['Close']
    }

def run_backtest():
    """運行滾動式回測 (使用優化參數)"""
    print("=" * 60)
    print("Louie 策略 - 滾動式回測 (優化參數)")
    print("=" * 60)
    
    # 使用優化後的參數
    score_threshold = OPTIMIZED_PARAMS['score_threshold']
    stop_loss = OPTIMIZED_PARAMS['stop_loss']
    take_profit = OPTIMIZED_PARAMS['take_profit']
    oos_length = OPTIMIZED_PARAMS['oos_length']
    is_length = OPTIMIZED_PARAMS['is_length']
    
    print(f"\n優化參數:")
    print(f"  Score Threshold: {score_threshold}")
    print(f"  Stop Loss: {stop_loss} ({(1-stop_loss)*100:.0f}%)")
    print(f"  Take Profit: {take_profit} ({(take_profit-1)*100:.0f}%)")
    print(f"  Hold Days: {oos_length}")
    
    # 獲取6個月的歷史數據（3個月IS + 3個月OOS）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"\n數據期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    all_results = []
    total_wins = 0
    total_losses = 0
    total_trades = 0
    
    for symbol in SYMBOLS:
        print(f"\n處理 {symbol}...")
        
        try:
            # 獲取數據
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty or len(df) < 60:
                print(f"  ⚠ 數據不足，跳過")
                continue
            
            df = calculate_indicators(df)
            
            symbol_wins = 0
            symbol_losses = 0
            
            # OOS期間的信號
            for i in range(is_length, len(df) - oos_length):
                signal = generate_signal(df, i)
                
                if signal and signal['score'] >= score_threshold:
                    # 買入信號
                    entry_price = signal['price']
                    
                    # 模擬持有到OOS結束
                    oos_end_idx = i + oos_length
                    if oos_end_idx < len(df):
                        # 檢查是否觸及止損或止盈
                        stop_price = entry_price * stop_loss
                        tp_price = entry_price * take_profit
                        
                        actual_exit = None
                        # 逐日檢查
                        for j in range(i, min(i + oos_length, len(df))):
                            high = df.iloc[j]['High']
                            low = df.iloc[j]['Low']
                            
                            if high >= tp_price:
                                actual_exit = tp_price
                                break
                            if low <= stop_price:
                                actual_exit = stop_price
                                break
                        
                        if actual_exit is None:
                            actual_exit = df.iloc[oos_end_idx]['Close']
                        
                        final_return = (actual_exit - entry_price) / entry_price
                        
                        is_win = final_return > 0
                        
                        if is_win:
                            symbol_wins += 1
                            total_wins += 1
                        else:
                            symbol_losses += 1
                            total_losses += 1
                        
                        total_trades += 1
            
            if symbol_wins + symbol_losses > 0:
                win_rate = symbol_wins / (symbol_wins + symbol_losses) * 100
                print(f"  ✅ 交易次數: {symbol_wins + symbol_losses}, 勝率: {win_rate:.2f}%")
                all_results.append({
                    'symbol': symbol,
                    'trades': symbol_wins + symbol_losses,
                    'wins': symbol_wins,
                    'losses': symbol_losses,
                    'win_rate': win_rate
                })
                
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
    
    # 匯總結果
    print("\n" + "=" * 60)
    print("回測結果匯總 (優化參數)")
    print("=" * 60)
    
    if total_trades > 0:
        overall_win_rate = total_wins / total_trades * 100
        print(f"\n總交易次數: {total_trades}")
        print(f"獲勝次數: {total_wins}")
        print(f"失敗次數: {total_losses}")
        print(f"\n🎯 真實勝率: {overall_win_rate:.2f}%")
        
        # 保存結果
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backtest_type": "滾動式回測 (優化參數)",
            "optimized_params": OPTIMIZED_PARAMS,
            "data_period": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            "total_trades": total_trades,
            "winning_trades": total_wins,
            "losing_trades": total_losses,
            "win_rate": round(overall_win_rate, 2),
            "stocks": all_results
        }
        
        with open("/Users/changrunlin/.openclaw/workspace/louie_backtest_result.json", "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n結果已保存至: louie_backtest_result.json")
        
    else:
        print("⚠ 沒有產生任何交易信號")

if __name__ == "__main__":
    run_backtest()
