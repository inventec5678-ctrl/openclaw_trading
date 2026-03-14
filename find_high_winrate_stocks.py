#!/usr/bin/env python3
"""
多策略優化分析
對每檔股票嘗試多種策略參數組合，找出最佳策略
篩選 出勝率 >70% 的股票
"""
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# 股票列表
SYMBOLS = [
    "0050.TW", "2330.TW", "2317.TW", "2454.TW", "2603.TW",
    "2303.TW", "2379.TW", "2382.TW", "2409.TW", "2474.TW",
    "2316.TW", "2633.TW", "2881.TW", "2884.TW", "2885.TW",
    "2891.TW", "2912.TW", "3008.TW", "3034.TW", "2002.TW"
]

# 策略參數組合 (精簡版)
STRATEGY_PARAMS = {
    'score_threshold': [55, 60, 65],
    'stop_loss': [0.08, 0.10],
    'take_profit': [0.15, 0.20],
    'holding_days': [20, 30]
}

def calculate_indicators(df):
    """計算技術指標"""
    df = df.copy()
    
    # MA
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    
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
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    # 成交量均線
    df['Volume_MA20'] = df['Volume'].rolling(20).mean()
    
    # 布林通道
    df['BB_Middle'] = df['Close'].rolling(20).mean()
    df['BB_Std'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
    
    # ATR
    df['TR'] = np.maximum(
        df['High'] - df['Low'],
        np.maximum(
            abs(df['High'] - df['Close'].shift(1)),
            abs(df['Low'] - df['Close'].shift(1))
        )
    )
    df['ATR'] = df['TR'].rolling(14).mean()
    
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
            reasons.append("KDJ超賣")
    else:
        score -= 5
    
    # MA趨勢 (權重 20%)
    if row['Close'] > row['MA20']:
        score += 10
    if row['MA20'] > row['MA60']:
        score += 10
        reasons.append("MA多頭")
    
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

def run_backtest_for_params(df, params):
    """針對特定策略參數運行回測"""
    score_threshold = params['score_threshold']
    stop_loss = params['stop_loss']
    take_profit = params['take_profit']
    holding_days = params['holding_days']
    
    wins = 0
    losses = 0
    
    # IS: 60天, 之後是 OOS
    is_length = 60
    
    for i in range(is_length, len(df) - holding_days):
        signal = generate_signal(df, i)
        
        if signal and signal['score'] >= score_threshold:
            entry_price = signal['price']
            
            # 持有指定天數
            exit_idx = min(i + holding_days, len(df) - 1)
            exit_price = df.iloc[exit_idx]['Close']
            
            # 止損止盈
            sl = entry_price * (1 - stop_loss)
            tp = entry_price * (1 + take_profit)
            
            actual_exit = min(exit_price, tp)
            actual_exit = max(actual_exit, sl)
            
            final_return = (actual_exit - entry_price) / entry_price
            
            if final_return > 0:
                wins += 1
            else:
                losses += 1
    
    total = wins + losses
    if total == 0:
        return None
    
    win_rate = wins / total * 100
    
    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'win_rate': win_rate
    }

def find_best_strategy_for_stock(df):
    """找出單一股票的最佳策略"""
    best_result = None
    best_params = None
    best_win_rate = 0
    
    # 生成所有參數組合
    param_combinations = list(product(
        STRATEGY_PARAMS['score_threshold'],
        STRATEGY_PARAMS['stop_loss'],
        STRATEGY_PARAMS['take_profit'],
        STRATEGY_PARAMS['holding_days']
    ))
    
    for threshold, sl, tp, holding in param_combinations:
        params = {
            'score_threshold': threshold,
            'stop_loss': sl,
            'take_profit': tp,
            'holding_days': holding
        }
        
        result = run_backtest_for_params(df, params)
        
        if result and result['total'] >= 5:  # 至少有5筆交易
            if result['win_rate'] > best_win_rate:
                best_win_rate = result['win_rate']
                best_result = result
                best_params = params
    
    return best_params, best_result

def main():
    print("=" * 70)
    print("多策略優化分析")
    print("找出每檔股票使用最佳策略後，勝率 >70% 的股票")
    print("=" * 70)
    
    # 獲取歷史數據
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 5)  # 5年數據
    
    print(f"\n數據期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"股票數量: {len(SYMBOLS)}")
    print(f"策略參數組合數: {len(list(product(*STRATEGY_PARAMS.values())))}")
    
    results = []
    high_win_rate_stocks = []
    
    for symbol in SYMBOLS:
        print(f"\n處理 {symbol}...")
        
        try:
            # 獲取數據
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty or len(df) < 120:
                print(f"  ⚠ 數據不足，跳過")
                continue
            
            df = calculate_indicators(df)
            
            # 找最佳策略
            best_params, best_result = find_best_strategy_for_stock(df)
            
            if best_result and best_params:
                print(f"  ✅ 最佳策略: score>={best_params['score_threshold']}, ")
                print(f"     SL={best_params['stop_loss']*100}%, TP={best_params['take_profit']*100}%, ")
                print(f"     持有={best_params['holding_days']}天")
                print(f"     交易次數: {best_result['total']}, 勝率: {best_result['win_rate']:.2f}%")
                
                stock_result = {
                    'symbol': symbol,
                    'best_params': best_params,
                    'wins': best_result['wins'],
                    'losses': best_result['losses'],
                    'total_trades': best_result['total'],
                    'win_rate': round(best_result['win_rate'], 2)
                }
                
                results.append(stock_result)
                
                # 檢查是否 >70%
                if best_result['win_rate'] > 70:
                    high_win_rate_stocks.append(stock_result)
                    print(f"  🏆 勝率 >70%!")
            else:
                print(f"  ⚠ 無足夠交易數據")
                
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
    
    # 輸出結果
    print("\n" + "=" * 70)
    print("結果匯總")
    print("=" * 70)
    
    print(f"\n總共分析了 {len(results)} 檔股票")
    print(f"勝率 >70% 的股票數量: {len(high_win_rate_stocks)}")
    
    if high_win_rate_stocks:
        print("\n🏆 勝率 >70% 的股票:")
        for stock in high_win_rate_stocks:
            print(f"  {stock['symbol']}: 勝率 {stock['win_rate']:.2f}% ({stock['wins']}/{stock['total_trades']})")
            print(f"    策略: score>={stock['best_params']['score_threshold']}, "
                  f"SL={stock['best_params']['stop_loss']*100}%, "
                  f"TP={stock['best_params']['take_profit']*100}%, "
                  f"持有{stock['best_params']['holding_days']}天")
    else:
        print("\n⚠ 沒有股票勝率 >70%")
    
    # 保存結果
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_stocks_analyzed': len(results),
        'stocks_above_70': len(high_win_rate_stocks),
        'high_win_rate_stocks': high_win_rate_stocks,
        'all_results': results
    }
    
    with open('/Users/changrunlin/.openclaw/workspace/stock_best_strategy.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n結果已保存至: stock_best_strategy.json")
    
    return output

if __name__ == "__main__":
    main()
