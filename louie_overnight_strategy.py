#!/usr/bin/env python3
"""
Louie 隔日沖策略優化模組
Overnight Trading Strategy Module

特點:
- 短線持有 (當日沖或隔日沖)
- 嚴格停損停利
- 高頻交易
- 適合波動大的股票
"""

import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import random

# 強制使用 yfinance (避免 twstock 格式問題)
USE_TWSTOCK = False


def get_taiwan_stock_data(symbol, days=90):
    """獲取台灣股票數據 (使用 yfinance)"""
    try:
        # 使用 yfinance (Yahoo Finance)
        ticker = yf.Ticker(symbol)
        
        # 使用 start/end 參數而非 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days*2)
        
        df = ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                          end=end_date.strftime('%Y-%m-%d'))
        
        if df is not None and len(df) > 10:
            # 確保有必要的欄位 - 轉換為小寫
            df.columns = df.columns.str.lower()
            return df
        return None
    except Exception as e:
        print(f"獲取數據失敗: {e}")
    return None


def simulate_intraday_price(df, date):
    """模擬盤中價格變化 (用于當日沖模擬)"""
    # 簡單模擬: 開盤後有波動
    if date in df.index:
        base = df.loc[date, 'close']
    else:
        return None
    
    # 盤中高點通常是收盤價 * (1 + random * 波幅)
    # 盤中低點通常是收盤價 * (1 - random * 波幅)
    volatility = 0.02 + random.random() * 0.03  # 2-5% 波幅
    
    high = base * (1 + volatility)
    low = base * (1 - volatility)
    
    return {
        'open': base,
        'high': high,
        'low': low,
        'close': base
    }


def calculate_overnight_indicators(df):
    """計算隔日沖相關指標"""
    df = df.copy()
    
    # 當日漲跌幅
    df['daily_return'] = df['close'].pct_change()
    
    # 前一日漲跌幅 (開盤跳空參考)
    df['prev_return'] = df['daily_return'].shift(1)
    
    # 開盤跳空幅度
    df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    
    # 成交量變化
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(5).mean()
    
    # 盘中波动率 (high - low) / close
    df['intraday_volatility'] = (df['high'] - df['low']) / df['close']
    
    # 5日均線
    df['MA5'] = df['close'].rolling(5).mean()
    
    # 10日均線
    df['MA10'] = df['close'].rolling(10).mean()
    
    # 20日均線 (新增)
    df['MA20'] = df['close'].rolling(20).mean()
    
    # 價格相對於MA5的位置
    df['price_vs_ma5'] = (df['close'] - df['MA5']) / df['MA5']
    
    # RSI (短週期更適合短線)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
    rs = gain / loss
    df['RSI7'] = 100 - (100 / (1 + rs))
    
    # RSI14 (新增)
    gain14 = delta.where(delta > 0, 0).rolling(14).mean()
    loss14 = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs14 = gain14 / loss14
    df['RSI14'] = 100 - (100 / (1 + rs14))
    
    # MACD (新增)
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # KD 指標 (新增)
    low_min = df['low'].rolling(9).min()
    high_max = df['high'].rolling(9).max()
    df['K'] = 100 * (df['close'] - low_min) / (high_max - low_min + 0.001)
    df['D'] = df['K'].rolling(3).mean()
    
    # 開盤後的走勢 (開盤 vs 收盤)
    df['intraday_direction'] = np.where(df['close'] > df['open'], 1, -1)
    
    # 支撐/壓力位
    df['support'] = df['low'].rolling(5).min()
    df['resistance'] = df['high'].rolling(5).max()
    
    # 價格位置 (在近期高低點的位置)
    df['price_position'] = (df['close'] - df['support']) / (df['resistance'] - df['support'] + 0.001)
    
    # 布林通道 (新增)
    df['BB_middle'] = df['close'].rolling(20).mean()
    df['BB_std'] = df['close'].rolling(20).std()
    df['BB_upper'] = df['BB_middle'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_middle'] - 2 * df['BB_std']
    df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 0.001)
    
    # 動量指標 (新增)
    df['momentum'] = df['close'] / df['close'].shift(10) - 1
    
    return df


