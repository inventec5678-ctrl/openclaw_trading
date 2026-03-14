"""
即時報價 API 服務
支援：Yahoo Finance (yfinance)、台灣證券交易所、加密貨幣、原物料
"""

from flask import Flask, jsonify, request, Response, send_file, render_template_string
import yfinance as yf
from datetime import datetime, timezone
import requests
import json
import os
import sqlite3
import csv
import io
from collections import defaultdict

# 嘗試導入 PDF 庫
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

app = Flask(__name__)

# 首頁 - 顯示所有股票報價、買賣訊號、分數
@app.route('/')
def index():
    import random
    
    # 載入股票數據
    DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'louie_realtime_winrate.json')
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stocks = data.get('stocks', [])
    except Exception as e:
        stocks = []
        print(f"載入數據錯誤: {e}")
    
    # 處理每支股票
    STOCKS = []
    for s in stocks:
        sym = s.get('symbol', '')
        current_price = s.get('current_price', 0)
        
        # 計算分數
        win_rate = s.get('win_rate', 0)
        trades = s.get('trades', 0)
        score = min(100, int(win_rate * 0.7 + min(trades, 50) * 0.6))
        
        # 買賣訊號
        if score >= 70:
            signal = "買入"
            signal_class = "buy"
        elif score >= 40:
            signal = "觀望"
            signal_class = "hold"
        else:
            signal = "賣出"
            signal_class = "sell"
        
        # 漲跌
        change = s.get('change', random.uniform(-3, 3))
        
        # 支撐/壓力
        support = round(current_price * 0.95, 2) if current_price > 0 else 0
        resistance = round(current_price * 1.05, 2) if current_price > 0 else 0
        
        STOCKS.append({
            'symbol': sym.replace('.TW', ''),
            'current_price': current_price,
            'change': change,
            'score': score,
            'signal': signal,
            'signal_class': signal_class,
            'win_rate': win_rate,
            'trades': trades,
            'support': support,
            'resistance': resistance
        })
    
    # 按分數排序
    STOCKS.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 統計
    overall_win_rate = data.get('overall_win_rate', 0)
    total_signals = data.get('total_signals', 0)
    high_winrate_count = len([s for s in STOCKS if s.get('win_rate', 0) >= 70])
    
    # 產生股票卡片 HTML
    cards_html = ""
    for s in STOCKS:
        change_class = "positive" if s["change"] >= 0 else "negative"
        sign = "+" if s["change"] >= 0 else ""
        cards_html += f"""
        <div class="card">
            <div class="signal-badge {s['signal_class']}">{s['signal']}</div>
            <div class="card-header">
                <div class="stock-icon">{s['symbol'][:2]}</div>
                <div class="stock-symbol">{s['symbol']}</div>
            </div>
            <div class="price-row">
                <div class="price">${s['current_price']:,.2f}</div>
                <div class="change-val {change_class}">{sign}{s['change']:.2f}%</div>
            </div>
            <div class="key-metrics">
                <div class="key-metric">
                    <div class="key-metric-label">分數</div>
                    <div class="key-metric-value score">{s['score']}</div>
                </div>
                <div class="key-metric">
                    <div class="key-metric-label">買賣訊號</div>
                    <div class="key-metric-value {s['signal_class']}">{s['signal']}</div>
                </div>
                <div class="key-metric">
                    <div class="key-metric-label">支撐</div>
                    <div class="key-metric-value support">${s['support']:,.2f}</div>
                </div>
                <div class="key-metric">
                    <div class="key-metric-label">壓力</div>
                    <div class="key-metric-value resistance">${s['resistance']:,.2f}</div>
                </div>
                <div class="key-metric">
                    <div class="key-metric-label">勝率</div>
                    <div class="key-metric-value winrate">{s['win_rate']:.1f}%</div>
                </div>
                <div class="key-metric">
                    <div class="key-metric-label">交易次數</div>
                    <div class="key-metric-value">{s['trades']}</div>
                </div>
            </div>
        </div>
        """
    
    html = f'''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ray 即時報價系統</title>
        <meta http-equiv="refresh" content="30">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
                min-height: 100vh;
                padding: 30px 20px;
            }}
            .signal-badge {{
                position: absolute;
                top: 16px;
                right: 16px;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 700;
                font-family: 'JetBrains Mono', monospace;
            }}
            .signal-badge.buy {{
                background: rgba(16, 185, 129, 0.25);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.4);
            }}
            .signal-badge.hold {{
                background: rgba(245, 158, 11, 0.25);
                color: #f59e0b;
                border: 1px solid rgba(245, 158, 11, 0.4);
            }}
            .signal-badge.sell {{
                background: rgba(239, 68, 68, 0.25);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.4);
            }}
            .header-stats {{
                display: flex;
                justify-content: center;
                gap: 24px;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }}
            .stat-box {{
                background: linear-gradient(145deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.95));
                backdrop-filter: blur(20px);
                border-radius: 14px;
                padding: 16px 24px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.1);
            }}
            .stat-label {{ font-size: 12px; color: #9ca3af; margin-bottom: 6px; }}
            .stat-value {{ font-size: 24px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
            .stat-value.green {{ color: #10b981; }}
            .stat-value.orange {{ color: #f59e0b; }}
            .stat-value.purple {{ color: #8b5cf6; }}
            h1 {{
                text-align: center;
                color: #fff;
                margin-bottom: 20px;
                font-size: 24px;
                font-weight: 700;
            }}
            .subtitle {{ 
                text-align: center; 
                color: #6b7280; 
                font-size: 13px; 
                margin-top: -15px; 
                margin-bottom: 25px; 
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 16px;
                max-width: 1400px;
                margin: 0 auto;
            }}
            .card {{
                background: linear-gradient(145deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.95));
                backdrop-filter: blur(20px);
                border-radius: 18px;
                padding: 20px;
                box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.08);
                position: relative;
                transition: transform 0.2s;
            }}
            .card:hover {{ transform: translateY(-4px); }}
            .card-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
            .stock-icon {{
                width: 40px; height: 40px;
                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 14px; color: #fff; font-weight: 700;
            }}
            .stock-symbol {{ font-size: 18px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
            .price-row {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 14px; }}
            .price {{ font-size: 26px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
            .change-val {{ 
                padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 12px;
                font-family: 'JetBrains Mono', monospace;
            }}
            .positive {{ color: #10b981; }}
            .negative {{ color: #ef4444; }}
            .key-metrics {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }}
            .key-metric {{
                background: rgba(255,255,255,0.05);
                border-radius: 10px;
                padding: 10px;
                text-align: center;
            }}
            .key-metric-label {{ font-size: 10px; color: #9ca3af; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
            .key-metric-value {{ font-size: 16px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
            .key-metric-value.score {{ color: #3b82f6; }}
            .key-metric-value.support {{ color: #10b981; }}
            .key-metric-value.resistance {{ color: #ef4444; }}
            .key-metric-value.winrate {{ color: #8b5cf6; }}
            .key-metric-value.buy {{ color: #10b981; }}
            .key-metric-value.hold {{ color: #f59e0b; }}
            .key-metric-value.sell {{ color: #ef4444; }}
            .footer {{
                text-align: center;
                color: #6b7280;
                font-size: 12px;
                margin-top: 30px;
                padding: 15px;
            }}
            .auto-refresh {{
                display: inline-block;
                background: rgba(59, 130, 246, 0.2);
                padding: 4px 12px;
                border-radius: 12px;
                margin-left: 10px;
                font-size: 11px;
                color: #3b82f6;
            }}
            @media (max-width: 768px) {{
                body {{ padding: 20px 12px; }}
                .grid {{ grid-template-columns: 1fr; }}
                .header-stats {{ gap: 12px; }}
                .stat-box {{ padding: 12px 16px; }}
            }}
        </style>
    </head>
    <body>
        <h1>📈 Ray 即時報價系統</h1>
        <p class="subtitle">依分數排序 · 顯示代碼/分數/買賣訊號/支撐/壓力</p>
        
        <div class="header-stats">
            <div class="stat-box">
                <div class="stat-label">整體勝率</div>
                <div class="stat-value green">{overall_win_rate:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">追蹤標的</div>
                <div class="stat-value orange">{len(STOCKS)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">高勝率標的</div>
                <div class="stat-value purple">{high_winrate_count}</div>
            </div>
        </div>
        
        <div class="grid">
            {cards_html}
        </div>
        
        <div class="footer">
            更新時間: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''
            <span class="auto-refresh">自動更新 30秒</span>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

# 舊的首頁 - 顯示進場/退場訊號（保留作為 /signal 路由）
@app.route('/signal')
def signal_page():
    html = '''
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ray 信號中心</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                text-align: center;
                padding: 40px;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
            }
            h1 {
                color: #fff;
                font-size: 2.5rem;
                margin-bottom: 30px;
            }
            .signal {
                font-size: 4rem;
                font-weight: bold;
                padding: 20px 60px;
                border-radius: 15px;
                display: inline-block;
            }
            .signal-entry {
                background: linear-gradient(135deg, #00c853, #69f0ae);
                color: #fff;
                box-shadow: 0 10px 30px rgba(0,200,83,0.4);
            }
            .signal-exit {
                background: linear-gradient(135deg, #ff5252, #ff8a80);
                color: #fff;
                box-shadow: 0 10px 30px rgba(255,82,82,0.4);
            }
            .signal-hold {
                background: linear-gradient(135deg, #ffd54f, #ffca28);
                color: #333;
                box-shadow: 0 10px 30px rgba(255,213,79,0.4);
            }
            .timestamp {
                color: rgba(255,255,255,0.6);
                margin-top: 30px;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📈 Ray 信號中心</h1>
            <div class="signal signal-entry">🚀 進場</div>
            <div class="timestamp">更新時間: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

# 數據目錄
DATA_DIR = os.path.expanduser("~/openclaw_data/stocks")

# 台灣證券交易所 API
TWSE_API = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"

def get_timestamp():
    """取得 ISO 格式時間戳"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def format_quote(symbol, data):
    """格式化報價數據為統一格式"""
    try:
        price = float(data.get('currentPrice', 0))
        prev_close = float(data.get('previousClose', price))
        change = price - prev_close
        change_percent = (change / prev_close * 100) if prev_close > 0 else 0
        volume = int(data.get('volume', 0))
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": volume,
            "timestamp": get_timestamp()
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "error": str(e),
            "timestamp": get_timestamp()
        }

def get_google_finance_quote(symbol):
    """使用 Google Finance 取得報價"""
    try:
        # 移除常見後綴
        clean_symbol = symbol.replace(".TW", "").replace("-USD", "").replace("=F", "")
        
        # 判斷交易所
        if symbol.endswith(".TW"):
            # 台股使用不同格式: 2330:TWSE
            exchange = "TWSE"
            google_symbol = f"{clean_symbol}:{exchange}"
        elif symbol.endswith("-USD"):
            # 加密貨幣: BTC-USD -> BTC:USD
            google_symbol = f"{clean_symbol}:USD"
        elif "=F" in symbol:
            # 原物料: CL=F -> CL:NYSE
            # 常見對應關係
            commodity_map = {"GC": "COMEX", "SI": "COMEX", "CL": "NYMEX", "HG": "COMEX"}
            exchange = commodity_map.get(clean_symbol, "NYSE")
            google_symbol = f"{clean_symbol}:{exchange}"
        else:
            # 美股: AAPL -> AAPL:NASDAQ
            # 假設為 NASDAQ，可擴展
            google_symbol = f"{clean_symbol}:NASDAQ"
        
        # 使用 Google Finance API
        url = f"https://www.google.com/finance/quote/{google_symbol}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 解析 HTML 獲取報價數據
            html = response.text
            
            # 查找價格
            import re
            
            # 嘗試找股價
            price_match = re.search(r'"cWwKGe">([0-9,]+\.?[0-9]*)', html)
            if not price_match:
                price_match = re.search(r'class="ymEaK">([0-9,]+\.?[0-9]*)', html)
            
            if price_match:
                price = float(price_match.group(1).replace(",", ""))
                
                # 找漲跌
                change_match = re.search(r'class="gE3vGe">([+-]?[0-9,]+\.?[0-9]*)', html)
                change_percent_match = re.search(r'class="bAaXzD">([+-]?[0-9,]+\.?[0-9]*)%', html)
                
                change = 0
                change_percent = 0
                
                if change_percent_match:
                    change_percent = float(change_percent_match.group(1).replace(",", ""))
                
                # 找成交量
                volume_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:股|shares|Shares)', html)
                volume = 0
                if volume_match:
                    volume = int(volume_match.group(1).replace(",", ""))
                
                return {
                    "currentPrice": price,
                    "previousClose": price - (price * change_percent / 100) if change_percent != 0 else price,
                    "volume": volume,
                    "changePercent": change_percent
                }
        
        # 如果解析失敗，嘗試備用方法
        return get_google_finance_fallback(symbol)
        
    except Exception as e:
        # 回退到備用方法
        return get_google_finance_fallback(symbol)

def get_google_finance_fallback(symbol):
    """Google Finance 備用方法 (直接解析頁面)"""
    try:
        clean_symbol = symbol.replace(".TW", "").replace("-USD", "").replace("=F", "")
        
        if symbol.endswith(".TW"):
            url = f"https://www.google.com/finance/quote/{clean_symbol}:TWSE"
        elif symbol.endswith("-USD"):
            url = f"https://www.google.com/finance/quote/{clean_symbol}:USD"
        elif "=F" in symbol:
            url = f"https://www.google.com/finance/quote/{clean_symbol}:NYSE"
        else:
            url = f"https://www.google.com/finance/quote/{clean_symbol}:NASDAQ"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # 使用更簡單的正則表達式
            import re
            
            # 找價格 - 多種模式嘗試
            patterns = [
                r'"cWwKGe">([0-9,]+\.?[0-9]*)',
                r'data-price="([0-9,]+\.?[0-9]*)"',
                r'>(\d{1,3}(?:,\d{3})*(?:\.\d+)?)<.*?price',
            ]
            
            price = None
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    price = float(match.group(1).replace(",", ""))
                    break
            
            if price:
                # 嘗試找漲跌百分比
                change_match = re.search(r'([+-]?\d+\.?\d*)%', html)
                change_percent = float(change_match.group(1)) if change_match else 0
                
                return {
                    "currentPrice": price,
                    "previousClose": price,
                    "volume": 0,
                    "changePercent": change_percent
                }
        
        return {"error": "無法從 Google Finance 取得數據"}
        
    except Exception as e:
        return {"error": str(e)}

def get_yahoo_quote(symbol):
    """使用 yfinance 取得報價 (備用)"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        
        return {
            "currentPrice": info.last_price,
            "previousClose": info.previous_close,
            "volume": info.last_volume or 0
        }
    except Exception as e:
        # 嘗試備用方法
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                return {
                    "currentPrice": latest['Close'],
                    "previousClose": prev['Close'],
                    "volume": int(latest['Volume'])
                }
        except:
            pass
        return {"error": str(e)}

def get_twse_quote(symbol, date_str=None):
    """取得台灣證券交易所報價"""
    try:
        if date_str is None:
            today = datetime.now()
            date_str = today.strftime("%Y%m%d")
        
        # 去掉 .TW 後綴
        stock_code = symbol.replace(".TW", "")
        
        params = {
            "stockNo": stock_code,
            "date": date_str,
            "response": "json"
        }
        
        response = requests.get(TWSE_API, params=params, timeout=10)
        data = response.json()
        
        if data.get("stat") == "OK":
            rows = data.get("data", [])
            if rows:
                latest = rows[-1]
                # 收盤價在第7欄 (index 6)
                close_price = float(latest[6].replace(",", ""))
                # 成交量在第2欄 (index 1)
                volume = int(latest[1].replace(",", ""))
                # 取得前一天收盤價來計算漲跌 (收盤價 - 漲跌價差)
                change_str = latest[7].strip()
                if change_str and change_str not in ['X0.00', '0.00', 'X 0.00']:
                    try:
                        change = float(change_str.replace("+", "").replace("-", ""))
                        prev_close = close_price - change
                    except:
                        prev_close = close_price
                else:
                    prev_close = close_price
                return {
                    "currentPrice": close_price,
                    "previousClose": prev_close,
                    "volume": volume
                }
        
        return {"error": "無法取得TWSE數據"}
    except Exception as e:
        return {"error": str(e)}

# ============ API Endpoints ============

@app.route('/api/quote', methods=['GET'])
def get_quote():
    """取得單一報價"""
    symbol = request.args.get('symbol', '2330.TW')
    
    # 判斷數據源 - 優先使用 Google Finance
    if symbol.endswith('.TW'):
        # 台灣股票 - 嘗試 Google Finance 再試 TWSE
        raw_data = get_google_finance_quote(symbol)
        if "error" in raw_data:
            raw_data = get_twse_quote(symbol)
    else:
        # 美股、加密貨幣、原物料 - 嘗試 Google Finance 再用 Yahoo
        raw_data = get_google_finance_quote(symbol)
        if "error" in raw_data:
            raw_data = get_yahoo_quote(symbol)
    
    if "error" in raw_data:
        return jsonify({"error": raw_data["error"], "symbol": symbol}), 400
    
    return jsonify(format_quote(symbol, raw_data))

@app.route('/api/quotes', methods=['GET'])
def get_quotes():
    """取得多個報價"""
    symbols = request.args.get('symbols', '').split(',')
    if not symbols or symbols == ['']:
        # 預設報價列表
        symbols = ['2330.TW', 'BTC-USD', 'ETH-USD', 'SOL-USD', 'GC=F', 'SI=F', 'CL=F']
    
    results = []
    for symbol in symbols:
        symbol = symbol.strip()
        if not symbol:
            continue
            
        # 優先使用 Google Finance
        if symbol.endswith('.TW'):
            raw_data = get_google_finance_quote(symbol)
            if "error" in raw_data:
                raw_data = get_twse_quote(symbol)
        else:
            raw_data = get_google_finance_quote(symbol)
            if "error" in raw_data:
                raw_data = get_yahoo_quote(symbol)
        
        if "error" not in raw_data:
            results.append(format_quote(symbol, raw_data))
        else:
            results.append({"symbol": symbol, "error": raw_data["error"]})
    
    return jsonify({
        "quotes": results,
        "timestamp": get_timestamp()
    })

@app.route('/api/stocks/tw', methods=['GET'])
def get_tw_stocks():
    """取得台灣個股報價"""
    symbol = request.args.get('symbol', '2330.TW')
    raw_data = get_twse_quote(symbol)
    
    if "error" in raw_data:
        return jsonify({"error": raw_data["error"]}), 400
    
    return jsonify(format_quote(symbol, raw_data))

@app.route('/api/crypto', methods=['GET'])
def get_crypto():
    """取得加密貨幣報價"""
    cryptos = ['BTC-USD', 'ETH-USD', 'SOL-USD']
    results = []
    
    for symbol in cryptos:
        raw_data = get_google_finance_quote(symbol)
        if "error" in raw_data:
            raw_data = get_yahoo_quote(symbol)
        if "error" not in raw_data:
            results.append(format_quote(symbol, raw_data))
    
    return jsonify({
        "type": "crypto",
        "quotes": results,
        "timestamp": get_timestamp()
    })

@app.route('/api/commodities', methods=['GET'])
def get_commodities():
    """取得原物料報價"""
    commodities = ['GC=F', 'SI=F', 'CL=F']  # 黃金、白銀、原油
    results = []
    
    for symbol in commodities:
        raw_data = get_google_finance_quote(symbol)
        if "error" in raw_data:
            raw_data = get_yahoo_quote(symbol)
        if "error" not in raw_data:
            results.append(format_quote(symbol, raw_data))
    
    return jsonify({
        "type": "commodities",
        "quotes": results,
        "timestamp": get_timestamp()
    })

@app.route('/health', methods=['GET'])
def health():
    """健康檢查"""
    return jsonify({"status": "ok", "timestamp": get_timestamp()})

# ============ 即時分析 API ============

@app.route('/api/analyze', methods=['GET'])
def analyze_symbol():
    """即時分析單一標的"""
    symbol = request.args.get('symbol', '2330.TW')
    period = request.args.get('period', '3mo')
    
    try:
        # 初始化分析
        analysis = RealtimeAnalysis(symbol, period)
        
        # 1. 支撐位/壓力位
        sr = analysis.calculate_support_resistance()
        
        # 2. 進場時間建議
        timing = analysis.get_entry_timing()
        
        # 3. 風險評估
        risk = analysis.get_risk_assessment()
        
        return jsonify({
            "symbol": symbol,
            "timestamp": get_timestamp(),
            "support_resistance": sr,
            "entry_timing": timing,
            "risk_assessment": risk
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/api/macd', methods=['GET'])
def get_macd():
    """取得 MACD 指標分析"""
    symbol = request.args.get('symbol', '2330.TW')
    period = request.args.get('period', '3mo')
    fast = int(request.args.get('fast', 12))
    slow = int(request.args.get('slow', 26))
    signal = int(request.args.get('signal', 9))
    
    try:
        analysis = RealtimeAnalysis(symbol, period)
        macd_data = analysis.calculate_macd(fast=fast, slow=slow, signal=signal)
        
        return jsonify({
            "symbol": symbol,
            "timestamp": get_timestamp(),
            "params": {"fast": fast, "slow": slow, "signal": signal},
            **macd_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/api/ma', methods=['GET'])
def get_ma():
    """取得 MA (移動平均線) 指標分析"""
    symbol = request.args.get('symbol', '2330.TW')
    period = request.args.get('period', '3mo')
    short_period = int(request.args.get('short', 20))
    long_period = int(request.args.get('long', 60))
    
    try:
        analysis = RealtimeAnalysis(symbol, period)
        ma_data = analysis.calculate_ma(short_period=short_period, long_period=long_period)
        
        return jsonify({
            "symbol": symbol,
            "timestamp": get_timestamp(),
            "params": {"short_period": short_period, "long_period": long_period},
            **ma_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/api/kd', methods=['GET'])
def get_kd():
    """取得 KD (隨機指標) 分析"""
    symbol = request.args.get('symbol', '2330.TW')
    period = request.args.get('period', '3mo')
    n = int(request.args.get('n', 9))
    m1 = int(request.args.get('m1', 3))
    m2 = int(request.args.get('m2', 3))
    oversold = int(request.args.get('oversold', 20))
    overbought = int(request.args.get('overbought', 80))
    
    try:
        analysis = RealtimeAnalysis(symbol, period)
        kd_data = analysis.calculate_kd(n=n, m1=m1, m2=m2, oversold=oversold, overbought=overbought)
        
        return jsonify({
            "symbol": symbol,
            "timestamp": get_timestamp(),
            "params": {"n": n, "m1": m1, "m2": m2, "oversold": oversold, "overbought": overbought},
            **kd_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/api/sar', methods=['GET'])
def get_sar():
    """取得 SAR (拋物線轉向指標) 分析"""
    symbol = request.args.get('symbol', '2330.TW')
    period = request.args.get('period', '3mo')
    af_start = float(request.args.get('af_start', 0.02))
    af_max = float(request.args.get('af_max', 0.2))
    af_increment = float(request.args.get('af_increment', 0.02))
    
    try:
        analysis = RealtimeAnalysis(symbol, period)
        sar_data = analysis.calculate_sar(af_start=af_start, af_max=af_max, af_increment=af_increment)
        
        return jsonify({
            "symbol": symbol,
            "timestamp": get_timestamp(),
            "params": {"af_start": af_start, "af_max": af_max, "af_increment": af_increment},
            **sar_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/api/adx', methods=['GET'])
def get_adx():
    """取得 ADX (Average Directional Index) 分析"""
    symbol = request.args.get('symbol', '2330.TW')
    period = request.args.get('period', '3mo')
    adx_period = int(request.args.get('period', 14))
    threshold = int(request.args.get('threshold', 25))
    
    try:
        analysis = RealtimeAnalysis(symbol, period)
        adx_data = analysis.calculate_adx(period=adx_period, adx_threshold=threshold)
        
        return jsonify({
            "symbol": symbol,
            "timestamp": get_timestamp(),
            "params": {"adx_period": adx_period, "threshold": threshold},
            **adx_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/api/rsi', methods=['GET'])
def get_rsi():
    """取得 RSI (相對強弱指標) 分析"""
    symbol = request.args.get('symbol', '2330.TW')
    period = request.args.get('period', '3mo')
    rsi_period = int(request.args.get('rsi_period', 14))
    oversold = int(request.args.get('oversold', 30))
    overbought = int(request.args.get('overbought', 70))
    
    try:
        analysis = RealtimeAnalysis(symbol, period)
        rsi_data = analysis.calculate_rsi(period=rsi_period, oversold=oversold, overbought=overbought)
        
        return jsonify({
            "symbol": symbol,
            "timestamp": get_timestamp(),
            "params": {"rsi_period": rsi_period, "oversold": oversold, "overbought": overbought},
            **rsi_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500

@app.route('/api/recommend', methods=['GET'])
def recommend_targets():
    """推薦最佳標的 (使用綜合推薦系統)"""
    # 取得 symbols 參數
    symbols_param = request.args.get('symbols', '')
    
    # 根據市場類型設定默認推薦數量
    # 台股/美股: 100檔, 加密貨幣: 10檔
    recommender = ComprehensiveRecommender()
    if recommender.current_market == "加密":
        default_limit = 10
    else:
        default_limit = 100
    
    limit = int(request.args.get('limit', default_limit))
    
    try:
        # 使用綜合推薦系統
        recommender = ComprehensiveRecommender()
        
        if symbols_param:
            # 針對特定股票進行推薦
            symbols = [s.strip() for s in symbols_param.split(',') if s.strip()]
            results = []
            for symbol in symbols:
                try:
                    rec = recommender.recommend(symbol)
                    results.append(rec)
                except Exception as e:
                    results.append({"symbol": symbol, "error": str(e)})
            
            # 按分數排序
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # 分類 - 改進推薦邏輯，返回 Top Picks
            recommended = [r for r in results if r.get('signal') == 'BUY']
            watchlist = [r for r in results if r.get('signal') in ['HOLD', 'NEUTRAL']]
            
            # 如果沒有 BUY 信號，返回分數最高的作為 Top Picks
            if not recommended and results:
                top_picks = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:5]
                recommendations = top_picks
            else:
                recommendations = recommended[:limit] if recommended else []
            
            top_pick = recommended[0] if recommended else (results[0] if results else None)
            
            return jsonify({
                "timestamp": get_timestamp(),
                "market": recommender.current_market,
                "total_scanned": len(symbols),
                "recommendations": recommendations,
                "top_picks": sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:5] if results else [],
                "watchlist": watchlist[:limit],
                "all_results": results,
                "summary": {
                    "buy_count": len(recommended),
                    "hold_count": len(watchlist),
                    "top_pick": top_pick
                }
            })
        else:
            # 對當前市場所有股票進行推薦
            # 台股時段推薦100檔台股，美股時段推薦100檔美股，加密貨幣時段推薦10檔
            if recommender.current_market == "加密":
                scan_limit = 10
            else:
                scan_limit = 100
            
            all_results = recommender.recommend_all(limit=scan_limit)
            
            # 解析 JSON timestamp
            if isinstance(all_results.get("timestamp"), str):
                import json
                timestamp_data = json.loads(all_results["timestamp"])
                all_results["generated_at"] = timestamp_data.get("generated_at")
                del all_results["timestamp"]
            
            # 分類 - 改進推薦邏輯，返回 Top Picks（無論信號是什麼）
            recommendations = all_results.get("recommendations", [])
            recommended = [r for r in recommendations if r.get('signal') == 'BUY']
            watchlist = [r for r in recommendations if r.get('signal') in ['HOLD', 'NEUTRAL']]
            
            # 如果沒有 BUY 信號，返回分數最高的作為 Top Picks
            if not recommended and recommendations:
                # 取分數最高的 5 檔作為推薦
                top_picks = sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True)[:5]
                all_results["recommendations"] = top_picks
                all_results["top_picks"] = top_picks
            else:
                all_results["recommendations"] = recommended[:limit] if recommended else []
                all_results["top_picks"] = recommended[:5] if recommended else []
            
            all_results["watchlist"] = watchlist[:limit]
            all_results["summary"] = {
                "buy_count": len(recommended),
                "hold_count": len(watchlist),
                "top_pick": all_results["top_picks"][0] if all_results.get("top_picks") else (recommended[0] if recommended else (recommendations[0] if recommendations else None))
            }
            all_results["timestamp"] = get_timestamp()
            
            return jsonify(all_results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ Backtest API ============
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

# 策略 Import
import sys
quant_path = "/Users/changrunlin/openclaw_quant"
sys.path.insert(0, quant_path)
from data_loader import StockDataLoader
from backtest import BacktestEngine

# 即時分析 Import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 添加上層目錄以導入 comprehensive_recommender
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)
from realtime_analysis import RealtimeAnalysis
from comprehensive_recommender import ComprehensiveRecommender

# SQLite 資料庫路徑
BACKTEST_DB = os.path.expanduser("~/.openclaw_workspace/backtest_history.db")

def init_backtest_db():
    """初始化回測歷史資料庫"""
    os.makedirs(os.path.dirname(BACKTEST_DB), exist_ok=True)
    conn = sqlite3.connect(BACKTEST_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            params TEXT NOT NULL,
            total_return REAL,
            annualized_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            win_rate REAL,
            total_trades INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_backtest_db()

def get_strategies():
    """取得可用策略"""
    return {
        "ma": {
            "name": "均線策略",
            "params": {
                "short_period": {"type": "number", "default": 20, "min": 5, "max": 60, "label": "短期MA週期"},
                "long_period": {"type": "number", "default": 60, "min": 20, "max": 250, "label": "長期MA週期"}
            }
        },
        "kd": {
            "name": "KD策略",
            "params": {
                "n": {"type": "number", "default": 9, "min": 5, "max": 20, "label": "RSV週期"},
                "m1": {"type": "number", "default": 3, "min": 1, "max": 10, "label": "K平滑週期"},
                "m2": {"type": "number", "default": 3, "min": 1, "max": 10, "label": "D平滑週期"},
                "oversold": {"type": "number", "default": 20, "min": 10, "max": 30, "label": "超賣門檻"},
                "overbought": {"type": "number", "default": 80, "min": 70, "max": 90, "label": "超買門檻"}
            }
        },
        "macd": {
            "name": "MACD策略",
            "params": {
                "fast": {"type": "number", "default": 12, "min": 5, "max": 30, "label": "快線週期"},
                "slow": {"type": "number", "default": 26, "min": 15, "max": 50, "label": "慢線週期"},
                "signal": {"type": "number", "default": 9, "min": 5, "max": 20, "label": "訊號線週期"}
            }
        },
        "rsi": {
            "name": "RSI策略",
            "params": {
                "period": {"type": "number", "default": 14, "min": 5, "max": 30, "label": "RSI週期"},
                "oversold": {"type": "number", "default": 30, "min": 10, "max": 40, "label": "超賣門檻"},
                "overbought": {"type": "number", "default": 70, "min": 60, "max": 90, "label": "超買門檻"}
            }
        },
        "sar": {
            "name": "SAR策略",
            "params": {
                "af_start": {"type": "number", "default": 0.02, "min": 0.01, "max": 0.05, "step": 0.01, "label": "初始加速因子"},
                "af_max": {"type": "number", "default": 0.2, "min": 0.1, "max": 0.5, "step": 0.01, "label": "最大加速因子"},
                "af_increment": {"type": "number", "default": 0.02, "min": 0.01, "max": 0.05, "step": 0.01, "label": "加速因子增量"}
            }
        },
        "adx": {
            "name": "ADX策略",
            "params": {
                "period": {"type": "number", "default": 14, "min": 7, "max": 28, "label": "ADX週期"},
                "threshold": {"type": "number", "default": 25, "min": 15, "max": 40, "label": "趨勢強度門檻"}
            }
        }
    }

def get_strategy_func(strategy_name):
    """根據策略名稱取得策略函數"""
    if strategy_name == "ma":
        from strategies.ma_strategy import ma_crossover_strategy
        return ma_crossover_strategy
    elif strategy_name == "kd":
        from strategies.kd_strategy import kd_strategy
        return kd_strategy
    elif strategy_name == "macd":
        from strategies.macd_strategy import macd_strategy
        return macd_strategy
    elif strategy_name == "rsi":
        from strategies.advanced_strategies import rsi_strategy
        return rsi_strategy
    elif strategy_name == "sar":
        from strategies.sar_strategy import sar_strategy
        return sar_strategy
    elif strategy_name == "adx":
        from strategies.adx_strategy import adx_strategy
        return adx_strategy
    return None

@app.route('/api/backtest/strategies', methods=['GET'])
def get_available_strategies():
    """取得可用策略列表"""
    return jsonify(get_strategies())

@app.route('/api/backtest/tickers', methods=['GET'])
def get_available_tickers():
    """取得可用股票代碼"""
    loader = StockDataLoader()
    tickers = loader.list_available_tickers()
    return jsonify({"tickers": tickers})

@app.route('/api/backtest/run', methods=['POST'])
def run_backtest():
    """執行回測"""
    data = request.get_json()
    
    ticker = data.get('ticker', '0050.TW')
    strategy = data.get('strategy', 'ma')
    params = data.get('params', {})
    initial_capital = data.get('capital', 100000)
    commission = data.get('commission', 0.001)
    
    # 載入數據
    loader = StockDataLoader()
    df = loader.load(ticker)
    
    if df is None or len(df) < 60:
        return jsonify({"error": "無法載入足夠的數據"}), 400
    
    # 取得策略函數
    strategy_func = get_strategy_func(strategy)
    if strategy_func is None:
        return jsonify({"error": "無效的策略"}), 400
    
    # 執行回測
    try:
        engine = BacktestEngine(initial_capital=initial_capital, commission=commission)
        engine.load_data(df.tail(500))  # 使用最近500天數據
        engine.add_strategy(strategy_func, **params)
        result = engine.run()
        
        # 準備返回數據
        result_data = {
            "ticker": ticker,
            "strategy": strategy,
            "params": params,
            "metrics": {
                "total_return": round(result.total_return, 2),
                "annualized_return": round(result.annualized_return, 2),
                "sharpe_ratio": round(result.sharpe_ratio, 2),
                "max_drawdown": round(result.max_drawdown, 2),
                "win_rate": round(result.win_rate, 2),
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades
            },
            "equity_curve": [
                {
                    "date": str(eq['date']),
                    "equity": round(eq['equity'], 2),
                    "price": eq['price'],
                    "signal": eq.get('signal', 0)
                }
                for eq in result.equity_curve
            ],
            "trades": [
                {
                    "date": str(t.date),
                    "action": t.action,
                    "price": t.price,
                    "quantity": t.quantity
                }
                for t in result.trades
            ]
        }
        
        # 儲存到資料庫
        conn = sqlite3.connect(BACKTEST_DB)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO backtest_results 
            (ticker, strategy, params, total_return, annualized_return, sharpe_ratio, max_drawdown, win_rate, total_trades)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker,
            strategy,
            json.dumps(params),
            result.total_return,
            result.annualized_return,
            result.sharpe_ratio,
            result.max_drawdown,
            result.win_rate,
            result.total_trades
        ))
        conn.commit()
        conn.close()
        
        return jsonify(result_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/backtest/history', methods=['GET'])
def get_backtest_history():
    """取得回測歷史記錄（支援分頁）"""
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    page = int(request.args.get('page', 1))
    
    # 如果有 page 參數，優先使用 page 計算 offset
    if page > 1:
        offset = (page - 1) * limit
    
    conn = sqlite3.connect(BACKTEST_DB)
    cursor = conn.cursor()
    
    # 取得總數
    cursor.execute('SELECT COUNT(*) FROM backtest_results')
    total = cursor.fetchone()[0]
    
    # 取得分頁資料
    cursor.execute('''
        SELECT id, ticker, strategy, params, total_return, annualized_return, 
               sharpe_ratio, max_drawdown, win_rate, total_trades, created_at
        FROM backtest_results
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "ticker": row[1],
            "strategy": row[2],
            "params": json.loads(row[3]),
            "total_return": row[4],
            "annualized_return": row[5],
            "sharpe_ratio": row[6],
            "max_drawdown": row[7],
            "win_rate": row[8],
            "total_trades": row[9],
            "created_at": row[10]
        })
    
    return jsonify({
        "history": history,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "page": page,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    })


def get_all_history_data():
    """取得所有歷史資料（用於匯出）"""
    conn = sqlite3.connect(BACKTEST_DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, ticker, strategy, params, total_return, annualized_return, 
               sharpe_ratio, max_drawdown, win_rate, total_trades, created_at
        FROM backtest_results
        ORDER BY created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "ticker": row[1],
            "strategy": row[2],
            "params": json.loads(row[3]),
            "total_return": row[4],
            "annualized_return": row[5],
            "sharpe_ratio": row[6],
            "max_drawdown": row[7],
            "win_rate": row[8],
            "total_trades": row[9],
            "created_at": row[10]
        })
    return history


@app.route('/api/backtest/export', methods=['GET'])
def export_backtest():
    """匯出回測記錄為 CSV 或 PDF"""
    export_format = request.args.get('format', 'csv')
    limit = int(request.args.get('limit', 50))
    
    history = get_all_history_data()
    if limit > 0:
        history = history[:limit]
    
    if export_format == 'csv':
        # CSV 匯出
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 標題
        writer.writerow([
            'ID', '股票代碼', '策略', '參數', '總報酬率(%)', '年化報酬率(%)', 
            '夏普比率', '最大回撤(%)', '勝率(%)', '交易次數', '建立時間'
        ])
        
        # 資料
        for row in history:
            params_str = json.dumps(row['params'], ensure_ascii=False)
            writer.writerow([
                row['id'],
                row['ticker'],
                row['strategy'],
                params_str,
                f"{row['total_return']:.2f}" if row['total_return'] else '',
                f"{row['annualized_return']:.2f}" if row['annualized_return'] else '',
                f"{row['sharpe_ratio']:.2f}" if row['sharpe_ratio'] else '',
                f"{row['max_drawdown']:.2f}" if row['max_drawdown'] else '',
                f"{row['win_rate']:.2f}" if row['win_rate'] else '',
                row['total_trades'],
                row['created_at']
            ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv;charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename=backtest_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    
    elif export_format == 'pdf':
        # PDF 匯出
        if not PDF_AVAILABLE:
            return jsonify({"error": "PDF 庫未安裝，請執行: pip install fpdf2"}), 500
        
        class PDFReport(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 15)
                self.cell(0, 10, 'Backtest History Report', 0, 1, 'C')
                self.ln(5)
            
            def section_title(self, title):
                self.set_font('Arial', 'B', 12)
                self.cell(0, 10, title, 0, 1, 'L')
                self.ln(2)
        
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font('Arial', '', 9)
        
        # 標題
        pdf.set_font('Arial', 'B', 9)
        headers = ['ID', 'Ticker', 'Strategy', 'Return%', 'Annual%', 'Sharpe', 'MaxDD%', 'Win%', 'Trades', 'Date']
        col_widths = [10, 20, 20, 20, 20, 20, 20, 20, 15, 35]
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, 1, 0, 'C')
        pdf.ln()
        
        # 資料
        pdf.set_font('Arial', '', 8)
        for row in history:
            pdf.cell(col_widths[0], 7, str(row['id']), 1, 0, 'C')
            pdf.cell(col_widths[1], 7, str(row['ticker']), 1, 0, 'C')
            pdf.cell(col_widths[2], 7, str(row['strategy']), 1, 0, 'C')
            pdf.cell(col_widths[3], 7, f"{row['total_return']:.2f}" if row['total_return'] else '', 1, 0, 'R')
            pdf.cell(col_widths[4], 7, f"{row['annualized_return']:.2f}" if row['annualized_return'] else '', 1, 0, 'R')
            pdf.cell(col_widths[5], 7, f"{row['sharpe_ratio']:.2f}" if row['sharpe_ratio'] else '', 1, 0, 'R')
            pdf.cell(col_widths[6], 7, f"{row['max_drawdown']:.2f}" if row['max_drawdown'] else '', 1, 0, 'R')
            pdf.cell(col_widths[7], 7, f"{row['win_rate']:.2f}" if row['win_rate'] else '', 1, 0, 'R')
            pdf.cell(col_widths[8], 7, str(row['total_trades']), 1, 0, 'C')
            pdf.cell(col_widths[9], 7, str(row['created_at'])[:19], 1, 0, 'C')
            pdf.ln()
        
        # 頁尾
        pdf.set_y(-15)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 10, f'Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 0, 'C')
        
        # 輸出 PDF
        pdf_buffer = io.BytesIO()
        pdf.output(pdf_buffer)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'backtest_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
    
    else:
        return jsonify({"error": "不支援的格式，請使用 csv 或 pdf"}), 400

@app.route('/backtest')
def backtest_page():
    """回測頁面"""
    from flask import render_template_string
    html = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回測系統 - OpenClaw Quant</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #38bdf8; margin-bottom: 20px; font-size: 1.8rem; }
        h2 { color: #94a3b8; margin-bottom: 15px; font-size: 1.2rem; margin-top: 30px; }
        
        .card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .card-header { font-weight: 600; margin-bottom: 15px; color: #e2e8f0; }
        
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .form-group { display: flex; flex-direction: column; gap: 5px; }
        label { font-size: 0.9rem; color: #94a3b8; }
        input, select { background: #334155; border: 1px solid #475569; border-radius: 6px; padding: 10px; color: #e2e8f0; font-size: 1rem; }
        input:focus, select:focus { outline: none; border-color: #38bdf8; }
        
        .params-container { display: none; }
        .params-container.active { display: block; }
        
        .btn { background: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 12px 24px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn:hover { background: #0ea5e9; }
        .btn:disabled { background: #475569; cursor: not-allowed; }
        .btn-secondary { background: #475569; }
        
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
        .metric-card { background: #334155; border-radius: 8px; padding: 15px; text-align: center; }
        .metric-label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 5px; }
        .metric-value { font-size: 1.4rem; font-weight: 700; }
        .metric-value.positive { color: #4ade80; }
        .metric-value.negative { color: #f87171; }
        
        .chart-container { position: relative; height: 400px; }
        
        .trades-list { max-height: 300px; overflow-y: auto; }
        .trade-item { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #334155; }
        .trade-item:last-child { border-bottom: none; }
        .trade-buy { color: #4ade80; }
        .trade-sell { color: #f87171; }
        
        .history-table { width: 100%; border-collapse: collapse; }
        .history-table th, .history-table td { padding: 12px; text-align: left; border-bottom: 1px solid #334155; }
        .history-table th { background: #334155; color: #94a3b8; font-weight: 600; }
        .history-table tr:hover { background: #334155; }
        
        .loading { text-align: center; padding: 40px; color: #94a3b8; }
        .error { background: #7f1d1d; color: #fecaca; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { background: #334155; border: none; color: #94a3b8; padding: 10px 20px; border-radius: 6px; cursor: pointer; }
        .tab.active { background: #38bdf8; color: #0f172a; }
        
        @media (max-width: 768px) {
            .form-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 回測系統</h1>
        
        <div class="card">
            <div class="card-header">策略設定</div>
            <div class="form-grid">
                <div class="form-group">
                    <label>股票代碼</label>
                    <select id="ticker">
                        <option value="0050.TW">0050.TW (元大台灣50)</option>
                        <option value="2330.TW">2330.TW (台積電)</option>
                        <option value="2317.TW">2317.TW (鴻海)</option>
                        <option value="2454.TW">2454.TW (聯發科)</option>
                        <option value="taiwan_index">taiwan_index (加權指數)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>交易策略</label>
                    <select id="strategy">
                        <option value="ma">均線策略 (MA)</option>
                        <option value="kd">KD策略</option>
                        <option value="macd">MACD策略</option>
                        <option value="rsi">RSI策略</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>初始資金</label>
                    <input type="number" id="capital" value="100000" min="10000">
                </div>
                <div class="form-group">
                    <label>手續費率</label>
                    <input type="number" id="commission" value="0.001" step="0.0001" min="0" max="0.01">
                </div>
            </div>
            
            <!-- MA 參數 -->
            <div id="params-ma" class="params-container active">
                <div class="form-grid" style="margin-top: 15px;">
                    <div class="form-group">
                        <label>短期MA週期</label>
                        <input type="number" id="ma_short" value="20" min="5" max="60">
                    </div>
                    <div class="form-group">
                        <label>長期MA週期</label>
                        <input type="number" id="ma_long" value="60" min="20" max="250">
                    </div>
                </div>
            </div>
            
            <!-- KD 參數 -->
            <div id="params-kd" class="params-container">
                <div class="form-grid" style="margin-top: 15px;">
                    <div class="form-group">
                        <label>RSV週期 (n)</label>
                        <input type="number" id="kd_n" value="9" min="5" max="20">
                    </div>
                    <div class="form-group">
                        <label>K平滑週期 (m1)</label>
                        <input type="number" id="kd_m1" value="3" min="1" max="10">
                    </div>
                    <div class="form-group">
                        <label>D平滑週期 (m2)</label>
                        <input type="number" id="kd_m2" value="3" min="1" max="10">
                    </div>
                </div>
            </div>
            
            <!-- MACD 參數 -->
            <div id="params-macd" class="params-container">
                <div class="form-grid" style="margin-top: 15px;">
                    <div class="form-group">
                        <label>快線週期</label>
                        <input type="number" id="macd_fast" value="12" min="5" max="30">
                    </div>
                    <div class="form-group">
                        <label>慢線週期</label>
                        <input type="number" id="macd_slow" value="26" min="15" max="50">
                    </div>
                    <div class="form-group">
                        <label>訊號線週期</label>
                        <input type="number" id="macd_signal" value="9" min="5" max="20">
                    </div>
                </div>
            </div>
            
            <!-- RSI 參數 -->
            <div id="params-rsi" class="params-container">
                <div class="form-grid" style="margin-top: 15px;">
                    <div class="form-group">
                        <label>RSI週期</label>
                        <input type="number" id="rsi_period" value="14" min="5" max="30">
                    </div>
                    <div class="form-group">
                        <label>超賣門檻</label>
                        <input type="number" id="rsi_oversold" value="30" min="10" max="40">
                    </div>
                    <div class="form-group">
                        <label>超買門檻</label>
                        <input type="number" id="rsi_overbought" value="70" min="60" max="90">
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <button class="btn" id="runBtn" onclick="runBacktest()">🚀 執行回測</button>
            </div>
        </div>
        
        <div id="error" class="error" style="display: none;"></div>
        
        <div id="results" style="display: none;">
            <div class="card">
                <div class="card-header">📊 績效指標</div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">總報酬率</div>
                        <div class="metric-value" id="metric-return">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">年化報酬</div>
                        <div class="metric-value" id="metric-annual">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value" id="metric-sharpe">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">最大回撤</div>
                        <div class="metric-value negative" id="metric-drawdown">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">勝率</div>
                        <div class="metric-value" id="metric-winrate">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">交易次數</div>
                        <div class="metric-value" id="metric-trades">--</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">📈 資金曲線</div>
                <div class="chart-container">
                    <canvas id="equityChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">📋 交易紀錄</div>
                <div class="trades-list" id="tradesList"></div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">📜 歷史記錄</div>
            <table class="history-table">
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>股票</th>
                        <th>策略</th>
                        <th>報酬率</th>
                        <th>Sharpe</th>
                        <th>交易次</th>
                    </tr>
                </thead>
                <tbody id="historyTable"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        let equityChart = null;
        
        // 策略切換
        document.getElementById('strategy').addEventListener('change', function() {
            document.querySelectorAll('.params-container').forEach(el => el.classList.remove('active'));
            document.getElementById('params-' + this.value).classList.add('active');
        });
        
        // 取得參數
        function getParams() {
            const strategy = document.getElementById('strategy').value;
            if (strategy === 'ma') {
                return {
                    short_period: parseInt(document.getElementById('ma_short').value),
                    long_period: parseInt(document.getElementById('ma_long').value)
                };
            } else if (strategy === 'kd') {
                return {
                    n: parseInt(document.getElementById('kd_n').value),
                    m1: parseInt(document.getElementById('kd_m1').value),
                    m2: parseInt(document.getElementById('kd_m2').value)
                };
            } else if (strategy === 'macd') {
                return {
                    fast: parseInt(document.getElementById('macd_fast').value),
                    slow: parseInt(document.getElementById('macd_slow').value),
                    signal: parseInt(document.getElementById('macd_signal').value)
                };
            } else if (strategy === 'rsi') {
                return {
                    period: parseInt(document.getElementById('rsi_period').value),
                    oversold: parseInt(document.getElementById('rsi_oversold').value),
                    overbought: parseInt(document.getElementById('rsi_overbought').value)
                };
            }
            return {};
        }
        
        // 執行回測
        async function runBacktest() {
            const btn = document.getElementById('runBtn');
            btn.disabled = true;
            btn.textContent = '執行中...';
            
            const errorDiv = document.getElementById('error');
            errorDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/backtest/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        ticker: document.getElementById('ticker').value,
                        strategy: document.getElementById('strategy').value,
                        params: getParams(),
                        capital: parseInt(document.getElementById('capital').value),
                        commission: parseFloat(document.getElementById('commission').value)
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || '回測失敗');
                }
                
                displayResults(data);
                loadHistory();
                
            } catch (err) {
                errorDiv.textContent = err.message;
                errorDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.textContent = '🚀 執行回測';
            }
        }
        
        // 顯示結果
        function displayResults(data) {
            document.getElementById('results').style.display = 'block';
            
            const m = data.metrics;
            const returnEl = document.getElementById('metric-return');
            returnEl.textContent = m.total_return.toFixed(2) + '%';
            returnEl.className = 'metric-value ' + (m.total_return >= 0 ? 'positive' : 'negative');
            
            document.getElementById('metric-annual').textContent = m.annualized_return.toFixed(2) + '%';
            document.getElementById('metric-sharpe').textContent = m.sharpe_ratio.toFixed(2);
            document.getElementById('metric-drawdown').textContent = m.max_drawdown.toFixed(2) + '%';
            document.getElementById('metric-winrate').textContent = m.win_rate.toFixed(1) + '%';
            document.getElementById('metric-trades').textContent = m.total_trades;
            
            // 繪製圖表
            drawChart(data.equity_curve);
            
            // 顯示交易紀錄
            const tradesList = document.getElementById('tradesList');
            tradesList.innerHTML = data.trades.map(t => `
                <div class="trade-item">
                    <span>${t.date.split('T')[0]}</span>
                    <span class="${t.action === 'buy' ? 'trade-buy' : 'trade-sell'}">${t.action === 'buy' ? '買入' : '賣出'}</span>
                    <span>${t.price.toFixed(2)}</span>
                    <span>${t.quantity}股</span>
                </div>
            `).join('');
            
            // 滾動到結果
            document.getElementById('results').scrollIntoView({behavior: 'smooth'});
        }
        
        // 繪製資金曲線圖
        function drawChart(equityData) {
            const ctx = document.getElementById('equityChart').getContext('2d');
            
            if (equityChart) {
                equityChart.destroy();
            }
            
            const dates = equityData.map(e => e.date.split('T')[0]);
            const equities = equityData.map(e => e.equity);
            const prices = equityData.map(e => e.price);
            
            // 找出買賣點
            const buyPoints = equityData.filter(e => e.signal === 1).map(e => ({x: e.date.split('T')[0], y: e.equity}));
            const sellPoints = equityData.filter(e => e.signal === -1).map(e => ({x: e.date.split('T')[0], y: e.equity}));
            
            equityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: '帳戶資金',
                        data: equities,
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.1)',
                        fill: true,
                        tension: 0.1,
                        yAxisID: 'y'
                    }, {
                        label: '股價',
                        data: prices,
                        borderColor: '#94a3b8',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y1',
                        pointRadius: 0
                    }, {
                        label: '買點',
                        data: buyPoints.map(p => ({x: p.x, y: p.y})),
                        backgroundColor: '#4ade80',
                        pointRadius: 8,
                        pointStyle: 'triangle',
                        showLine: false,
                        yAxisID: 'y'
                    }, {
                        label: '賣點',
                        data: sellPoints.map(p => ({x: p.x, y: p.y})),
                        backgroundColor: '#f87171',
                        pointRadius: 8,
                        pointStyle: 'triangle',
                        rotation: 180,
                        showLine: false,
                        yAxisID: 'y'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8', maxTicksLimit: 10 } },
                        y: { 
                            type: 'linear', 
                            display: true, 
                            position: 'left',
                            grid: { color: '#334155' },
                            ticks: { color: '#38bdf8' },
                            title: { display: true, text: '資金', color: '#38bdf8' }
                        },
                        y1: { 
                            type: 'linear', 
                            display: true, 
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            ticks: { color: '#94a3b8' },
                            title: { display: true, text: '股價', color: '#94a3b8' }
                        }
                    },
                    plugins: { legend: { labels: { color: '#e2e8f0' } } }
                }
            });
        }
        
        // 載入歷史記錄
        async function loadHistory() {
            try {
                const response = await fetch('/api/backtest/history?limit=20');
                const data = await response.json();
                
                const strategyNames = {ma: '均線', kd: 'KD', macd: 'MACD'};
                
                document.getElementById('historyTable').innerHTML = data.history.map(h => `
                    <tr>
                        <td>${h.created_at.split(' ')[0]}</td>
                        <td>${h.ticker}</td>
                        <td>${strategyNames[h.strategy] || h.strategy}</td>
                        <td class="${h.total_return >= 0 ? 'trade-buy' : 'trade-sell'}">${h.total_return.toFixed(2)}%</td>
                        <td>${h.sharpe_ratio.toFixed(2)}</td>
                        <td>${h.total_trades}</td>
                    </tr>
                `).join('');
                
            } catch (err) {
                console.error('載入歷史失敗:', err);
            }
        }
        
        // 頁面載入時取得歷史記錄
        loadHistory();
    </script>
</body>
</html>
    '''
    return render_template_string(html)

if __name__ == '__main__':
    print("🚀 啟動即時報價 API 服務...")
    print("📡 端點:")
    print("   GET /api/quote?symbol=<代碼> - 取得單一報價")
    print("   GET /api/quotes?symbols=<代碼1>,<代碼2> - 取得多個報價")
    print("   GET /api/crypto - 加密貨幣報價")
    print("   GET /api/commodities - 原物料報價")
    print("   GET /api/stocks/tw?symbol=<代碼> - 台灣股票")
    print("   GET /health - 健康檢查")
    print("   📊 即時分析 (新!):")
    print("   GET /api/analyze?symbol=<代碼> - 即時分析 (支撐/壓力位,進場時間,風險)")
    print("   GET /api/ma?symbol=<代碼>&short=20&long=60 - MA 指標分析")
    print("   GET /api/macd?symbol=<代碼>&fast=12&slow=26&signal=9 - MACD 指標分析")
    print("   GET /api/kd?symbol=<代碼>&n=9&m1=3&m2=3 - KD 指標分析")
    print("   GET /api/rsi?symbol=<代碼>&rsi_period=14&oversold=30&overbought=70 - RSI 指標分析")
    print("   GET /api/adx?symbol=<代碼>&period=14&threshold=25 - ADX 指標分析")
    print("   GET /api/recommend?symbols=<代碼1>,<代碼2> - 推薦標的")
    print("   📈 回測系統:")
    print("   GET /backtest - 回測網頁")
    print("   POST /api/backtest/run - 執行回測")
    print("   GET /api/backtest/history - 歷史記錄（支援分頁）")
    print("   GET /api/backtest/strategies - 策略列表")
    print("   GET /api/backtest/tickers - 股票清單")
    print("   GET /api/backtest/export?format=csv - 匯出 CSV")
    print("   GET /api/backtest/export?format=pdf - 匯出 PDF")
    app.run(host='0.0.0.0', port=3001, debug=True)
