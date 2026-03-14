#!/usr/bin/env python3
"""
綜合推薦系統 (Comprehensive Recommendation System)
根據市場情緒、新聞、技術指標、基本面、籌碼等因素進行綜合評分
自動根據台灣時間切換市場：
- 台股時段 (09:00-13:30): 推薦台股
- 美股時段 (21:30-04:00): 推薦美股
- 其他時間: 推薦加密貨幣
"""

import json
import os
from pathlib import Path
from datetime import datetime

# 數據路徑
DATA_DIR = Path.home() / "openclaw_data"

# 市場時段配置 (台北時間)
MARKET_HOURS = {
    "台股": {"start": "09:00", "end": "13:30", "timezone": "Asia/Taipei"},
    "美股": {"start": "21:30", "end": "04:00", "timezone": "America/New_York"},
    "加密": {"start": None, "end": None, "timezone": None}  # 24小時
}

# 加密貨幣列表 (10檔)
CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD",
    "DOGE-USD", "SOL-USD", "DOT-USD", "MATIC-USD", "LTC-USD"
]

# 台股100檔 (主要上市公司)
TAIWAN_STOCKS = [
    # 電子權值股
    "2330.TW", "2454.TW", "2317.TW", "3034.TW", "3711.TW",
    # 金融股
    "2885.TW", "2884.TW", "2883.TW", "2882.TW", "2881.TW",
    "2891.TW", "2892.TW", "5876.TW", "6005.TW", "5854.TW",
    # 傳產權值
    "2002.TW", "2105.TW", "1301.TW", "1303.TW", "1326.TW",
    "1216.TW", "9904.TW", "1707.TW", "2609.TW", "2603.TW",
    # 航運
    "2609.TW", "2615.TW", "2618.TW", "2633.TW", "2655.TW",
    # 半導體
    "2330.TW", "2454.TW", "3034.TW", "3443.TW", "3661.TW",
    "4968.TW", "5371.TW", "5469.TW", "6789.TW", "6655.TW",
    # AI/科技
    "2382.TW", "2395.TW", "2412.TW", "2383.TW", "4938.TW",
    "2327.TW", "2357.TW", "2376.TW", "2399.TW", "2427.TW",
    # 其他電子
    "2324.TW", "2344.TW", "2345.TW", "2353.TW", "2362.TW",
    "2377.TW", "2388.TW", "2390.TW", "2401.TW", "2408.TW",
    # 遊戲/網路
    "3089.TW", "3095.TW", "3130.TW", "3229.TW", "3257.TW",
    "3290.TW", "3356.TW", "3416.TW", "3443.TW", "3454.TW",
    # 生技/醫療
    "1707.TW", "1762.TW", "1783.TW", "1789.TW", "1795.TW",
    "1802.TW", "1805.TW", "1813.TW", "1834.TW", "1871.TW",
    # 營建/鋼鐵
    "2105.TW", "2106.TW", "2115.TW", "2211.TW", "2221.TW",
    "2227.TW", "2231.TW", "2233.TW", "2303.TW", "2308.TW",
    # 其他
    "0050.TW", "0056.TW", "00878.TW", "00881.TW", "00715B.TW",
    "1723.TW", "1722.TW", "1711.TW", "1760.TW", "1773.TW",
    "1477.TW", "1476.TW", "1473.TW", "1465.TW", "1463.TW"
]