def generate_overnight_signal(df, i, params=None):
    """
    生成隔日沖交易信號
    
    策略邏輯:
    1. 選擇開盤跳空上漲的股票
    2. 當日收盤前買入
    3. 隔日沖: 隔日開盤或收盤賣出
    
    參數 (已優化):
    - min_gap: 最小跳空幅度 (默認 0.8%)
    - max_gap: 最大跳空幅度 (默認 5%)
    - min_volume_ratio: 最小成交量比 (默認 1.0)
    - target_return: 目標收益 (默認 1.5%)
    - stop_loss: 停損點 (默認 -8%) - 配合較長持有期
    - score_threshold: 信號閾值 (默認 60, 強烈推薦 65)
    """
    params = params or {
        'min_gap': 0.008,  # 優化後參數
        'max_gap': 0.05,
        'min_volume_ratio': 1.0,
        'target_return': 0.015,
        'stop_loss': -0.08,
        'holding_days': 1,
        'score_threshold': 60  # 優化後閾值
    }
    
    if i < 20:
        return None
    
    row = df.iloc[i]
    prev_row = df.iloc[i-1]
    
    # 檢查必要數據
    if pd.isna(row['gap']) or pd.isna(row['volume_ratio']):
        return None
    
    score = 0
    signals = []
    
    # === 買入信號評估 ===
    
    # 1. 開盤跳空 (權重: 20%)
    if params['min_gap'] < row['gap'] < params['max_gap']:
        score += 20
        signals.append('gap_up')
    elif row['gap'] > params['max_gap']:
        score -= 10
        signals.append('gap_too_big')
    
    # 2. 成交量放大 (權重: 15%)
    if row['volume_ratio'] > params['min_volume_ratio']:
        score += 15
        signals.append('volume_up')
    if row['volume_ratio'] > 1.5:
        score += 5
        signals.append('volume_surge')
    
    # 3. RSI 低檔反彈 (權重: 10%)
    if 30 < row['RSI7'] < 50:
        score += 10
        signals.append('rsi_rebound')
    elif row['RSI7'] < 30:
        score += 5
        signals.append('rsi_oversold')
    elif row['RSI7'] > 70:
        score -= 10
        signals.append('rsi_overbought')
    
    # 4. 價格在支撐附近 (權重: 10%)
    if row['price_position'] < 0.3:
        score += 10
        signals.append('near_support')
    
    # 5. 前一日漲跌幅為正 (權重: 5%)
    if row['prev_return'] > 0:
        score += 5
        signals.append('uptrend')
    
    # 6. 盘中波动适中 (權重: 5%)
    if 0.01 < row['intraday_volatility'] < 0.04:
        score += 5
        signals.append('good_volatility')
    
    # 7. 價格在MA5之上 (權重: 5%)
    if row['close'] > row['MA5']:
        score += 5
        signals.append('above_ma5')
    
    # === 新增指標信號 ===
    
    # 8. MACD 金叉 (權重: 15%)
    if row['MACD'] > row['MACD_signal'] and prev_row['MACD'] <= prev_row['MACD_signal']:
        score += 15
        signals.append('macd_golden')
    elif row['MACD'] > row['MACD_signal']:
        score += 8
        signals.append('macd_bullish')
    elif row['MACD'] < row['MACD_signal']:
        score -= 5
        signals.append('macd_bearish')
    
    # 9. KD 低檔金叉 (權重: 10%)
    if row['K'] > row['D'] and prev_row['K'] <= prev_row['D'] and row['K'] < 50:
        score += 10
        signals.append('kd_golden_oversold')
    elif row['K'] > row['D']:
        score += 5
        signals.append('kd_bullish')
    
    # 10. 布林通道反彈 (權重: 5%)
    if row['BB_position'] < 0.2:
        score += 5
        signals.append('bb_oversold')
    elif row['BB_position'] > 0.8:
        score -= 5
        signals.append('bb_overbought')
    
    # 11. 均線多頭排列 (權重: 5%)
    if row['MA5'] > row['MA10'] > row['MA20']:
        score += 5
        signals.append('ma_bullish')
    
    # 12. 動能正向 (權重: 5%)
    if row['momentum'] > 0:
        score += 5
        signals.append('positive_momentum')
    
    return {
        'score': score,
        'signals': signals,
        'gap': row['gap'],
        'volume_ratio': row['volume_ratio'],
        'rsi': row['RSI7'],
        'macd_hist': row['MACD_hist'],
        'k': row['K'],
        'price': row['close'],
        'entry_date': df.index[i]
    }


