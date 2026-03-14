#!/usr/bin/env python3
"""
新量化因子研究 - 新增因子庫
Louie 量化策略優化

新增因子:
1. ATR (Average True Range) - 波動率因子
2. OBV (On-Balance Volume) - 成交量動量
3. ADX (Average Directional Index) - 趨勢強度
4. ROC (Rate of Change) - 價格變動率
5. MFI (Money Flow Index) - 資金流向
6. CMF (Chaikin Money Flow) - 蔡金資金流量
7. VWAP (Volume Weighted Average Price) - 成交量加權均價
8. Stochastic RSI - RSI 隨機指標
"""

import json
import os
from pathlib import Path
from datetime import datetime
import numpy as np

try:
    import yfinance as yf
    USE_YFINANCE = True
except ImportError:
    USE_YFINANCE = False
    print("Warning: yfinance not available")

# 數據路徑
DATA_DIR = Path.home() / "openclaw_data"
NEW_FACTORS_DIR = DATA_DIR / "new_factors"
NEW_FACTORS_DIR.mkdir(parents=True, exist_ok=True)


def calculate_atr(high, low, close, period=14):
    """計算平均真實範圍 (ATR) - 波動率因子"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_obv(close, volume):
    """計算能量潮 (OBV) - 成交量動量"""
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def calculate_adx(high, low, close, period=14):
    """計算平均趨向指數 (ADX) - 趨勢強度"""
    # 計算 +DI 和 -DI
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = calculate_atr(high, low, close, period)
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di


def calculate_roc(close, period=12):
    """計算變動率 (ROC) - 價格動量"""
    roc = ((close - close.shift(period)) / close.shift(period)) * 100
    return roc


def calculate_mfi(high, low, close, volume, period=14):
    """計算貨幣流量指標 (MFI) - 資金流向"""
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    
    return mfi


def calculate_cmf(high, low, close, volume, period=20):
    """計算蔡金資金流量 (CMF) - 資金流量"""
    money_flow_multiplier = ((close - low) - (high - close)) / (high - low)
    money_flow_multiplier = money_flow_multiplier.fillna(0)
    
    money_flow_volume = money_flow_multiplier * volume
    
    cmf = money_flow_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
    
    return cmf


def calculate_vwap(high, low, close, volume):
    """計算成交量加權均價 (VWAP)"""
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    
    return vwap


def calculate_stochastic_rsi(close, period=14, k_period=3, d_period=3):
    """計算隨機 RSI (Stochastic RSI)"""
    # 計算 RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # 計算 Stochastic RSI
    stoch_rsi = (rsi - rsi.rolling(window=period).min()) / \
                (rsi.rolling(window=period).max() - rsi.rolling(window=period).min())
    stoch_rsi = stoch_rsi * 100
    
    # K 和 D 線
    k = stoch_rsi.rolling(window=k_period).mean()
    d = k.rolling(window=d_period).mean()
    
    return stoch_rsi, k, d


def calculate_bollinger_bands(close, period=20, std_dev=2):
    """計算布林通道"""
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    bb_width = (upper - lower) / middle
    bb_position = (close - lower) / (upper - lower)
    
    return upper, middle, lower, bb_width, bb_position


def calculate_new_factors(symbol):
    """計算新因子並返回結果"""
    if not USE_YFINANCE:
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo")
        
        if df.empty or len(df) < 30:
            return None
        
        # 計算各項新因子
        atr = calculate_atr(df['High'], df['Low'], df['Close'])
        obv = calculate_obv(df['Close'], df['Volume'])
        adx, plus_di, minus_di = calculate_adx(df['High'], df['Low'], df['Close'])
        roc = calculate_roc(df['Close'])
        mfi = calculate_mfi(df['High'], df['Low'], df['Close'], df['Volume'])
        cmf = calculate_cmf(df['High'], df['Low'], df['Close'], df['Volume'])
        vwap = calculate_vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        stoch_rsi, k, d = calculate_stochastic_rsi(df['Close'])
        upper, middle, lower, bb_width, bb_position = calculate_bollinger_bands(df['Close'])
        
        latest = df.iloc[-1]
        
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "price": {
                "close": float(latest['Close']),
                "high": float(latest['High']),
                "low": float(latest['Low']),
                "open": float(latest['Open']),
                "volume": int(latest['Volume']),
                "vwap": float(vwap.iloc[-1]) if not vwap.empty else None
            },
            "new_factors": {
                "atr": {
                    "value": float(atr.iloc[-1]) if not atr.empty else None,
                    "period": 14,
                    "description": "Average True Range - 波動率指標"
                },
                "obv": {
                    "value": float(obv.iloc[-1]) if not obv.empty else None,
                    "description": "On-Balance Volume - 成交量動量"
                },
                "adx": {
                    "value": float(adx.iloc[-1]) if not adx.empty else None,
                    "plus_di": float(plus_di.iloc[-1]) if not plus_di.empty else None,
                    "minus_di": float(minus_di.iloc[-1]) if not minus_di.empty else None,
                    "description": "Average Directional Index - 趨勢強度"
                },
                "roc": {
                    "value": float(roc.iloc[-1]) if not roc.empty else None,
                    "period": 12,
                    "description": "Rate of Change - 價格變動率"
                },
                "mfi": {
                    "value": float(mfi.iloc[-1]) if not mfi.empty else None,
                    "period": 14,
                    "description": "Money Flow Index - 資金流向"
                },
                "cmf": {
                    "value": float(cmf.iloc[-1]) if not cmf.empty else None,
                    "period": 20,
                    "description": "Chaikin Money Flow - 蔡金資金流量"
                },
                "stochastic_rsi": {
                    "stoch_rsi": float(stoch_rsi.iloc[-1]) if not stoch_rsi.empty else None,
                    "k": float(k.iloc[-1]) if not k.empty else None,
                    "d": float(d.iloc[-1]) if not d.empty else None,
                    "description": "Stochastic RSI - RSI 隨機指標"
                },
                "bollinger": {
                    "upper": float(upper.iloc[-1]) if not upper.empty else None,
                    "middle": float(middle.iloc[-1]) if not middle.empty else None,
                    "lower": float(lower.iloc[-1]) if not lower.empty else None,
                    "width": float(bb_width.iloc[-1]) if not bb_width.empty else None,
                    "position": float(bb_position.iloc[-1]) if not bb_position.empty else None,
                    "description": "Bollinger Bands - 布林通道"
                }
            }
        }
        
        return result
        
    except Exception as e:
        print(f"Error calculating new factors for {symbol}: {e}")
        return None


def score_new_factors(factors_data):
    """根據新因子計算評分"""
    if not factors_data:
        return 50, {}
    
    scores = {}
    details = {}
    
    nf = factors_data.get("new_factors", {})
    
    # 1. ATR 波動率評分 - 波動率過高或過低都不好
    atr = nf.get("atr", {}).get("value")
    if atr:
        # 相對 ATR = ATR / 價格
        close = factors_data.get("price", {}).get("close", 1)
        relative_atr = (atr / close) * 100
        
        if relative_atr < 1:
            atr_score = 50  # 波動太低，流動性差
        elif relative_atr < 3:
            atr_score = 75  # 適中波動
        elif relative_atr < 5:
            atr_score = 60  # 波動較大
        else:
            atr_score = 40  # 波動過大，風險高
        scores["atr"] = atr_score
        details["atr_score"] = atr_score
    
    # 2. ADX 趨勢強度評分
    adx = nf.get("adx", {}).get("value")
    plus_di = nf.get("adx", {}).get("plus_di")
    minus_di = nf.get("adx", {}).get("minus_di")
    
    if adx and plus_di and minus_di:
        if adx >= 25:
            if plus_di > minus_di:
                adx_score = 80  # 強上升趨勢
            else:
                adx_score = 30  # 強下降趨勢
        elif adx >= 15:
            if plus_di > minus_di:
                adx_score = 65  # 中等上升趨勢
            else:
                adx_score = 35  # 中等下降趨勢
        else:
            adx_score = 50  # 盤整
        scores["adx"] = adx_score
        details["adx_score"] = adx_score
    
    # 3. ROC 變動率評分
    roc = nf.get("roc", {}).get("value")
    if roc:
        if roc > 10:
            roc_score = 70  # 強勢上漲
        elif roc > 3:
            roc_score = 60  # 温和上漲
        elif roc > -3:
            roc_score = 50  # 盤整
        elif roc > -10:
            roc_score = 40  # 温和下跌
        else:
            roc_score = 30  # 強勢下跌
        scores["roc"] = roc_score
        details["roc_score"] = roc_score
    
    # 4. MFI 資金流向評分
    mfi = nf.get("mfi", {}).get("value")
    if mfi:
        if mfi > 80:
            mfi_score = 30  # 過熱
        elif mfi > 60:
            mfi_score = 70  # 資金流入
        elif mfi > 40:
            mfi_score = 50  # 中性
        elif mfi > 20:
            mfi_score = 40  # 資金流出
        else:
            mfi_score = 30  # 超賣
        scores["mfi"] = mfi_score
        details["mfi_score"] = mfi_score
    
    # 5. CMF 蔡金資金流量評分
    cmf = nf.get("cmf", {}).get("value")
    if cmf:
        if cmf > 0.2:
            cmf_score = 75  # 強資金流入
        elif cmf > 0:
            cmf_score = 60  # 溫和資金流入
        elif cmf > -0.2:
            cmf_score = 40  # 溫和資金流出
        else:
            cmf_score = 25  # 強資金流出
        scores["cmf"] = cmf_score
        details["cmf_score"] = cmf_score
    
    # 6. Stochastic RSI 評分
    stoch_rsi = nf.get("stochastic_rsi", {})
    k = stoch_rsi.get("k")
    d = stoch_rsi.get("d")
    
    if k and d:
        if k > d and k < 30:
            stoch_rsi_score = 80  # 黃金交叉且超賣
        elif k > d:
            stoch_rsi_score = 65  # 黃金交叉
        elif k < d and k > 70:
            stoch_rsi_score = 20  # 死亡交叉且超買
        elif k < d:
            stoch_rsi_score = 35  # 死亡交叉
        else:
            stoch_rsi_score = 50
        scores["stoch_rsi"] = stoch_rsi_score
        details["stoch_rsi_score"] = stoch_rsi_score
    
    # 7. 布林通道評分
    bb = nf.get("bollinger", {})
    bb_position = bb.get("position")
    
    if bb_position is not None:
        if bb_position > 0.8:
            bb_score = 30  # 接近上軌，超買
        elif bb_position < 0.2:
            bb_score = 70  # 接近下軌，超賣可能反彈
        elif bb_position > 0.5:
            bb_score = 60  # 中上半
        else:
            bb_score = 40  # 中下半
        scores["bollinger"] = bb_score
        details["bb_score"] = bb_score
    
    # 計算加權平均分數
    # 權重: ADX 25%, ROC 20%, MFI 20%, CMF 15%, Stochastic RSI 15%, ATR 5%
    weights = {
        "adx": 0.25,
        "roc": 0.20,
        "mfi": 0.20,
        "cmf": 0.15,
        "stoch_rsi": 0.15,
        "atr": 0.05
    }
    
    total_score = 50  # 默認中性
    weight_sum = 0
    
    for factor, score in scores.items():
        weight = weights.get(factor, 0)
        total_score += (score - 50) * weight
        weight_sum += weight
    
    if weight_sum > 0:
        total_score = 50 + (total_score - 50) / weight_sum
    
    return round(total_score, 1), details, scores


def analyze_symbols(symbols):
    """分析多個股票的新因子"""
    results = []
    
    for symbol in symbols[:20]:  # 限制分析數量
        print(f"Analyzing {symbol}...")
        
        factors_data = calculate_new_factors(symbol)
        
        if factors_data:
            score, details, raw_scores = score_new_factors(factors_data)
            
            # 存儲結果
            output_file = NEW_FACTORS_DIR / f"{symbol}_new_factors.json"
            with open(output_file, "w") as f:
                json.dump(factors_data, f, indent=2, default=str)
            
            results.append({
                "symbol": symbol,
                "score": score,
                "details": details,
                "raw_scores": raw_scores,
                "close": factors_data.get("price", {}).get("close"),
                "adx": factors_data.get("new_factors", {}).get("adx", {}).get("value"),
                "mfi": factors_data.get("new_factors", {}).get("mfi", {}).get("value"),
                "roc": factors_data.get("new_factors", {}).get("roc", {}).get("value"),
            })
    
    return results


# 測試股票列表
TEST_STOCKS = [
    "2330.TW",  # 台積電
    "0050.TW",  # 元大台灣50
    "2317.TW",  # 鴻海
    "2454.TW",  # 聯發科
    "2603.TW",  # 長榮
    "AAPL",     # Apple
    "NVDA",     # NVIDIA
    "TSLA",     # Tesla
]


if __name__ == "__main__":
    import pandas as pd
    
    print("=" * 60)
    print("新量化因子研究 - Louie Strategy Optimization")
    print("=" * 60)
    
    # 分析股票
    results = analyze_symbols(TEST_STOCKS)
    
    print("\n" + "=" * 60)
    print("新因子評分結果")
    print("=" * 60)
    
    # 按分數排序
    results.sort(key=lambda x: x["score"], reverse=True)
    
    for r in results:
        print(f"\n{r['symbol']}: {r['score']}分")
        print(f"  ADX(趨勢): {r.get('adx', 'N/A'):.1f}, MFI(資金): {r.get('mfi', 'N/A'):.1f}, ROC(動量): {r.get('roc', 'N/A'):.1f}%")
        print(f"  細節: {r.get('details', {})}")
    
    # 保存排名結果
    ranking_file = NEW_FACTORS_DIR / "ranking.json"
    with open(ranking_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n結果已保存到: {ranking_file}")
    print("完成！")
