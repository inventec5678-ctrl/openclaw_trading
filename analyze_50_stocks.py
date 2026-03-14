#!/usr/bin/env python3
"""
全面分析 - 篩選勝率>70% 且 盈虧比>2 的股票
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product
import os
import warnings
warnings.filterwarnings('ignore')

# 股票列表 - 50檔 (30台 + 20美)
TAIWAN_SYMBOLS = [
    "0050.TW", "2002.TW", "2105.TW", "2303.TW", "2316.TW",
    "2317.TW", "2330.TW", "2379.TW", "2382.TW", "2409.TW",
    "2454.TW", "2458.TW", "2474.TW", "2542.TW", "2603.TW",
    "2633.TW", "2881.TW", "2882.TW", "2884.TW", "2885.TW",
    "2891.TW", "2892.TW", "2912.TW", "3008.TW", "3034.TW",
    "3711.TW", "4938.TW", "5269.TW", "5871.TW", "6415.TW"
]

US_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", 
    "INTC", "NFLX", "JPM", "V", "JNJ", "WMT", "PG", "MA", "HD", "KO", "PEP", "DIS"
]

# 策略參數
STRATEGY_PARAMS = {
    'score_threshold': [50, 55, 60, 65],
    'stop_loss': [0.05, 0.08, 0.10, 0.12],
    'take_profit': [0.10, 0.15, 0.20, 0.25, 0.30],
    'holding_days': [10, 20, 30, 40, 50]
}

def calculate_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Histogram'] = df['MACD'] - df['Signal']
    
    low14 = df['Low'].rolling(14).min()
    high14 = df['High'].rolling(14).max()
    df['K'] = 100 * (df['Close'] - low14) / (high14 - low14)
    df['D'] = df['K'].rolling(3).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    df['Volume_MA20'] = df['Volume'].rolling(20).mean()
    
    df['BB_Middle'] = df['Close'].rolling(20).mean()
    df['BB_Std'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
    
    return df

def generate_signal(df, i):
    if i < 60:
        return None
    
    row = df.iloc[i]
    if pd.isna(row['RSI']) or pd.isna(row['MACD']) or pd.isna(row['K']):
        return None
    
    score = 0
    if 30 < row['RSI'] < 70:
        score += 10
    elif row['RSI'] < 30:
        score += 15
    elif row['RSI'] > 70:
        score -= 10
    
    if row['MACD'] > row['Signal']:
        score += 15
        if row['Histogram'] > 0:
            score += 10
    else:
        score -= 10
    
    if row['K'] > row['D']:
        score += 10
        if row['K'] < 20:
            score += 5
    else:
        score -= 5
    
    if row['Close'] > row['MA20']:
        score += 10
    if row['MA20'] > row['MA60']:
        score += 10
    
    if row['Volume'] > row['Volume_MA20']:
        score += 10
    
    if row['Close'] < row['BB_Lower']:
        score += 10
    
    return {'score': score, 'price': row['Close']}

def run_backtest_for_params(df, params):
    score_threshold = params['score_threshold']
    stop_loss = params['stop_loss']
    take_profit = params['take_profit']
    holding_days = params['holding_days']
    
    wins = 0
    losses = 0
    win_returns = []
    loss_returns = []
    
    is_length = 60
    
    for i in range(is_length, len(df) - holding_days):
        signal = generate_signal(df, i)
        
        if signal and signal['score'] >= score_threshold:
            entry_price = signal['price']
            exit_idx = min(i + holding_days, len(df) - 1)
            exit_price = df.iloc[exit_idx]['Close']
            
            sl = entry_price * (1 - stop_loss)
            tp = entry_price * (1 + take_profit)
            
            actual_exit = min(exit_price, tp)
            actual_exit = max(actual_exit, sl)
            
            ret = (actual_exit - entry_price) / entry_price * 100
            
            if ret > 0:
                wins += 1
                win_returns.append(ret)
            else:
                losses += 1
                loss_returns.append(ret)
    
    total = wins + losses
    if total == 0:
        return None
    
    win_rate = wins / total * 100
    avg_return = np.mean(win_returns + loss_returns) if (win_returns + loss_returns) else 0
    
    # 計算盈虧比 (平均盈利 / 平均虧損)
    avg_win = np.mean(win_returns) if win_returns else 0
    avg_loss = abs(np.mean(loss_returns)) if loss_returns else 0.001
    risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
    
    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'risk_reward': risk_reward
    }

def find_best_strategy_for_stock(df):
    best_result = None
    best_params = None
    best_score = 0
    
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
        
        if result and result['total'] >= 10:
            # 優先滿足兩個條件: 勝率>70% 且 盈虧比>2
            if result['win_rate'] > 70 and result['risk_reward'] > 2:
                score = 2000 + result['win_rate'] + result['risk_reward'] * 10
            else:
                score = result['win_rate'] * 0.5 + min(result['risk_reward'] * 20, 50) * 0.5
            
            if score > best_score:
                best_score = score
                best_result = result
                best_params = params
    
    return best_params, best_result

def load_taiwan_stock(symbol):
    csv_path = f"/Users/changrunlin/.openclaw/workspace/taiwan_stocks_data/{symbol.replace('.TW', '')}_TW.csv"
    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    return df

def load_us_stock(symbol):
    with open('/Users/changrunlin/.openclaw/workspace/stocks_data.json', 'r') as f:
        data = json.load(f)
    
    for stock in data.get('us', []):
        if stock['symbol'] == symbol:
            history = stock.get('history', [])
            if not history:
                return None
            df = pd.DataFrame(history)
            df['Date'] = pd.to_datetime(df['date'])
            df = df.rename(columns={
                'open': 'Open', 'high': 'High', 'low': 'Low', 
                'close': 'Close', 'volume': 'Volume'
            })
            df = df.sort_values('Date')
            return df
    return None

def main():
    print("=" * 70)
    print("全面分析 - 篩選 勝率>70% 且 盈虧比>2 的股票")
    print("=" * 70)
    
    all_symbols = TAIWAN_SYMBOLS + US_SYMBOLS
    print(f"\n股票數量: {len(all_symbols)} (台股 {len(TAIWAN_SYMBOLS)} + 美股 {len(US_SYMBOLS)})")
    
    results = []
    qualified_stocks = []
    
    for symbol in all_symbols:
        print(f"\n處理 {symbol}...", end=" ")
        
        try:
            if symbol.endswith('.TW'):
                df = load_taiwan_stock(symbol)
            else:
                df = load_us_stock(symbol)
            
            if df is None or len(df) < 120:
                print(f"⚠ 數據不足")
                continue
            
            df = calculate_indicators(df)
            best_params, best_result = find_best_strategy_for_stock(df)
            
            if best_result and best_params:
                print(f"勝率: {best_result['win_rate']:.2f}%, 盈虧比: {best_result['risk_reward']:.2f}")
                
                stock_result = {
                    'symbol': symbol,
                    'best_params': best_params,
                    'wins': best_result['wins'],
                    'losses': best_result['losses'],
                    'total_trades': best_result['total'],
                    'win_rate': round(best_result['win_rate'], 2),
                    'avg_return': round(best_result['avg_return'], 2),
                    'avg_win': round(best_result['avg_win'], 2),
                    'avg_loss': round(best_result['avg_loss'], 2),
                    'risk_reward': round(best_result['risk_reward'], 2)
                }
                
                results.append(stock_result)
                
                if best_result['win_rate'] > 70 and best_result['risk_reward'] > 2:
                    qualified_stocks.append(stock_result)
                    print(f"  🏆 符合條件!")
            else:
                print(f"⚠ 無足夠交易數據")
                
        except Exception as e:
            print(f"❌ 錯誤: {e}")
    
    print("\n" + "=" * 70)
    print("結果匯總")
    print("=" * 70)
    
    print(f"\n總共分析了 {len(results)} 檔股票")
    print(f"符合條件 (勝率>70% 且 盈虧比>2): {len(qualified_stocks)} 檔")
    
    if qualified_stocks:
        print("\n🏆 符合條件的股票:")
        for stock in qualified_stocks:
            print(f"  📈 {stock['symbol']}")
            print(f"     勝率: {stock['win_rate']:.2f}%, 盈虧比: {stock['risk_reward']:.2f}")
            print(f"     平均盈利: {stock['avg_win']:.2f}%, 平均虧損: {stock['avg_loss']:.2f}%")
            print(f"     交易次數: {stock['total_trades']} (賺{stock['wins']} / 賠{stock['losses']})")
            print(f"     策略: score>={stock['best_params']['score_threshold']}, "
                  f"SL={stock['best_params']['stop_loss']*100:.0f}%, "
                  f"TP={stock['best_params']['take_profit']*100:.0f}%, "
                  f"持有{stock['best_params']['holding_days']}天")
            print()
    else:
        print("\n⚠ 沒有找到符合條件的股票")
    
    # 顯示接近達標的股票
    near_qualified = [r for r in results if r['win_rate'] > 60 or r['risk_reward'] > 1.5]
    near_qualified.sort(key=lambda x: (x['win_rate'], x['risk_reward']), reverse=True)
    
    if not qualified_stocks and near_qualified:
        print("\n📊 接近達標的股票 (勝率>60% 或 盈虧比>1.5):")
        for stock in near_qualified[:10]:
            print(f"  {stock['symbol']}: 勝率 {stock['win_rate']:.2f}%, 盈虧比 {stock['risk_reward']:.2f}")
    
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_stocks_analyzed': len(results),
        'qualified_stocks_count': len(qualified_stocks),
        'qualified_stocks': qualified_stocks,
        'all_results': results
    }
    
    with open('/Users/changrunlin/.openclaw/workspace/full_stock_analysis.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n結果已保存至: full_stock_analysis.json")
    
    return qualified_stocks

if __name__ == "__main__":
    main()