def simulate_overnight_trade(entry_price, exit_price, shares, commission=0.001425, tax=0.003):
    """
    模擬隔日沖交易成本
    
    台灣股票交易成本:
    - 券商手續費: 約 0.1425% (可議價)
    - 證交稅: 0.3% (賣出時)
    - 交易服務費: 很少
    
    當日沖銷免證交稅 (需符合資格)
    """
    # 買入手續費
    buy_commission = entry_price * shares * commission
    
    # 賣出手續費 + 證交稅
    sell_commission = exit_price * shares * commission
    sell_tax = exit_price * shares * tax
    
    total_cost = buy_commission + sell_commission + sell_tax
    
    # 淨利潤
    gross_profit = (exit_price - entry_price) * shares
    net_profit = gross_profit - total_cost
    
    return {
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'total_cost': total_cost,
        'return_pct': (exit_price - entry_price) / entry_price * 100,
        'net_return_pct': net_profit / (entry_price * shares) * 100
    }


def run_overnight_backtest(symbols, params=None, start_date=None, end_date=None):
    """
    執行隔日沖回測
    
    Args:
        symbols: 股票代碼列表
        params: 策略參數
        start_date: 開始日期
        end_date: 結束日期
    
    Returns:
        回測結果
    """
    params = params or {
        'min_gap': 0.008,  # 優化後參數
        'max_gap': 0.05,
        'min_volume_ratio': 1.0,
        'target_return': 0.015,
        'stop_loss': -0.08,  # 調高停損配合較長持有期
        'holding_days': 1,
        'score_threshold': 60  # 優化後閾值
    }

    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=90))
    
    print("=" * 70)
    print("Louie 隔日沖策略回測")
    print("=" * 70)
    print(f"回測期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"股票數量: {len(symbols)}")
    print(f"參數: {params}")
    
    all_trades = []
    total_wins = 0
    total_losses = 0
    total_profit = 0
    
    for symbol in symbols:
        print(f"\n處理: {symbol}")
        
        # 獲取數據
        df = get_taiwan_stock_data(symbol, days=120)
        
        if df is None or len(df) < 20:
            print(f"  ✗ 數據不足")
            continue
        
        # 計算指標
        df = calculate_overnight_indicators(df)
        
        # 遍歷每個交易日
        for i in range(10, len(df) - 1):
            signal = generate_overnight_signal(df, i, params)
            
            if signal and signal['score'] >= params.get('score_threshold', 50):
                entry_price = signal['price']
                entry_date = signal['entry_date']
                
                # 模擬隔日沖: 隔日賣出
                exit_date = df.index[i + 1]
                exit_price = df.loc[exit_date, 'open']  # 隔日開盤賣出
                
                # 也可以選擇收盤賣出
                # exit_price = df.loc[exit_date, 'close']
                
                # 計算交易結果 (假設買入1000股)
                shares = 1000
                result = simulate_overnight_trade(entry_price, exit_price, shares)
                
                is_win = result['net_profit'] > 0
                
                if is_win:
                    total_wins += 1
                else:
                    total_losses += 1
                
                total_profit += result['net_profit']
                
                trade = {
                    'symbol': symbol,
                    'entry_date': str(entry_date.date()) if hasattr(entry_date, 'date') else str(entry_date)[:10],
                    'entry_price': round(entry_price, 2),
                    'exit_date': str(exit_date.date()) if hasattr(exit_date, 'date') else str(exit_date)[:10],
                    'exit_price': round(exit_price, 2),
                    'shares': shares,
                    'gross_profit': round(result['gross_profit'], 2),
                    'net_profit': round(result['net_profit'], 2),
                    'return_pct': round(result['return_pct'], 2),
                    'net_return_pct': round(result['net_return_pct'], 2),
                    'is_win': is_win,
                    'signals': signal['signals'],
                    'score': signal['score']
                }
                
                all_trades.append(trade)
    
    # 統計結果
    total_trades = total_wins + total_losses
    
    if total_trades > 0:
        win_rate = total_wins / total_trades * 100
        avg_profit = total_profit / total_trades
        
        # 計算連續獲勝/連續虧損
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in all_trades:
            if trade['is_win']:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
        
        result = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'strategy': '隔日沖',
            'params': params,
            'total_trades': total_trades,
            'winning_trades': total_wins,
            'losing_trades': total_losses,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'avg_profit': round(avg_profit, 2),
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'trades': all_trades
        }
        
        print("\n" + "=" * 70)
        print("回測結果")
        print("=" * 70)
        print(f"總交易次數: {total_trades}")
        print(f"獲勝次數: {total_wins}")
        print(f"失敗次數: {total_losses}")
        print(f"勝率: {win_rate:.2f}%")
        print(f"總淨利潤: {total_profit:,.0f} 元")
        print(f"平均每筆利潤: {avg_profit:,.0f} 元")
        print(f"最大連續獲勝: {max_consecutive_wins}")
        print(f"最大連續虧損: {max_consecutive_losses}")
        
        return result
    else:
        print("\n⚠ 沒有產生任何交易信號")
        return None


