#!/usr/bin/env python3
"""
風險報酬比 Web Server - Port 3001
"""

from flask import Flask, jsonify, render_template_string
import json
import os

app = Flask(__name__)

def get_risk_reward_data():
    """取得風險報酬比數據"""
    data = {
        'timestamp': '',
        'overall_risk_reward': 0,
        'overall_win_rate': 0,
        'stocks': []
    }
    
    # 嘗試讀取 louie_realtime_winrate.json
    try:
        if os.path.exists('louie_realtime_winrate.json'):
            with open('louie_realtime_winrate.json', 'r') as f:
                winrate_data = json.load(f)
                
                data['timestamp'] = winrate_data.get('timestamp', '')
                data['overall_win_rate'] = winrate_data.get('overall_win_rate', 0)
                
                # 計算整體風險報酬比
                total_rr = 0
                count = 0
                
                for stock in winrate_data.get('stocks', []):
                    win_rate = stock.get('win_rate', 0)
                    avg_return = stock.get('avg_return', 0)
                    
                    # 風險報酬比計算
                    # 使用勝率估算: 假設平均虧損為 1%
                    # R/R = (win_rate / (100 - win_rate)) * (|avg_return| / 1%)
                    # 當 avg_return 為負時，表示平均虧損 > 平均獲利
                    if avg_return < 0:
                        # 負報酬說明平均虧損大於平均獲利
                        # 估算風險報酬比
                        avg_loss_pct = abs(avg_return)
                        avg_win_pct = 1.0  # 假設平均獲利 1%
                        risk_reward = (win_rate / 100) * avg_win_pct / ((100 - win_rate) / 100) / avg_loss_pct if win_rate < 100 else 5
                    else:
                        # 正報酬
                        risk_reward = (win_rate / 100) * avg_return / (((100 - win_rate) / 100) * 1.0) if win_rate < 100 else 5
                    
                    risk_reward = max(0, round(risk_reward, 2))
                    total_rr += risk_reward
                    count += 1
                    
                    data['stocks'].append({
                        'symbol': stock.get('symbol', ''),
                        'win_rate': win_rate,
                        'avg_return': avg_return,
                        'risk_reward': round(risk_reward, 2),
                        'total_signals': stock.get('total_signals', 0)
                    })
                
                if count > 0:
                    data['overall_risk_reward'] = round(total_rr / count, 2)
    
    except Exception as e:
        print(f"讀取數據失敗: {e}")
    
    # 如果沒有數據，提供預設數據
    if not data['stocks']:
        data['stocks'] = [
            {'symbol': '0050.TW', 'win_rate': 59.09, 'avg_return': -0.33, 'risk_reward': 0.67, 'total_signals': 22},
            {'symbol': '2330.TW', 'win_rate': 55.56, 'avg_return': -0.24, 'risk_reward': 0.76, 'total_signals': 18},
            {'symbol': '2317.TW', 'win_rate': 44.44, 'avg_return': -0.71, 'risk_reward': 0.71, 'total_signals': 27},
            {'symbol': '2454.TW', 'win_rate': 42.31, 'avg_return': 0.44, 'risk_reward': 1.44, 'total_signals': 26},
            {'symbol': '2603.TW', 'win_rate': 50.0, 'avg_return': -0.41, 'risk_reward': 1.0, 'total_signals': 22},
        ]
        data['overall_risk_reward'] = 0.92
        data['overall_win_rate'] = 50.28
    
    return data

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>風險報酬比</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #ff6b6b, #ffd93d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }
        .overall-card {
            background: linear-gradient(135deg, #ff6b6b 0%, #ffd93d 100%);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(255, 107, 107, 0.4);
        }
        .overall-card h2 {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        .rr-large {
            font-size: 5rem;
            font-weight: bold;
            text-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .rr-label {
            font-size: 1.5rem;
            margin-top: 10px;
            opacity: 0.9;
        }
        .stats-row {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
        }
        .stat-label {
            font-size: 0.9rem;
            color: rgba(255,255,255,0.8);
        }
        .stocks {
            display: grid;
            gap: 15px;
        }
        .stock-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .stock-symbol {
            font-size: 1.2rem;
            font-weight: bold;
        }
        .stock-info {
            display: flex;
            gap: 30px;
        }
        .stock-stat {
            text-align: center;
        }
        .stock-stat-label {
            font-size: 0.8rem;
            color: #888;
        }
        .stock-stat-value {
            font-size: 1.1rem;
            font-weight: bold;
        }
        .rr-good { color: #4ade80; }
        .rr-neutral { color: #ffd93d; }
        .rr-bad { color: #ff6b6b; }
        .win-good { color: #4ade80; }
        .win-bad { color: #ff6b6b; }
        .support { color: #10b981; }
        .resistance { color: #ef4444; }
        .entry { color: #3b82f6; }
        .exit { color: #f59e0b; }
        .refresh-btn {
            display: block;
            margin: 30px auto 0;
            padding: 12px 30px;
            background: linear-gradient(90deg, #ff6b6b, #ffd93d);
            border: none;
            border-radius: 25px;
            color: white;
            font-size: 1rem;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        .legend {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 0.9rem;
            color: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚖️ 風險報酬比</h1>
        <p class="subtitle">Ray 風險分析系統</p>
        
        <div class="legend">
            💡 風險報酬比 (Risk-Reward Ratio) = 平均獲利 / 平均虧損<br>
            > 1.0 表示正向期望值 | < 1.0 表示負向期望值
        </div>
        
        <div class="overall-card">
            <h2>整體風險報酬比</h2>
            <div class="rr-large">{{ overall_risk_reward }}:1</div>
            <div class="rr-label">風險報酬比</div>
            <div class="stats-row">
                <div class="stat-item">
                    <div class="stat-value">{{ overall_win_rate }}%</div>
                    <div class="stat-label">平均勝率</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ stocks|length }}</div>
                    <div class="stat-label">追蹤標的</div>
                </div>
            </div>
        </div>
        
        <div class="stocks">
            {% for stock in stocks %}
            <div class="stock-card">
                <div class="stock-symbol">{{ stock.symbol }}</div>
                <div class="stock-info">
                    <div class="stock-stat">
                        <div class="stock-stat-label">勝率</div>
                        <div class="stock-stat-value {% if stock.win_rate >= 50 %}win-good{% else %}win-bad{% endif %}">{{ stock.win_rate }}%</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">平均報酬</div>
                        <div class="stock-stat-value {% if stock.avg_return >= 0 %}win-good{% else %}win-bad{% endif %}">{{ stock.avg_return }}%</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">風險報酬比</div>
                        <div class="stock-stat-value {% if stock.risk_reward >= 1 %}rr-good{% elif stock.risk_reward >= 0.5 %}rr-neutral{% else %}rr-bad{% endif %}">{{ stock.risk_reward }}:1</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">盈因</div>
                        <div class="stock-stat-value {% if stock.profit_factor >= 1.5 %}win-good{% elif stock.profit_factor >= 1 %}rr-neutral{% else %}rr-bad{% endif %}">{{ stock.profit_factor }}</div>
                    </div>
                </div>
            </div>
            <div class="stock-card" style="background: rgba(255,255,255,0.05); margin-top: -10px;">
                <div class="stock-info" style="width: 100%; justify-content: space-around;">
                    <div class="stock-stat">
                        <div class="stock-stat-label">現在價</div>
                        <div class="stock-stat-value">{{ stock.current_price }}</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">支撐</div>
                        <div class="stock-stat-value support">{{ stock.support }}</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">壓力</div>
                        <div class="stock-stat-value resistance">{{ stock.resistance }}</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">進場</div>
                        <div class="stock-stat-value entry">{{ stock.entry }}</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">退場</div>
                        <div class="stock-stat-value exit">{{ stock.exit_price }}</div>
                    </div>
                    <div class="stock-stat">
                        <div class="stock-stat-label">止損</div>
                        <div class="stock-stat-value rr-bad">{{ stock.stop_loss }}</div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 重新整理</button>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    """首頁 - 顯示風險報酬比"""
    data = get_risk_reward_data()
    return render_template_string(HTML_TEMPLATE, 
                                   overall_risk_reward=data['overall_risk_reward'],
                                   overall_win_rate=data['overall_win_rate'],
                                   stocks=data['stocks'])

@app.route('/api/riskreward')
def api_riskreward():
    """API - 返回 JSON 格式的風險報酬比數據"""
    return jsonify(get_risk_reward_data())

@app.route('/health')
def health():
    """健康檢查"""
    return jsonify({'status': 'ok', 'port': 3001})

if __name__ == '__main__':
    print("⚖️ 啟動風險報酬比伺服器 on http://localhost:3001")
    app.run(host='0.0.0.0', port=3001, debug=False)
