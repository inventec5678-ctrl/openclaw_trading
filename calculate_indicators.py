#!/usr/bin/env python3
"""
技術指標計算腳本
計算：均線 (MA5, MA10, MA20, MA60)、KD 指標、MACD、RSI
"""

import yfinance as yf
import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 股票清單
TAIWAN_STOCKS = ['2330.TW', '2317.TW', '2454.TW', '0050.TW']
US_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
ALL_STOCKS = TAIWAN_STOCKS + US_STOCKS

OUTPUT_DIR = os.path.expanduser('~/openclaw_data/indicators')

def calculate_ma(data, period):
    """計算移動平均線"""
    return data['Close'].rolling(window=period).mean()

def calculate_kd(high, low, close, period=9):
    """計算 KD 指標"""
    # 計算 RSV (Raw Stochastic Value)
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)
    
    # 計算 K 值 (平滑 RSV)
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    
    # 計算 D 值 (平滑 K)
    d = k.ewm(alpha=1/3, adjust=False).mean()
    
    return k, d

def calculate_macd(data, fast=12, slow=26, signal=9):
    """計算 MACD 指標"""
    ema_fast = data['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['Close'].ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_rsi(data, period=14):
    """計算 RSI 相對強弱指標"""
    delta = data['Close'].diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # 使用 EMA 方式計算
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def get_indicators(ticker_symbol, period='1y'):
    """取得股票技術指標"""
    try:
        # 下載歷史數據
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period=period)
        
        if data.empty:
            return {'symbol': ticker_symbol, 'error': 'No data available'}
        
        # 計算均線
        data['MA5'] = calculate_ma(data, 5)
        data['MA10'] = calculate_ma(data, 10)
        data['MA20'] = calculate_ma(data, 20)
        data['MA60'] = calculate_ma(data, 60)
        
        # 計算 KD 指標
        data['K'], data['D'] = calculate_kd(data['High'], data['Low'], data['Close'])
        
        # 計算 MACD
        data['MACD'], data['Signal'], data['Histogram'] = calculate_macd(data)
        
        # 計算 RSI
        data['RSI'] = calculate_rsi(data)
        
        # 取得最新指標值
        latest = data.iloc[-1]
        
        result = {
            'symbol': ticker_symbol,
            'timestamp': datetime.now().isoformat(),
            'period': period,
            'latest': {
                'date': str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10],
                'close': float(latest['Close']),
                'ma5': float(latest['MA5']) if pd.notna(latest['MA5']) else None,
                'ma10': float(latest['MA10']) if pd.notna(latest['MA10']) else None,
                'ma20': float(latest['MA20']) if pd.notna(latest['MA20']) else None,
                'ma60': float(latest['MA60']) if pd.notna(latest['MA60']) else None,
                'k': float(latest['K']) if pd.notna(latest['K']) else None,
                'd': float(latest['D']) if pd.notna(latest['D']) else None,
                'macd': float(latest['MACD']) if pd.notna(latest['MACD']) else None,
                'signal': float(latest['Signal']) if pd.notna(latest['Signal']) else None,
                'histogram': float(latest['Histogram']) if pd.notna(latest['Histogram']) else None,
                'rsi': float(latest['RSI']) if pd.notna(latest['RSI']) else None,
            },
            # 歷史數據 (最近30天)
            'history_30d': data[['Open', 'High', 'Low', 'Close', 'Volume', 
                                 'MA5', 'MA10', 'MA20', 'MA60',
                                 'K', 'D', 'MACD', 'Signal', 'Histogram', 'RSI']].tail(30).to_dict(orient='records')
        }
        
        # 技術指標解讀
        result['analysis'] = analyze_indicators(result['latest'])
        
        return result
        
    except Exception as e:
        return {
            'symbol': ticker_symbol,
            'error': str(e)
        }