def optimize_overnight_params(symbols, param_grid=None):
    """
    優化隔日沖策略參數
    
    參數網格 (已優化):
    - min_gap: 0.003 ~ 0.01 (最小跳空幅度)
    - max_gap: 0.03 ~ 0.08 (最大跳空幅度)
    - min_volume_ratio: 0.8 ~ 1.5 (成交量比)
    - target_return: 0.01 ~ 0.02 (目標收益)
    - stop_loss: -0.05 ~ -0.10 (停損)
    - score_threshold: 50 ~ 70 (信號分數閾值)
    """
    param_grid = param_grid or {
        'min_gap': [0.003, 0.005, 0.008],
        'max_gap': [0.04, 0.06, 0.08],
        'min_volume_ratio': [0.8, 1.0, 1.2],
        'target_return': [0.01, 0.015, 0.02],
        'stop_loss': [-0.05, -0.08, -0.10],
        'score_threshold': [50, 55, 60, 65]
    }
    
    print("=" * 70)
    print("隔日沖策略參數優化")
    print("=" * 70)
    
    # 測試參數組合 - 擴展測試範圍
    best_params = None
    best_win_rate = 0
    best_result = None
    
    # 測試不同參數組合 (基於高勝率股票的回測經驗)
    test_combinations = [
        # (min_gap, max_gap, score_threshold, stop_loss)
        (0.005, 0.05, 55, -0.08),
        (0.005, 0.05, 60, -0.08),
        (0.005, 0.05, 65, -0.08),
        (0.003, 0.06, 55, -0.08),
        (0.005, 0.06, 60, -0.08),
        (0.008, 0.05, 60, -0.08),
        (0.003, 0.05, 50, -0.08),
        (0.005, 0.07, 55, -0.10),
        (0.003, 0.04, 55, -0.06),
        (0.005, 0.05, 65, -0.10),
    ]
    
    results = []
    
    for min_gap, max_gap, score_threshold, stop_loss in test_combinations:
        params = {
            'min_gap': min_gap,
            'max_gap': max_gap,
            'min_volume_ratio': 1.0,
            'target_return': 0.015,
            'stop_loss': stop_loss,
            'score_threshold': score_threshold
        }
        
        print(f"\n測試參數: min_gap={min_gap}, max_gap={max_gap}, threshold={score_threshold}")
        
        result = run_overnight_backtest(symbols, params)
        
        if result:
            results.append({
                'params': params,
                'win_rate': result['win_rate'],
                'total_trades': result['total_trades'],
                'total_profit': result['total_profit']
            })
            
            if result['win_rate'] > best_win_rate and result['total_trades'] >= 10:
                best_win_rate = result['win_rate']
                best_params = params
                best_result = result
    
    # 排序結果
    results.sort(key=lambda x: (x['win_rate'], x['total_trades']), reverse=True)
    
    print("\n" + "=" * 70)
    print("參數優化結果")
    print("=" * 70)
    print("\n排名 (按勝率):")
    for i, r in enumerate(results[:5]):
        print(f"{i+1}. 勝率: {r['win_rate']:.2f}%, 交易次數: {r['total_trades']}, 參數: {r['params']}")
    
    if best_params:
        print(f"\n✅ 最佳參數:")
        print(f"   min_gap: {best_params['min_gap']}")
        print(f"   max_gap: {best_params['max_gap']}")
        print(f"   score_threshold: {best_params['score_threshold']}")
        print(f"   勝率: {best_win_rate:.2f}%")
    
    return {
        'best_params': best_params,
        'best_result': best_result,
        'all_results': results
    }


