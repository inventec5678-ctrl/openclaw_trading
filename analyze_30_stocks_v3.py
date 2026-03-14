#!/usr/bin/env python3
"""
多策略優化分析 v3 - 擴展參數範圍
對每檔股票嘗試更多策略參數組合，找出最佳策略
篩選 出勝率 >70% 且 平均盈利 >5% 的股票
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# 股票列表 - 30檔
SYMBOLS = [
    "0050.TW", "2002.TW", "2105.TW", "2303.TW", "2316.TW",
    "2317.TW", "2330.TW", "2379.TW", "2382.TW", "2409.TW",
    "2454.TW", "2458.TW", "2474.TW", "2542.TW", "2603.TW",
    "2633.TW", "2881.TW", "2882.TW", "2884.TW", "2885.TW",
    "2891.TW", "2892.TW", "2912.TW", "3008.TW", "3034.TW",
    "3711.TW", "4938.TW", "5269.TW", "5871.TW", "6415.TW"
]

# 擴展策略參數組合
STRATEGY_PARAMS = {
    'score_threshold': [50, 55, 60, 65],
    'stop_loss': [0.05, 0.08, 0.10, 0.12],
    'take_profit': [0.10, 0.15, 0.20, 0.25, 0.30],
    'holding_days': [10, 20, 30, 40, 50]
}

def calculate_indicators(df):
    """計算技術指標"""
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
    total_returns = []
    
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
            total_returns.append(ret)
            
            if ret > 0:
                wins += 1
            else:
                losses += 1
    
    total = wins + losses
    if total == 0:
        return None
    
    win_rate = wins / total * 100
    avg_return = np.mean(total_returns) if total_returns else 0
    
    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'win_rate': win_rate,
        'avg_return': avg_return
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
            # 优先满足两个条件
            if result['win_rate'] > 70 and result['avg_return'] > 5:
                score = 1000 + result['win_rate'] + result['avg_return']  # 优先选
            else:
                score = result['win_rate'] * 0.5 + min(result['avg_return'] * 10, 50) * 0.5
            
            if score > best_score:
                best_score = score
                best_result = result
                best_params = params
    
    return best_params, best_result

def main():
    print("=" * 70)
    print("多策略優化分析 v3 - 擴展參數範圍")
    print("找出每檔股票使用最佳策略後，勝率 >70% 且 平均盈利 >5% 的股票")
    print("=" * 70)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 5)
    
    print(f"\n數據期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"股票數量: {len(SYMBOLS)}")
    print(f"策略參數組合數: {len(list(product(*STRATEGY_PARAMS.values())))}")
    
    results = []
    qualified_stocks = []
    
    for symbol in SYMBOLS:
        print(f"\n處理 {symbol}...", end=" ")
        
        try:
            csv_path = f"/Users/changrunlin/.openclaw/workspace/taiwan_stocks_data/{symbol.replace('.TW', '')}_TW.csv"
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            
            if len(df) < 120:
                print(f"⚠ 數據不足")
                continue
            
            df = calculate_indicators(df)
            best_params, best_result = find_best_strategy_for_stock(df)
            
            if best_result and best_params:
                print(f"勝率: {best_result['win_rate']:.2f}%, 平均盈利: {best_result['avg_return']:.2f}%")
                
                stock_result = {
                    'symbol': symbol,
                    'best_params': best_params,
                    'wins': best_result['wins'],
                    'losses': best_result['losses'],
                    'total_trades': best_result['total'],
                    'win_rate': round(best_result['win_rate'], 2),
                    'avg_return': round(best_result['avg_return'], 2)
                }
                
                results.append(stock_result)
                
                if best_result['win_rate'] > 70 and best_result['avg_return'] > 5:
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
    print(f"勝率 >70% 且 盈利 >5% 的股票數量: {len(qualified_stocks)}")
    
    if qualified_stocks:
        print("\n🏆 符合條件的股票 (勝率>70% 且 盈利>5%):")
        for stock in qualified_stocks:
            print(f"  {stock['symbol']}: 勝率 {stock['win_rate']:.2f}%, 平均盈利 {stock['avg_return']:.2f}%")
            print(f"    策略: score>={stock['best_params']['score_threshold']}, "
                  f"SL={stock['best_params']['stop_loss']*100}%, "
                  f"TP={stock['best_params']['take_profit']*100}%, "
                  f"持有{stock['best_params']['holding_days']}天")
    
    # 顯示接近達標的股票
    near_qualified = [r for r in results if r['win_rate'] > 60 or r['avg_return'] > 3]
    near_qualified.sort(key=lambda x: (x['win_rate'], x['avg_return']), reverse=True)
    
    if not qualified_stocks and near_qualified:
        print("\n📊 接近達標的股票 (勝率>60% 或 盈利>3%):")
        for stock in near_qualified[:10]:
            print(f"  {stock['symbol']}: 勝率 {stock['win_rate']:.2f}%, 平均盈利 {stock['avg_return']:.2f}%")
    
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_stocks_analyzed': len(results),
        'qualified_stocks_count': len(qualified_stocks),
        'qualified_stocks': qualified_stocks,
        'all_results': results
    }
    
    with open('/Users/changrunlin/.openclaw/workspace/stock_analysis_result.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n結果已保存至: stock_analysis_result.json")

if __name__ == "__main__":
    main()