# 美股100檔 (主要科技股 + S&P 500 成分股)
US_STOCKS = [
    # 科技巨頭
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "JNJ",
    # 半導體
    "AVGO", "AMD", "INTC", "QCOM", "TXN", "MU", "LRCX", "KLAC", "AMAT", "NXPI",
    "ADI", "MRVL", "ON", "MCHP", "ENTG", "FSLR", "ENPH", "SEDG", "SPWR", "FSLR",
    # 軟體/雲端
    "CRM", "ORCL", "ADBE", "NOW", "SNOW", "PANW", "CRWD", "ZM", "DOCU", "TEAM",
    "WDAY", "OKTA", "SPLK", "VEEV", "TWLO", "SQ", "SHOP", "UBER", "LYFT", "DASH",
    # 網路/媒體
    "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "PARA", "WBD", "FOX",
    # 金融
    "BAC", "WFC", "GS", "MS", "C", "BLK", "AXP", "USB", "PNC", "TFC",
    "COF", "SCHW", "SPGI", "MCO", "AON", "CB", "PGR", "CME", "ICE", "COIN",
    # 消費
    "WMT", "HD", "COST", "TGT", "LOW", "NKE", "SBUX", "MCD", "KO", "PEP",
    "PG", "CL", "EL", "KMB", "GIS", "K", "HSY", "MDLZ", "KHC", "GILD",
    # 醫藥
    "UNH", "LLY", "ABBV", "MRK", "PFE", "BMY", "AMGN", "GILD", "BIIB", "REGN",
    "VRTX", "MRNA", "ISRG", "BDX", "SYK", "MDT", "EW", "ZTS", "HUM", "CNC",
    # 能源
    "XOM", "CVX", "COP", "EOG", "MPC", "PSX", "VLO", "SLB", "HAL", "OXY",
    # 工業
    "CAT", "DE", "BA", "HON", "UPS", "RTX", "LMT", "GE", "MMM", "EMR",
    # 航空/旅遊
    "UAL", "DAL", "AAL", "LUV", "ALK", "MAR", "IHG", "HLT", "EXPE", "BOOK"
]

