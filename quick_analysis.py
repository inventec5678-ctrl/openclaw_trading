#!/usr/bin/env python3
"""
快速分析 - 篩選勝率>70% 且 盈虧比>2 的股票
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# 股票列表 - 50檔
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

# 精簡策略參數
STRATEGY_PARAMS = {
    'score_threshold': [55, 60, 65],
    'stop_loss': [0.08, 0.10],
    'take_profit': [0.15, 0.20],
    'holding_days': [20, 30]
}

def calculate_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['RSI'] = df['Close'].diff().apply(lambda x: x if x > 0 else 0).rolling(14).mean()
    rsi_loss = df['Close'].diff().apply(lambda x: -x if x < 0 else 0).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + df['RSI'] / rsi_loss.replace(0, 0.001)))
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Histogram'] = df['MACD'] - df['Signal']
    
    low14 = df['Low'].rolling(14).min()
    high14 = df['High'].rolling(14).max()
    df['K'] = 100 * (df['Close'] - low14) / (high14 - low14)
    df['D'] = df['K'].rolling(3).mean()
    
    df['Volume_MA20'] = df['Volume'].rolling(20).mean()
    
    return df

def generate_signal(df, i):
    if i < 60:
        return None
    row = df.iloc[i]
    if pd.isna(row.get('RSI')) or pd.isna(row.get('MACD')) or pd.isna(row.get('K')):
        return None
    
    score = 0
    if 30 < row['RSI'] < 70:
        score += 10
    elif row['RSI'] < 30:
        score += 15
    
    if row['MACD'] > row['Signal']:
        score += 20
    if row['K'] > row['D']:
        score += 10
    if row['Close'] > row['MA20']:
        score += 10
    if row['Volume'] > row['Volume_MA20']:
        score += 10
    
    return {'score': score, 'price': row['Close']}

def run_backtest(df, params):
    wins = losses = 0
    win_returns = []
    loss_returns = []
    
    for i in range(60, len(df) - params['holding_days']):
        signal = generate_signal(df, i)
        if signal and signal['score'] >= params['score_threshold']:
            entry = signal['price']
            exit_idx = min(i + params['holding_days'], len(df) - 1)
            exit_price = df.iloc[exit_idx]['Close']
            
            sl = entry * (1 - params['stop_loss'])
            tp = entry * (1 + params['take_profit'])
            actual = min(exit_price, tp)
            actual = max(actual, sl)
            
            ret = (actual - entry) / entry * 100
            if ret > 0:
                wins += 1
                win_returns.append(ret)
            else:
                losses += 1
                loss_returns.append(ret)
    
    total = wins + losses
    if total < 10:
        return None
    
    win_rate = wins / total * 100
    avg_win = np.mean(win_returns) if win_returns else 0
    avg_loss = abs(np.mean(loss_returns)) if loss_returns else 0.001
    risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
    
    return {
        'wins': wins, 'losses': losses, 'total': total,
        'win_rate': win_rate, 'risk_reward': risk_reward,
        'avg_win': avg_win, 'avg_loss': avg_loss
    }

def analyze_stock(symbol, is_taiwan=True):
    try:
        if is_taiwan:
            csv_path = f"/Users/changrunlin/.openclaw/workspace/taiwan_stocks_data/{symbol.replace('.TW', '')}_TW.csv"
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date'])
        else:
            with open('/Users/changrunlin/.openclaw/workspace/stocks_data.json') as f:
                data = json.load(f)
            for s in data.get('us', []):
                if s['symbol'] == symbol:
                    df = pd.DataFrame(s['history'])
                    df['Date'] = pd.to_datetime(df['date'])
                    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                    break
            else:
                return None
        
        df = df.sort_values('Date').dropna(subset=['Close'])
        if len(df) < 120:
            return None
        
        df = calculate_indicators(df)
        
        best = None
        best_params = None
        for params in product(*STRATEGY_PARAMS.values()):
            p = dict(zip(STRATEGY_PARAMS.keys(), params))
            result = run_backtest(df, p)
            if result and result['total'] >= 10:
                score = result['win_rate'] * 0.5 + min(result['risk_reward'] * 30, 50) * 0.5
                if not best or score > best[0]:
                    best = (score, result, p)
        
        if best:
            return {'result': best[1], 'params': best[2]}
        return None
    except Exception as e:
        return None

def main():
    print("=" * 60)
    print("快速分析 - 篩選 勝率>70% 且 盈虧比>2 的股票")
    print("=" * 60)
    
    all_symbols = TAIWAN_SYMBOLS + US_SYMBOLS
    print(f"\n股票數量: {len(all_symbols)}")
    
    results = []
    qualified = []
    
    for i, symbol in enumerate(all_symbols):
        is_taiwan = symbol.endswith('.TW')
        print(f"[{i+1}/{len(all_symbols)}] {symbol}...", end=" ")
        
        data = analyze_stock(symbol, is_taiwan)
        if data:
            r = data['result']
            p = data['params']
            win_rate = r['win_rate']
            rr = r['risk_reward']
            print(f"勝率{win_rate:.1f}%, 盈虧比{rr:.2f}")
            
            stock = {
                'symbol': symbol,
                'wins': r['wins'], 'losses': r['losses'], 'total': r['total'],
                'win_rate': round(win_rate, 2), 'risk_reward': round(rr, 2),
                'avg_win': round(r['avg_win'], 2), 'avg_loss': round(r['avg_loss'], 2),
                'params': p
            }
            results.append(stock)
            if win_rate > 70 and rr > 2:
                qualified.append(stock)
                print(f"  🏆 符合!")
        else:
            print("⚠")
    
    print("\n" + "=" * 60)
    print(f"分析結果: {len(results)}/{len(all_symbols)} 檔")
    print(f"符合條件 (勝率>70% 且 盈虧比>2): {len(qualified)} 檔")
    print("=" * 60)
    
    if qualified:
        print("\n🏆 符合條件的股票:")
        for s in qualified:
            print(f"\n  📈 {s['symbol']}")
            print(f"     勝率: {s['win_rate']:.2f}%  盈虧比: {s['risk_reward']:.2f}")
            print(f"     平均盈利: {s['avg_win']:.2f}%  平均虧損: {s['avg_loss']:.2f}%")
            print(f"     交易次數: {s['total']} (賺{s['wins']}/賠{s['losses']})")
            print(f"     策略: score>={s['params']['score_threshold']}, SL={s['params']['stop_loss']*100:.0f}%, TP={s['params']['take_profit']*100:.0f}%, 持有{s['params']['holding_days']}天")
    else:
        print("\n⚠ 沒有找到符合條件的股票")
        
        # 顯示接近的
        near = [r for r in results if r['win_rate'] > 55 or r['risk_reward'] > 1.5]
        near.sort(key=lambda x: (x['win_rate'], x['risk_reward']), reverse=True)
        if near:
            print("\n📊 接近達標 (勝率>55% 或 盈虧比>1.5):")
            for s in near[:10]:
                print(f"  {s['symbol']}: 勝率 {s['win_rate']:.2f}%, 盈虧比 {s['risk_reward']:.2f}")
    
    # 保存結果
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(results),
        'qualified': len(qualified),
        'qualified_stocks': qualified,
        'all': results
    }
    with open('/Users/changrunlin/.openclaw/workspace/full_analysis_result.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n結果已保存")

if __name__ == "__main__":
    main()