def analyze_indicators(latest):
    """分析技術指標"""
    analysis = []
    
    # 均線分析
    if latest['ma5'] and latest['ma20']:
        if latest['ma5'] > latest['ma20']:
            analysis.append({'type': 'MA', 'signal': 'bullish', 'message': 'MA5 > MA20, 多頭排列'})
        else:
            analysis.append({'type': 'MA', 'signal': 'bearish', 'message': 'MA5 < MA20, 空頭排列'})
    
    # RSI 分析
    if latest['rsi']:
        rsi = latest['rsi']
        if rsi > 70:
            analysis.append({'type': 'RSI', 'signal': 'overbought', 'message': f'RSI={rsi:.1f}, 超買區'})
        elif rsi < 30:
            analysis.append({'type': 'RSI', 'signal': 'oversold', 'message': f'RSI={rsi:.1f}, 超賣區'})
        else:
            analysis.append({'type': 'RSI', 'signal': 'neutral', 'message': f'RSI={rsi:.1f}, 中性區'})
    
    # KD 指標分析
    if latest['k'] and latest['d']:
        k, d = latest['k'], latest['d']
        if k > 80:
            analysis.append({'type': 'KD', 'signal': 'overbought', 'message': f'K={k:.1f}, 超買'})
        elif k < 20:
            analysis.append({'type': 'KD', 'signal': 'oversold', 'message': f'K={k:.1f}, 超賣'})
        elif k > d:
            analysis.append({'type': 'KD', 'signal': 'bullish', 'message': f'K>{d}, 多頭'})
        else:
            analysis.append({'type': 'KD', 'signal': 'bearish', 'message': f'K<{d}, 空頭'})
    
    # MACD 分析
    if latest['macd'] and latest['signal']:
        if latest['histogram'] > 0:
            analysis.append({'type': 'MACD', 'signal': 'bullish', 'message': 'MACD > Signal, 多頭'})
        else:
            analysis.append({'type': 'MACD', 'signal': 'bearish', 'message': 'MACD < Signal, 空頭'})
    
    return analysis

def main():
    print("=" * 70)
    print("技術指標計算")
    print("=" * 70)
    
    all_data = {}
    
    for symbol in ALL_STOCKS:
        print(f"\n正在計算 {symbol} 技術指標...")
        data = get_indicators(symbol)
        all_data[symbol] = data
        
        if 'error' in data:
            print(f"  ❌ 錯誤: {data['error']}")
        else:
            latest = data['latest']
            print(f"  ✓ 最新收盤價: ${latest['close']:.2f}")
            print(f"    均線: MA5=${latest['ma5']:.2f}, MA10=${latest['ma10']:.2f}, MA20=${latest['ma20']:.2f}, MA60=${latest['ma60']:.2f}")
            print(f"    KD: K={latest['k']:.2f}, D={latest['d']:.2f}")
            print(f"    MACD: {latest['macd']:.4f}, Signal: {latest['signal']:.4f}")
            print(f"    RSI: {latest['rsi']:.2f}")
            
            if data.get('analysis'):
                print("    分析:", ", ".join([a['message'] for a in data['analysis']]))
    
    # 儲存為 JSON
    output_file = os.path.join(OUTPUT_DIR, 'technical_indicators.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n{'=' * 70}")
    print(f"✓ 技術指標已儲存至: {output_file}")
    print("=" * 70)
    
    # 產生摘要表格
    print("\n📊 技術指標摘要:")
    print("-" * 70)
    print(f"{'代碼':8} | {'收盤價':>8} | {'MA5':>8} | {'MA20':>8} | {'RSI':>6} | {'K':>6} | {'D':>6} | {'趨勢':<8}")
    print("-" * 70)
    
    for symbol in ALL_STOCKS:
        if symbol in all_data and 'latest' in all_data[symbol]:
            d = all_data[symbol]['latest']
            
            # 判斷趨勢
            trend = "中性"
            if d.get('ma5') and d.get('ma20'):
                if d['ma5'] > d['ma20']:
                    trend = "多頭"
                else:
                    trend = "空頭"
            
            print(f"{symbol:8} | ${d['close']:>7.2f} | ${d['ma5']:>7.2f} | ${d['ma20']:>7.2f} | {d['rsi']:>6.1f} | {d['k']:>6.1f} | {d['d']:>6.1f} | {trend:<8}")

if __name__ == '__main__':
    main()
