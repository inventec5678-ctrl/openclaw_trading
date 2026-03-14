#!/usr/bin/env python3
"""
Louie 策略 - 參數優化
測試多組參數找出最佳組合
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

def calculate_indicators(df):
    """計算技術指標"""
    df = df.copy()
    
    # MA
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    
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
    df['Volume_MA5'] = df['Volume'].rolling(5).mean()
    
    # 布林通道
    df['BB_Middle'] = df['Close'].rolling(20).mean()
    df['BB_Std'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    df['ATR_Pct'] = df['ATR'] / df['Close'] * 100
    
    return df

def generate_signal(df, i, params):
    """根據參數生成交易信號"""
    if i < 60:
        return None
    
    row = df.iloc[i]
    prev_row = df.iloc[i-1] if i > 0 else row
    
    # 檢查必要數據
    if pd.isna(row['RSI']) or pd.isna(row['MACD']) or pd.isna(row['K']):
        return None
    
    score = 0
    reasons = []
    
    rsi_oversold = params['rsi_oversold']
    rsi_overbought = params['rsi_overbought']
    
    # RSI (權重可調)
    rsi_weight = params.get('rsi_weight', 20)
    if rsi_oversold < row['RSI'] < rsi_overbought:
        score += rsi_weight * 0.5
    elif row['RSI'] < rsi_oversold:
        score += rsi_weight
        reasons.append("RSI超賣")
    elif row['RSI'] > rsi_overbought:
        score -= rsi_weight * 0.5
        reasons.append("RSI超買")
    
    # MACD (權重可調)
    macd_weight = params.get('macd_weight', 25)
    if row['MACD'] > row['Signal']:
        score += macd_weight
        if row['Histogram'] > 0:
            score += macd_weight * 0.3
            reasons.append("MACD黃金交叉")
    else:
        score -= macd_weight * 0.5
    
    # KDJ (權重可調)
    kdj_weight = params.get('kdj_weight', 15)
    if row['K'] > row['D']:
        score += kdj_weight
        if row['K'] < 20:
            score += kdj_weight * 0.3
            reasons.append("KDJ超賣反彈")
        if row['J'] < 0:
            score += kdj_weight * 0.2
            reasons.append("KDJ J值超賣")
    else:
        score -= kdj_weight * 0.3
    
    # MA趨勢 (權重可調)
    ma_weight = params.get('ma_weight', 20)
    if row['Close'] > row['MA20']:
        score += ma_weight * 0.5
    if row['MA20'] > row['MA60']:
        score += ma_weight
        reasons.append("MA多頭排列")
    
    # 成交量 (權重可調)
    vol_weight = params.get('vol_weight', 10)
    if row['Volume'] > row['Volume_MA20']:
        score += vol_weight
    
    # 布林通道 (權重可調)
    bb_weight = params.get('bb_weight', 10)
    if row['Close'] < row['BB_Lower']:
        score += bb_weight
        reasons.append("觸及布林下軌")
    elif row['BB_Position'] < 0.1:
        score += bb_weight * 0.5
    
    # ATR 波動率過濾
    if params.get('use_atr_filter', False):
        if row['ATR_Pct'] > params.get('min_atr', 2):
            score += 5
    
    return {
        'score': score,
        'reasons': reasons,
        'price': row['Close']
    }

def run_backtest_single_params(df, params):
    """針對單組參數運行回測"""
    is_length = params.get('is_length', 60)
    oos_length = params.get('oos_length', 30)
    score_threshold = params.get('score_threshold', 60)
    stop_loss = params.get('stop_loss', 0.08)
    take_profit = params.get('take_profit', 0.15)
    
    wins = 0
    losses = 0
    trades = []
    
    for i in range(is_length, len(df) - oos_length):
        signal = generate_signal(df, i, params)
        
        if signal and signal['score'] >= score_threshold:
            entry_price = signal['price']
            
            oos_end_idx = i + oos_length
            if oos_end_idx < len(df):
                exit_price = df.iloc[oos_end_idx]['Close']
                
                # 止損止盈
                stop_price = entry_price * (1 - stop_loss)
                tp_price = entry_price * (1 + take_profit)
                
                actual_exit = exit_price
                # 檢查是否觸及止損或止盈
                for j in range(i, min(i + oos_length, len(df))):
                    high = df.iloc[j]['High']
                    low = df.iloc[j]['Low']
                    if high >= tp_price:
                        actual_exit = tp_price
                        break
                    if low <= stop_price:
                        actual_exit = stop_price
                        break
                
                returns = (actual_exit - entry_price) / entry_price
                
                is_win = returns > 0
                
                if is_win:
                    wins += 1
                else:
                    losses += 1
                
                trades.append({
                    'return': returns,
                    'is_win': is_win,
                    'score': signal['score']
                })
    
    total = wins + losses
    if total == 0:
        return None
    
    win_rate = wins / total * 100
    
    # 計算 Sharpe Ratio (簡化版)
    if len(trades) > 1:
        returns = [t['return'] for t in trades]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    else:
        sharpe = 0
    
    # 計算平均收益
    avg_return = np.mean([t['return'] for t in trades]) * 100 if trades else 0
    
    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'sharpe': sharpe
    }

def optimize_parameters():
    """參數優化主函數"""
    print("=" * 70)
    print("Louie 策略 - 參數優化")
    print("=" * 70)
    
    # 結束日期
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 1年數據
    
    print(f"\n數據期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 預先獲取所有股票的數據
    print("\n獲取股票數據...")
    stock_data = {}
    for symbol in SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            if df is not None and len(df) > 60:
                stock_data[symbol] = calculate_indicators(df)
                print(f"  ✓ {symbol}: {len(df)} 天")
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")
    
    # 參數網格
    param_grid = {
        'score_threshold': [50, 55, 60, 65, 70],
        'rsi_oversold': [25, 30, 35],
        'rsi_overbought': [65, 70, 75],
        'stop_loss': [0.05, 0.08, 0.10],
        'take_profit': [0.12, 0.15, 0.20],
        'oos_length': [20, 30, 45],
        'rsi_weight': [15, 20, 25],
        'macd_weight': [20, 25, 30],
        'kdj_weight': [10, 15, 20],
        'ma_weight': [15, 20, 25],
    }
    
    # 簡化測試：先測試核心參數
    print("\n" + "=" * 70)
    print("第一階段：測試核心參數")
    print("=" * 70)
    
    # 核心參數測試
    core_results = []
    core_combinations = [
        # (score_threshold, rsi_oversold, rsi_overbought, stop_loss, take_profit, oos_length)
        (50, 30, 70, 0.08, 0.15, 30),
        (55, 30, 70, 0.08, 0.15, 30),
        (60, 30, 70, 0.08, 0.15, 30),
        (65, 30, 70, 0.08, 0.15, 30),
        (70, 30, 70, 0.08, 0.15, 30),
        (55, 25, 70, 0.08, 0.15, 30),
        (55, 35, 70, 0.08, 0.15, 30),
        (55, 30, 65, 0.08, 0.15, 30),
        (55, 30, 75, 0.08, 0.15, 30),
        (55, 30, 70, 0.05, 0.15, 30),
        (55, 30, 70, 0.10, 0.15, 30),
        (55, 30, 70, 0.08, 0.12, 30),
        (55, 30, 70, 0.08, 0.20, 30),
        (55, 30, 70, 0.08, 0.15, 20),
        (55, 30, 70, 0.08, 0.15, 45),
    ]
    
    base_params = {
        'score_threshold': 60,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'stop_loss': 0.08,
        'take_profit': 0.15,
        'oos_length': 30,
        'is_length': 60,
        'rsi_weight': 20,
        'macd_weight': 25,
        'kdj_weight': 15,
        'ma_weight': 20,
        'vol_weight': 10,
        'bb_weight': 10,
    }
    
    for combo in core_combinations:
        params = base_params.copy()
        params['score_threshold'] = combo[0]
        params['rsi_oversold'] = combo[1]
        params['rsi_overbought'] = combo[2]
        params['stop_loss'] = combo[3]
        params['take_profit'] = combo[4]
        params['oos_length'] = combo[5]
        
        total_wins = 0
        total_losses = 0
        total_trades = 0
        
        for symbol, df in stock_data.items():
            result = run_backtest_single_params(df, params)
            if result:
                total_wins += result['wins']
                total_losses += result['losses']
                total_trades += result['total']
        
        if total_trades > 0:
            win_rate = total_wins / total_trades * 100
            print(f"  閾值={combo[0]}, RSI=({combo[1]},{combo[2]}), SL={combo[3]:.0%}, TP={combo[4]:.0%}, 持倉={combo[5]}天 => 交易:{total_trades}, 勝率:{win_rate:.1f}%")
            
            core_results.append({
                'params': {
                    'score_threshold': combo[0],
                    'rsi_oversold': combo[1],
                    'rsi_overbought': combo[2],
                    'stop_loss': combo[3],
                    'take_profit': combo[4],
                    'oos_length': combo[5],
                },
                'total_trades': total_trades,
                'wins': total_wins,
                'losses': total_losses,
                'win_rate': win_rate
            })
    
    # 找出最佳參數
    if core_results:
        best = max(core_results, key=lambda x: (x['win_rate'], x['total_trades']))
        print(f"\n🏆 最佳核心參數: 勝率 {best['win_rate']:.1f}%, 交易次數 {best['total_trades']}")
        print(f"   閾值={best['params']['score_threshold']}, RSI=({best['params']['rsi_oversold']},{best['params']['rsi_overbought']})")
        print(f"   SL={best['params']['stop_loss']:.0%}, TP={best['params']['take_profit']:.0%}, 持倉={best['params']['oos_length']}天")
    
    # 第二階段：權重優化
    print("\n" + "=" * 70)
    print("第二階段：測試權重組合")
    print("=" * 70)
    
    weight_combinations = [
        # (rsi_weight, macd_weight, kdj_weight, ma_weight)
        (15, 25, 15, 20),
        (20, 20, 15, 20),
        (20, 25, 10, 20),
        (20, 25, 15, 15),
        (25, 20, 15, 15),
        (15, 30, 15, 15),
        (20, 30, 10, 15),
    ]
    
    best_params = best['params'].copy() if core_results else base_params.copy()
    weight_results = []
    
    for w_combo in weight_combinations:
        params = base_params.copy()
        params.update(best_params)
        params['rsi_weight'] = w_combo[0]
        params['macd_weight'] = w_combo[1]
        params['kdj_weight'] = w_combo[2]
        params['ma_weight'] = w_combo[3]
        
        total_wins = 0
        total_losses = 0
        total_trades = 0
        
        for symbol, df in stock_data.items():
            result = run_backtest_single_params(df, params)
            if result:
                total_wins += result['wins']
                total_losses += result['losses']
                total_trades += result['total']
        
        if total_trades > 0:
            win_rate = total_wins / total_trades * 100
            print(f"  RSI={w_combo[0]}, MACD={w_combo[1]}, KDJ={w_combo[2]}, MA={w_combo[3]} => 交易:{total_trades}, 勝率:{win_rate:.1f}%")
            
            weight_results.append({
                'weights': {
                    'rsi_weight': w_combo[0],
                    'macd_weight': w_combo[1],
                    'kdj_weight': w_combo[2],
                    'ma_weight': w_combo[3],
                },
                'total_trades': total_trades,
                'wins': total_wins,
                'losses': total_losses,
                'win_rate': win_rate
            })
    
    # 找出最佳權重
    if weight_results:
        best_weight = max(weight_results, key=lambda x: (x['win_rate'], x['total_trades']))
        print(f"\n🏆 最佳權重: RSI={best_weight['weights']['rsi_weight']}, MACD={best_weight['weights']['macd_weight']}, KDJ={best_weight['weights']['kdj_weight']}, MA={best_weight['weights']['ma_weight']}")
        print(f"   勝率: {best_weight['win_rate']:.1f}%, 交易次數: {best_weight['total_trades']}")
    
    # 合併最佳參數
    final_params = base_params.copy()
    if core_results:
        final_params.update(best['params'])
    if weight_results:
        final_params.update(best_weight['weights'])
    
    # 保存結果
    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "optimization_type": "參數網格搜索",
        "data_period": f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
        "core_results": core_results,
        "weight_results": weight_results,
        "best_core_params": best.get('params', {}) if core_results else {},
        "best_weights": best_weight.get('weights', {}) if weight_results else {},
        "final_params": final_params
    }
    
    with open("/Users/changrunlin/.openclaw/workspace/louie_optimization_result.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print("📊 最終最佳參數")
    print("=" * 70)
    for k, v in final_params.items():
        print(f"  {k}: {v}")
    
    print(f"\n✅ 結果已保存至: louie_optimization_result.json")
    
    return final_params

if __name__ == "__main__":
    optimize_parameters()