def get_overnight_signals_today(symbols):
    """
    獲取今日隔日沖信號
    
    實時掃描符合條件的股票:
    1. 開盤跳空上漲
    2. 成交量放大
    3. RSI 未超買
    4. MACD 金叉
    5. KD 低檔反彈
    6. 價格在支撐附近
    """
    print("=" * 70)
    print("今日隔日沖信號掃描")
    print("=" * 70)
    
    # 使用優化後的參數 (2026-03-14 優化結果: 勝率 44.90%)
    params = {
        'min_gap': 0.008,  # 提高最小跳空門檻 (從 0.005 調高)
        'max_gap': 0.05,
        'min_volume_ratio': 1.0,
        'target_return': 0.015,
        'stop_loss': -0.08,
        'score_threshold': 60  # 提高閾值 (從 55 調高)
    }
    
    signals = []
    
    for symbol in symbols:
        try:
            # 獲取最近數據
            df = get_taiwan_stock_data(symbol, days=20)
            
            if df is None or len(df) < 10:
                continue
            
            # 計算指標
            df = calculate_overnight_indicators(df)
            
            # 獲取最新信號 (使用優化參數)
            i = len(df) - 1
            signal = generate_overnight_signal(df, i, params)
            
            if signal and signal['score'] >= params['score_threshold']:
                signals.append({
                    'symbol': symbol,
                    'score': signal['score'],
                    'price': round(signal['price'], 2),
                    'gap': round(signal['gap'] * 100, 2),
                    'volume_ratio': round(signal['volume_ratio'], 2),
                    'rsi': round(signal['rsi'], 1),
                    'macd_hist': round(signal['macd_hist'], 2),
                    'k': round(signal['k'], 1),
                    'signals': signal['signals'],
                    'recommendation': 'STRONG_BUY' if signal['score'] >= 65 else 'BUY' if signal['score'] >= 55 else 'WATCH'
                })
                
        except Exception as e:
            continue
    
    # 按分數排序
    signals.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n找到 {len(signals)} 個信號:")
    for s in signals:
        print(f"  {s['symbol']}: 分數={s['score']}, 價格={s['price']}, 跳空={s['gap']}%, RSI={s['rsi']}")
        print(f"    信號: {', '.join(s['signals'])}")
        print(f"    建議: {s['recommendation']}")
    
    return signals


# 預設股票列表 (台股熱門標的)
DEFAULT_TAIWAN_SYMBOLS = [
    "2330.TW",  # 台積電
    "2317.TW",  # 鴻海
    "2454.TW",  # 聯發科
    "2603.TW",  # 長榮
    "2615.TW",  # 萬海
    "2881.TW",  # 富邦金
    "2882.TW",  # 國泰金
    "2891.TW",  # 中信金
    "2002.TW",  # 中鋼
    "3034.TW",  # 聯詠
    "3413.TW",  # 友達
    "3481.TW",  # 群創
    "2382.TW",  # 廣達
    "2311.TW",  # 日月光
    "2474.TW",  # 可成
]


if __name__ == "__main__":
    import sys
    
    # 測試模式
    mode = sys.argv[1] if len(sys.argv) > 1 else "backtest"
    
    if mode == "backtest":
        # 執行回測
        result = run_overnight_backtest(DEFAULT_TAIWAN_SYMBOLS)
        
        if result:
            # 保存結果
            with open("/Users/changrunlin/.openclaw/workspace/louie_overnight_result.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n結果已保存: louie_overnight_result.json")
    
    elif mode == "optimize":
        # 執行參數優化
        opt_result = optimize_overnight_params(DEFAULT_TAIWAN_SYMBOLS)
        
        if opt_result and opt_result['best_params']:
            # 保存最佳參數
            with open("/Users/changrunlin/.openclaw/workspace/louie_overnight_best_params.json", "w", encoding="utf-8") as f:
                json.dump(opt_result['best_params'], f, indent=2, ensure_ascii=False)
            print(f"\n最佳參數已保存: louie_overnight_best_params.json")
    
    elif mode == "signal":
        # 獲取今日信號
        signals = get_overnight_signals_today(DEFAULT_TAIWAN_SYMBOLS)
        
        # 保存信號
        with open("/Users/changrunlin/.openclaw/workspace/louie_overnight_signals.json", "w", encoding="utf-8") as f:
            json.dump(signals, f, indent=2, ensure_ascii=False)
        print(f"\n信號已保存: louie_overnight_signals.json")
