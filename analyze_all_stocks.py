#!/usr/bin/env python3
"""
Louie 策略 - 全股票分析 (使用 yfinance 獲取完整數據)
找出勝率 > 70% 且盈虧比 > 2 的股票
"""
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 股票列表 - 從 stocks_data.json 讀取
with open('/Users/changrunlin/.openclaw/workspace/stocks_data.json', 'r') as f:
    stocks_data = json.load(f)

taiwan_stocks = stocks_data['taiwan']
SYMBOLS = [s['symbol'] for s in taiwan_stocks]
print(f"加載了 {len(SYMBOLS)} 檔台灣股票")

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

def analyze_stock(symbol, name):
    """分析單一股票"""
    # 獲取2年歷史數據
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2年
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df is None or len(df) < 120:
            return None
        
        # 計算指標
        df = calculate_indicators(df)
        
        # 回測參數
        is_length = 60
        oos_length = 30
        
        wins = 0
        losses = 0
        total_profit = 0
        total_loss = 0
        
        # OOS期間的信號
        for i in range(is_length, len(df) - oos_length):
            signal = generate_signal(df, i)
            
            if signal and signal['score'] >= 60:
                entry_price = signal['price']
                
                # 持有30天或到數據結束
                exit_idx = min(i + oos_length, len(df) - 1)
                exit_price = df.iloc[exit_idx]['Close']
                
                # 止損止盈
                stop_loss = entry_price * 0.92  # 8% 止損
                take_profit = entry_price * 1.15  # 15% 止盈
                
                actual_exit = min(exit_price, take_profit)
                actual_exit = max(actual_exit, stop_loss)
                
                returns = (actual_exit - entry_price) / entry_price
                
                if returns > 0:
                    wins += 1
                    total_profit += returns
                else:
                    losses += 1
                    total_loss += abs(returns)
        
        total_trades = wins + losses
        
        if total_trades < 5:  # 至少5筆交易
            return None
        
        win_rate = wins / total_trades * 100
        
        # 計算盈虧比
        avg_profit = total_profit / wins if wins > 0 else 0
        avg_loss = total_loss / losses if losses > 0 else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        
        return {
            'symbol': symbol,
            'name': name,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_profit': avg_profit * 100,
            'avg_loss': avg_loss * 100,
            'profit_loss_ratio': profit_loss_ratio
        }
        
    except Exception as e:
        print(f"  Error: {e}")
        return None

# 分析所有股票
print("\n" + "=" * 70)
print("開始分析所有股票 (使用 yfinance 數據)...")
print("=" * 70)

results = []
for i, stock in enumerate(taiwan_stocks):
    symbol = stock['symbol']
    name = stock['name']
    
    print(f"[{i+1}/{len(taiwan_stocks)}] {symbol} {name}...", end=" ")
    
    result = analyze_stock(symbol, name)
    if result:
        print(f"交易:{result['total_trades']}, 勝率:{result['win_rate']:.1f}%, P/L比:{result['profit_loss_ratio']:.2f}")
        results.append(result)
    else:
        print("數據不足")

# 按股票統計結果
print("\n" + "=" * 70)
print("分析結果匯總")
print("=" * 70)

print(f"\n總共分析了 {len(taiwan_stocks)} 檔股票")
print(f"有足夠交易數據的股票: {len(results)} 檔")

# 找出符合條件的股票
qualified = [r for r in results if r['win_rate'] > 70 and r['profit_loss_ratio'] > 2]

print(f"\n🎯 符合條件 (勝率 > 70% 且 盈虧比 > 2) 的股票: {len(qualified)} 檔")

if qualified:
    # 按勝率排序
    qualified.sort(key=lambda x: x['win_rate'], reverse=True)
    print("\n" + "=" * 70)
    print("符合條件的股票列表:")
    print("=" * 70)
    for r in qualified:
        print(f"\n  {r['symbol']} {r['name']}")
        print(f"    交易次數: {r['total_trades']}")
        print(f"    勝率: {r['win_rate']:.2f}%")
        print(f"    平均盈利: {r['avg_profit']:.2f}%")
        print(f"    平均虧損: {r['avg_loss']:.2f}%")
        print(f"    盈虧比: {r['profit_loss_ratio']:.2f}")
else:
    print("\n⚠ 沒有找到符合條件的股票")

# 找出高勝率的股票
high_win_rate = [r for r in results if r['win_rate'] > 60]
high_win_rate.sort(key=lambda x: x['win_rate'], reverse=True)

print("\n" + "=" * 70)
print(f"高勝率股票 (勝率 > 60%): {len(high_win_rate)} 檔")
print("=" * 70)
for r in high_win_rate[:15]:
    print(f"  {r['symbol']} {r['name']}: 勝率 {r['win_rate']:.1f}%, 盈虧比 {r['profit_loss_ratio']:.2f}, 交易 {r['total_trades']}次")

# 找出高盈虧比的股票
high_pl = [r for r in results if r['profit_loss_ratio'] > 1.5]
high_pl.sort(key=lambda x: x['profit_loss_ratio'], reverse=True)

print("\n" + "=" * 70)
print(f"高盈虧比股票 (盈虧比 > 1.5): {len(high_pl)} 檔")
print("=" * 70)
for r in high_pl[:15]:
    print(f"  {r['symbol']} {r['name']}: 盈虧比 {r['profit_loss_ratio']:.2f}, 勝率 {r['win_rate']:.1f}%, 交易 {r['total_trades']}次")

# 保存結果
output = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_stocks_analyzed": len(taiwan_stocks),
    "stocks_with_enough_data": len(results),
    "qualified_stocks_count": len(qualified),
    "qualified_stocks": qualified,
    "high_win_rate_stocks": high_win_rate[:20],
    "high_profit_loss_ratio_stocks": high_pl[:20],
    "all_results": results
}

with open('/Users/changrunlin/.openclaw/workspace/stock_winrate_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n結果已保存至: stock_winrate_analysis.json")
