#!/usr/bin/env python3
"""
Louie 策略 - 新因子優化版本
測試 advanced factors (TRIX, MFI, CCI, Williams%R, OBV等) 的組合效果
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

def calculate_advanced_indicators(df):
    """計算進階技術指標"""
    df = df.copy()
    
    # 基礎 MA
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
    
    # ====== 新因子 ======
    
    # TRIX (Triple Exponential Average)
    ema1 = df['Close'].ewm(span=15, adjust=False).mean()
    ema2 = ema1.ewm(span=15, adjust=False).mean()
    ema3 = ema2.ewm(span=15, adjust=False).mean()
    df['TRIX'] = ema3.pct_change() * 100
    df['TRIX'] = df['TRIX'].fillna(0)
    
    # CCI (Commodity Channel Index)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    sma_tp = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
    df['CCI'] = (tp - sma_tp) / (0.015 * mad)
    df['CCI'] = df['CCI'].fillna(0)
    
    # Williams %R
    highest_high = df['High'].rolling(14).max()
    lowest_low = df['Low'].rolling(14).min()
    df['Williams_R'] = -100 * (highest_high - df['Close']) / (highest_high - lowest_low)
    df['Williams_R'] = df['Williams_R'].fillna(-50)
    
    # MFI (Money Flow Index)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    raw_money_flow = tp * df['Volume']
    money_flow_sign = np.where(tp > tp.shift(1), 1, -1)
    signed_money_flow = raw_money_flow * money_flow_sign
    positive_flow = signed_money_flow.where(signed_money_flow > 0, 0).rolling(14).sum()
    negative_flow = signed_money_flow.where(signed_money_flow < 0, 0).rolling(14).sum()
    mfi = 100 - (100 / (1 + positive_flow / negative_flow))
    df['MFI'] = mfi.fillna(50)
    
    # OBV (On-Balance Volume)
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['OBV'] = obv
    df['OBV_MA'] = obv.rolling(20).mean()
    df['OBV_Signal'] = np.where(obv > df['OBV_MA'], 1, -1)
    
    # Volume Ratio
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']
    
    # ROC (Rate of Change)
    df['ROC'] = ((df['Close'] - df['Close'].shift(12)) / df['Close'].shift(12)) * 100
    
    return df


def generate_signal_advanced(df, i, params):
    """根據參數生成交易信號 - 新因子版本"""
    if i < 60:
        return None
    
    row = df.iloc[i]
    prev_row = df.iloc[i-1]
    
    # 基礎分數
    score = 0
    
    # RSI (權重可調整)
    rsi_weight = params.get('rsi_weight', 15)
    if row['RSI'] < params.get('rsi_oversold', 30):
        score += rsi_weight
    elif row['RSI'] > params.get('rsi_overbought', 70):
        score -= rsi_weight * 0.5
    
    # MACD (權重可調整)
    macd_weight = params.get('macd_weight', 25)
    if row['MACD'] > row['Signal'] and prev_row['MACD'] <= prev_row['Signal']:
        score += macd_weight
    elif row['MACD'] < row['Signal'] and prev_row['MACD'] >= prev_row['Signal']:
        score -= macd_weight * 0.5
    
    # KDJ
    kdj_weight = params.get('kdj_weight', 15)
    if row['K'] < row['D'] and prev_row['K'] >= prev_row['D'] and row['K'] < 30:
        score += kdj_weight
    elif row['K'] > row['D'] and prev_row['K'] <= prev_row['D'] and row['K'] > 70:
        score -= kdj_weight * 0.5
    
    # MA 趨勢
    ma_weight = params.get('ma_weight', 15)
    if row['MA5'] > row['MA20'] and row['MA20'] > row['MA60']:
        score += ma_weight
    elif row['MA5'] < row['MA20'] and row['MA20'] < row['MA60']:
        score -= ma_weight * 0.5
    
    # 成交量
    vol_weight = params.get('vol_weight', 10)
    if row['Volume_Ratio'] > 1.2:
        score += vol_weight
    elif row['Volume_Ratio'] < 0.5:
        score -= vol_weight * 0.5
    
    # ====== 新因子評分 ======
    
    # TRIX (動量)
    trix_weight = params.get('trix_weight', 10)
    if row['TRIX'] > 0:
        score += trix_weight
    elif row['TRIX'] < 0:
        score -= trix_weight * 0.5
    
    # CCI (震盪)
    cci_weight = params.get('cci_weight', 8)
    if row['CCI'] < -100:
        score += cci_weight  # 超賣
    elif row['CCI'] > 100:
        score -= cci_weight * 0.5  # 超買
    
    # Williams %R
    williams_weight = params.get('williams_weight', 8)
    if row['Williams_R'] < -80:
        score += williams_weight  # 超賣
    elif row['Williams_R'] > -20:
        score -= williams_weight * 0.5  # 超買
    
    # MFI
    mfi_weight = params.get('mfi_weight', 8)
    if row['MFI'] < 20:
        score += mfi_weight  # 超賣
    elif row['MFI'] > 80:
        score -= mfi_weight * 0.5  # 超買
    
    # OBV 趨勢
    obv_weight = params.get('obv_weight', 5)
    if row['OBV_Signal'] > 0:
        score += obv_weight
    else:
        score -= obv_weight * 0.3
    
    # ROC
    roc_weight = params.get('roc_weight', 5)
    if row['ROC'] > 0:
        score += roc_weight
    elif row['ROC'] < 0:
        score -= roc_weight * 0.5
    
    return score


def run_backtest(df, params):
    """執行回測"""
    df = calculate_advanced_indicators(df)
    
    trades = []
    position = None
    entry_price = 0
    entry_date = None
    
    stop_loss = params.get('stop_loss', 0.08)
    take_profit = params.get('take_profit', 0.15)
    score_threshold = params.get('score_threshold', 55)
    
    for i in range(60, len(df)):
        row = df.iloc[i]
        
        if position is None:
            # 嘗試進場
            score = generate_signal_advanced(df, i, params)
            if score is not None and score >= score_threshold:
                position = 'long'
                entry_price = row['Close']
                entry_date = df.index[i]
        
        elif position == 'long':
            # 檢查是否停損/停利
            current_price = row['Close']
            price_change = (current_price - entry_price) / entry_price
            
            if price_change >= take_profit or price_change <= -stop_loss:
                trades.append({
                    'entry_date': str(entry_date),
                    'exit_date': str(df.index[i]),
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'return': price_change,
                    'result': 'win' if price_change > 0 else 'loss'
                })
                position = None
    
    return trades


def evaluate_params(params_list, symbols, start_date, end_date):
    """評估多組參數"""
    results = []
    
    print(f"開始回測 {len(symbols)} 支股票...")
    
    # 合併所有股票數據
    all_data = []
    for symbol in symbols:
        try:
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if len(df) > 100:
                df['Symbol'] = symbol
                all_data.append(df)
        except:
            pass
    
    if not all_data:
        print("無法下載股票數據")
        return results
    
    combined_df = pd.concat(all_data)
    
    print(f"總共 {len(combined_df)} 筆記錄")
    
    for params in params_list:
        all_trades = []
        
        for symbol in symbols:
            try:
                df = yf.download(symbol, start=start_date, end=end_date, progress=False)
                if len(df) > 100:
                    trades = run_backtest(df, params)
                    all_trades.extend(trades)
            except:
                pass
        
        if all_trades:
            wins = sum(1 for t in all_trades if t['result'] == 'win')
            losses = len(all_trades) - wins
            win_rate = wins / len(all_trades) * 100
            
            results.append({
                'params': params,
                'trades': len(all_trades),
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate
            })
            
            print(f"  參數: threshold={params['score_threshold']}, stop_loss={params['stop_loss']}, take_profit={params['take_profit']}")
            print(f"    TRIX_w={params.get('trix_weight', 10)}, CCI_w={params.get('cci_weight', 8)}, MFI_w={params.get('mfi_weight', 8)}")
            print(f"    交易次數: {len(all_trades)}, 勝率: {win_rate:.2f}%")
    
    return results


if __name__ == "__main__":
    # 測試不同參數組合
    param_combinations = []
    
    # 測試不同的新因子權重組合
    for threshold in [50, 55, 60]:
        for stop_loss in [0.08, 0.10, 0.12]:
            for take_profit in [0.15, 0.18, 0.20]:
                for trix_w in [8, 10, 12]:
                    for cci_w in [6, 8, 10]:
                        for mfi_w in [6, 8, 10]:
                            params = {
                                'score_threshold': threshold,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'rsi_weight': 15,
                                'macd_weight': 25,
                                'kdj_weight': 15,
                                'ma_weight': 10,
                                'vol_weight': 8,
                                'trix_weight': trix_w,
                                'cci_weight': cci_w,
                                'williams_weight': 6,
                                'mfi_weight': mfi_w,
                                'obv_weight': 4,
                                'roc_weight': 4,
                                'rsi_oversold': 30,
                                'rsi_overbought': 70
                            }
                            param_combinations.append(params)
    
    # 限制測試數量
    param_combinations = param_combinations[:100]
    
    print(f"測試 {len(param_combinations)} 組參數...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    results = evaluate_params(param_combinations, SYMBOLS, start_date, end_date)
    
    if results:
        # 排序結果
        results_sorted = sorted(results, key=lambda x: x['win_rate'], reverse=True)
        
        # 輸出最佳結果
        print("\n========== 最佳結果 ==========")
        for i, r in enumerate(results_sorted[:10]):
            print(f"\n#{i+1} 勝率: {r['win_rate']:.2f}%")
            print(f"   交易次數: {r['trades']}")
            print(f"   參數: {r['params']}")
        
        # 保存結果
        with open('/Users/changrunlin/.openclaw/workspace/louie_newfactors_optimization.json', 'w') as f:
            json.dump(results_sorted, f, indent=2, default=str)
        
        print(f"\n結果已保存到 louie_newfactors_optimization.json")
    else:
        print("沒有結果")