class ComprehensiveRecommender:
    """綜合推薦系統"""
    
    def __init__(self):
        self.current_market = self._get_current_market()
        self.symbols = self._get_available_symbols()
        
    def _get_current_market(self):
        """根據台灣時間自動判斷當前市場"""
        # 取得台灣時間
        taipei_tz = datetime.now().astimezone()
        current_time = taipei_tz.strftime("%H:%M")
        
        # 判斷市場
        # 美股時段: 21:30 - 04:00 (次日)
        if current_time >= "21:30" or current_time < "04:00":
            return "美股"
        # 台股時段: 09:00 - 13:30
        elif current_time >= "09:00" and current_time < "13:30":
            return "台股"
        # 其他時間: 加密貨幣
        else:
            return "加密"
    
    def _is_market_open(self):
        """檢查目前是否在交易時段內"""
        taipei_tz = datetime.now().astimezone()
        current_time = taipei_tz.strftime("%H:%M")
        current_weekday = taipei_tz.weekday()  # 0=周一, 6=周日
        
        # 周末不交易
        if current_weekday >= 5:
            return False
        
        # 台股時段
        if current_time >= "09:00" and current_time < "13:30":
            return True
        
        # 美股時段 (需轉換為美股時間判斷，這裡簡化處理)
        # 美股交易時間為 21:30-04:00 (台北時間)
        if current_time >= "21:30" or current_time < "04:00":
            return True
        
        # 加密貨幣 24 小時交易
        return True
        
    def _get_available_symbols(self):
        """根據當前市場獲取可用的股票代碼"""
        # 直接返回對應市場的股票列表
        if self.current_market == "台股":
            return TAIWAN_STOCKS
        elif self.current_market == "美股":
            return US_STOCKS
        elif self.current_market == "加密":
            return CRYPTO_SYMBOLS
        return []
    
    def _fetch_realtime_data(self, symbol):
        """使用 yfinance 獲取實時數據"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="6mo")  # 獲取6個月數據用於技術分析
            
            if hist.empty or len(hist) < 30:
                return None
            
            # 計算基本技術指標
            close = hist['Close'].values
            high = hist['High'].values
            low = hist['Low'].values
            volume = hist['Volume'].values
            
            latest = hist.iloc[-1]
            prev = hist.iloc[-1] if len(hist) > 1 else latest
            
            # 計算 MA
            ma5 = float(hist['Close'].rolling(5).mean().iloc[-1]) if len(hist) >= 5 else close[-1]
            ma10 = float(hist['Close'].rolling(10).mean().iloc[-1]) if len(hist) >= 10 else close[-1]
            ma20 = float(hist['Close'].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else close[-1]
            
            # 計算 RSI (14天)
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if len(hist) >= 14 else 50
            
            # 計算 KD
            low_min = hist['Low'].rolling(9).min()
            high_max = hist['High'].rolling(9).max()
            rsv = (hist['Close'] - low_min) / (high_max - low_min) * 100
            k = rsv.rolling(3).mean()
            d = k.rolling(3).mean()
            k_value = float(k.iloc[-1]) if len(hist) >= 9 else 50
            d_value = float(d.iloc[-1]) if len(hist) >= 9 else 50
            
            # 計算 MACD
            ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
            ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_hist = macd_line - signal_line
            
            macd = float(macd_line.iloc[-1])
            signal = float(signal_line.iloc[-1])
            histogram = float(macd_hist.iloc[-1])
            
            return {
                "close": float(latest['Close']),
                "open": float(latest['Open']),
                "high": float(latest['High']),
                "low": float(latest['Low']),
                "volume": int(latest['Volume']),
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20,
                "rsi": rsi,
                "k": k_value,
                "d": d_value,
                "macd": macd,
                "signal": signal,
                "histogram": histogram
            }
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def load_sentiment(self, symbol=None):
        """載入市場情緒數據"""
        sentiment_file = DATA_DIR / "sentiment" / "latest.json"
        if not sentiment_file.exists():
            return None
            
        with open(sentiment_file, "r") as f:
            data = json.load(f)
        
        # 計算情緒分數 (0-100)
        positive = data.get("sentiments", {}).get("positive", 0)
        negative = data.get("sentiments", {}).get("negative", 0)
        total = positive + negative
        
        if total == 0:
            return 50  # 中性
        
        # 情緒比率 = (正面 - 负面) / 總數 * 100 + 50 (偏移到 0-100)
        sentiment_score = ((positive - negative) / total * 50) + 50
        return max(0, min(100, sentiment_score))
    
    def load_news(self, symbol=None):
        """載入新聞數據並評分"""
        news_file = DATA_DIR / "news" / "latest.json"
        if not news_file.exists():
            return 50
            
        with open(news_file, "r") as f:
            news_data = json.load(f)
        
        if isinstance(news_data, list):
            news_list = news_data
        else:
            news_list = news_data.get("news", [])
        
        if not news_list:
            return 50
        
        # 簡單的新聞評分：分析標題中的關鍵詞
        positive_keywords = ["漲", "上漲", "利多", "成長", "看好", "突破", "創新高", "收益", "訂單", "擴產"]
        negative_keywords = ["跌", "下跌", "利空", "衰退", "看衰", "暴跌", "虧損", "裁員", "制裁", "戰爭", "衝突"]
        
        score = 50
        for news in news_list[:10]:  # 只看前10條
            title = news.get("title", "").lower()
            
            for kw in positive_keywords:
                if kw in title:
                    score += 3
            for kw in negative_keywords:
                if kw in title:
                    score -= 3
        
        return max(0, min(100, score))
    
    def load_technical(self, symbol):
        """載入技術指標並評分"""
        # 首先嘗試從本地文件讀取
        indicator_file = DATA_DIR / "indicators" / f"{symbol}_indicators.json"
        
        if indicator_file.exists():
            try:
                with open(indicator_file, "r") as f:
                    data = json.load(f)
                latest = data.get("latest", {})
            except:
                latest = {}
        else:
            latest = {}
        
        # 如果本地沒有數據，使用 yfinance 獲取實時數據
        if not latest or not latest.get("close"):
            realtime_data = self._fetch_realtime_data(symbol)
            if realtime_data:
                latest = realtime_data
            else:
                return 50, {}
        
        # 技術指標評分
        score = 50
        details = {}
        
        # 1. MA 趨勢判斷
        ma5 = latest.get("ma5", 0)
        ma10 = latest.get("ma10", 0)
        ma20 = latest.get("ma20", 0)
        close = latest.get("close", 0)
        
        if ma5 > ma10 > ma20:
            ma_score = 80  # 多頭排列
        elif ma5 < ma10 < ma20:
            ma_score = 20  # 空頭排列
        elif ma5 > ma20:
            ma_score = 60  # 偏多
        else:
            ma_score = 40  # 偏空
        details["ma_score"] = ma_score
        
        # 2. KD 指標
        k = latest.get("k", 50)
        d = latest.get("d", 50)
        
        if k > d and k < 30:
            kd_score = 80  #黃金交叉且在超賣區
        elif k > d:
            kd_score = 65  # 黃金交叉
        elif k < d and k > 70:
            kd_score = 20  # 死亡交叉且在超買區
        elif k < d:
            kd_score = 35  # 死亡交叉
        else:
            kd_score = 50
        details["kd_score"] = kd_score
        
        # 3. MACD
        macd = latest.get("macd", 0)
        signal = latest.get("signal", 0)
        histogram = latest.get("histogram", 0)
        
        if histogram > 0 and macd > signal:
            macd_score = 75  # 多頭
        elif histogram < 0 and macd < signal:
            macd_score = 25  # 空頭
        elif histogram > 0:
            macd_score = 60
        else:
            macd_score = 40
        details["macd_score"] = macd_score
        
        # 4. RSI
        rsi = latest.get("rsi", 50)
        if rsi > 70:
            rsi_score = 30  # 超買
        elif rsi < 30:
            rsi_score = 70  # 超賣可能反彈
        elif rsi > 50:
            rsi_score = 60
        else:
            rsi_score = 40
        details["rsi_score"] = rsi_score
        
        # 計算加權技術分數 - 優化權重: 提高KD和MACD權重
        score = (ma_score * 0.20 + kd_score * 0.30 + macd_score * 0.35 + rsi_score * 0.15)
        
        return score, details
    
    def load_fundamental(self, symbol):
        """載入基本面數據並評分"""
        fundamental_file = DATA_DIR / "fundamental" / f"{symbol}_fundamental.json"
        if not fundamental_file.exists():
            return 50, {}
            
        try:
            with open(fundamental_file, "r") as f:
                data = json.load(f)
        except:
            return 50, {}
        
        score = 50
        details = {}
        
        # 處理 None 值的安全函數
        def safe_float(value, default=0):
            return float(value) if value is not None else default
        
        # 1. 本益比 (PE Ratio)
        pe = safe_float(data.get("pe_ratio", 0))
        if pe > 0:
            if pe < 15:
                pe_score = 80  # 低本益比，股價相對便宜
            elif pe < 25:
                pe_score = 60
            elif pe < 35:
                pe_score = 40
            else:
                pe_score = 20
        else:
            pe_score = 50
        details["pe_score"] = pe_score
        
        # 2. ROE
        roe = safe_float(data.get("roe", 0))
        if roe > 0.20:
            roe_score = 90
        elif roe > 0.15:
            roe_score = 75
        elif roe > 0.10:
            roe_score = 60
        elif roe > 0.05:
            roe_score = 40
        else:
            roe_score = 20
        details["roe_score"] = roe_score
        
        # 3. EPS 成長
        eps = safe_float(data.get("eps", 0))
        forward_eps = safe_float(data.get("forward_eps", 0))
        if forward_eps > eps:
            eps_score = 80
        elif eps > 10:
            eps_score = 70
        elif eps > 5:
            eps_score = 50
        else:
            eps_score = 30
        details["eps_score"] = eps_score
        
        # 4. 營收成長 (從財務數據)
        financials = data.get("financials", {})
        annual = financials.get("annual", {})
        
        if annual:
            years = sorted(annual.keys())
            if len(years) >= 2:
                try:
                    latest_revenue = annual[years[-1]].get("Total Revenue", 0)
                    prev_revenue = annual[years[-2]].get("Total Revenue", 0)
                    if prev_revenue > 0:
                        growth = (latest_revenue - prev_revenue) / prev_revenue
                        if growth > 0.3:
                            revenue_score = 90
                        elif growth > 0.15:
                            revenue_score = 75
                        elif growth > 0:
                            revenue_score = 60
                        elif growth > -0.1:
                            revenue_score = 40
                        else:
                            revenue_score = 20
                    else:
                        revenue_score = 50
                except:
                    revenue_score = 50
            else:
                revenue_score = 50
        else:
            revenue_score = 50
        details["revenue_score"] = revenue_score
        
        # 計算加權基本面分數
        score = pe_score * 0.25 + roe_score * 0.30 + eps_score * 0.20 + revenue_score * 0.25
        
        return score, details
    
    def load_chips(self, symbol):
        """載入籌碼數據並評分"""
        chips_file = DATA_DIR / "chips" / f"{symbol}_chips.json"
        if not chips_file.exists():
            return 50, {}
            
        try:
            with open(chips_file, "r") as f:
                data = json.load(f)
        except:
            return 50, {}
        
        institutional = data.get("institutional", {})
        shareholding = data.get("shareholding", {})
        concentration = data.get("concentration", {})
        
        if institutional or shareholding or concentration:
            # 有數據時的評分邏輯
            score = 50  # 暫時設為中性
        else:
            # 沒有數據時，嘗試從技術指標中的成交量來推斷
            indicator_file = DATA_DIR / "indicators" / f"{symbol}_indicators.json"
            try:
                with open(indicator_file, "r") as f:
                    ind_data = json.load(f)
                
                latest = ind_data.get("latest", {})
                volume = latest.get("volume", 0)
                avg_volume = latest.get("volume", 1)  # 如果沒有平均成交量，用當前成交量
                
                # 簡單的成交量評分
                if volume > avg_volume * 1.5:
                    score = 70  # 量增，可能有主力進貨
                elif volume > avg_volume:
                    score = 60
                elif volume > avg_volume * 0.7:
                    score = 50
                else:
                    score = 40
            except:
                score = 50
        
        return score, {"source": "volume_inference"}
    
    def calculate_total_score(self, sentiment, news, technical, fundamental, chips):
        """計算綜合評分"""
        # 優化權重: 情緒 10% + 新聞 10% + 技術 40% + 基本面 20% + 籌碼 20%
        # 原因: 技術指標和籌碼更能反映短期走勢,情緒/新聞波動太大
        total = (sentiment * 0.10 + 
                news * 0.10 + 
                technical * 0.40 + 
                fundamental * 0.20 + 
                chips * 0.20)
        return round(total, 1)
    
    def get_signal(self, score):
        """根據分數給出信號 - 優化閾值提高勝率"""
        # 提高閾值: 只在更高確定性時買入,減少噪音交易
        if score >= 72:
            return "BUY"
        elif score >= 60:
            return "HOLD"
        elif score >= 45:
            return "NEUTRAL"
        else:
            return "SELL"
    
    def generate_reason(self, factors):
        """生成推薦理由"""
        reasons = []
        
        if factors.get("technical", 0) >= 65:
            if factors.get("kd_score", 0) >= 65:
                reasons.append("KD黃金交叉")
            if factors.get("macd_score", 0) >= 60:
                reasons.append("MACD正向")
            if factors.get("ma_score", 0) >= 60:
                reasons.append("MA多頭排列")
        
        if factors.get("sentiment", 0) >= 60:
            reasons.append("市場情緒正向")
        
        if factors.get("news", 0) >= 60:
            reasons.append("新聞利好")
        
        if factors.get("fundamental", 0) >= 70:
            if factors.get("roe_score", 0) >= 70:
                reasons.append("ROE優異")
            if factors.get("revenue_score", 0) >= 70:
                reasons.append("營收成長強勁")
        
        if factors.get("chips", 0) >= 60:
            reasons.append("籌碼穩定")
        
        if not reasons:
            return "觀望為主"
        
        return "+".join(reasons[:3])
    
    def recommend(self, symbol):
        """對單一股票進行推薦"""
        # 載入各項數據
        sentiment = self.load_sentiment(symbol) or 50
        news = self.load_news(symbol) or 50
        technical, tech_details = self.load_technical(symbol)
        fundamental, fund_details = self.load_fundamental(symbol)
        chips, chips_details = self.load_chips(symbol)
        
        # 計算總分
        total_score = self.calculate_total_score(sentiment, news, technical, fundamental, chips)
        
        # 獲取信號
        signal = self.get_signal(total_score)
        
        # 收集所有因素詳情
        all_factors = {
            "sentiment": round(sentiment, 1),
            "news": round(news, 1),
            "technical": round(technical, 1),
            "fundamental": round(fundamental, 1),
            "chips": round(chips, 1),
            **tech_details,
            **fund_details,
            **chips_details
        }
        
        # 生成理由
        reason = self.generate_reason(all_factors)
        
        return {
            "symbol": symbol,
            "score": total_score,
            "signal": signal,
            "factors": all_factors,
            "reason": reason
        }
    
    def recommend_all(self, limit=100):
        """對當前市場的所有股票進行推薦"""
        taipei_tz = datetime.now().astimezone()
        recommendations = []
        
        # 根據市場設定掃描數量
        if self.current_market == "加密":
            scan_count = min(len(self.symbols), 10)  # 加密貨幣只推薦10檔
        else:
            scan_count = min(len(self.symbols), limit)  # 美股/台股推薦100檔
        
        for symbol in self.symbols[:scan_count]:
            try:
                rec = self.recommend(symbol)
                recommendations.append(rec)
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
        
        # 按分數排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "market": self.current_market,
            "scan_count": scan_count,
            "total_available": len(self.symbols),
            "current_time": taipei_tz.strftime("%Y-%m-%d %H:%M:%S"),
            "recommendations": recommendations,
            "timestamp": json.dumps({"generated_at": taipei_tz.isoformat()})
        }

def main():
    """主函數"""
    recommender = ComprehensiveRecommender()
    
    print("=" * 60)
    print("📊 綜合推薦系統 (Comprehensive Recommendation System)")
    print("=" * 60)
    
    # 顯示當前市場
    market = recommender.current_market
    print(f"\n🌐 當前市場: {market}")
    
    # 顯示對應時段
    taipei_time = datetime.now().astimezone().strftime("%H:%M")
    if market == "台股":
        print(f"⏰ 台北時間: {taipei_time} (台股盤中 09:00-13:30)")
        print(f"📊 掃描標的數量: 100檔台股")
    elif market == "美股":
        print(f"⏰ 台北時間: {taipei_time} (美股盤前+盤後+盤中 21:30-04:00)")
        print(f"📊 掃描標的數量: 100檔美股")
    else:
        print(f"⏰ 台北時間: {taipei_time} (加密貨幣 24小時)")
        print(f"📊 掃描標的數量: 10檔加密貨幣")
    
    print("-" * 40)
    
    # 測試單一股票
    test_symbol = recommender.symbols[0] if recommender.symbols else "2330.TW"
    print(f"\n📈 測試個股: {test_symbol}")
    print("-" * 40)
    
    result = recommender.recommend(test_symbol)
    print(f"代碼: {result['symbol']}")
    print(f"總分: {result['score']}")
    print(f"信號: {result['signal']}")
    print(f"理由: {result['reason']}")
    print("\n各項分數:")
    for key, value in result['factors'].items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value}")
    
    # 全部股票推薦
    print("\n" + "=" * 60)
    print(f"📈 {market} 推薦排名 (Top 10)")
    print("=" * 60)
    
    # 設定推薦數量
    if market == "加密":
        limit = 10
    else:
        limit = 100
    
    all_results = recommender.recommend_all(limit=limit)
    
    for i, rec in enumerate(all_results["recommendations"][:10], 1):
        print(f"{i}. {rec['symbol']} | 分數: {rec['score']} | 信號: {rec['signal']} | {rec['reason']}")
    
    # 輸出 JSON 格式
    print("\n" + "=" * 60)
    print("📄 JSON 輸出 (Top 20)")
    print("=" * 60)
    output = all_results.copy()
    output["recommendations"] = output["recommendations"][:20]
    print(json.dumps(output, indent=2, ensure_ascii=False))
    
    return all_results

if __name__ == "__main__":
    main()
