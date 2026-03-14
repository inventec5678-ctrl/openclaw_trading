#!/usr/bin/env python3
"""
情緒分析腳本 - 分析社群文章情緒
"""

import json
import os
import glob
from datetime import datetime
from collections import defaultdict

SOCIAL_DIR = os.path.expanduser("~/openclaw_data/social")
SENTIMENT_DIR = os.path.expanduser("~/openclaw_data/sentiment")

# 情緒關鍵字
BULLISH_KEYWORDS = [
    '漲', '看好', '買進', '多頭', '突破', '爆漲', '大漲', '飆漲', '漲停', '牛',
    '獲利', '成長', '利多', '好消息', '接手', '撐住', '反彈', '回升', '衝',
    'call', 'long', 'bull', 'buy', 'up', 'moon', 'rip', 'gain', 'profit'
]

BEARISH_KEYWORDS = [
    '跌', '看跌', '放空', '空頭', '跌破', '爆跌', '大跌', '崩跌', '跌停', '熊',
    '虧損', '利空', '壞消息', '停損', '割肉', '跳水', '暴跌', '狂瀉', '逃',
    'put', 'short', 'bear', 'sell', 'down', 'crash', 'drop', 'loss', 'dump'
]

NEUTRAL_KEYWORDS = [
    '分析', '請益', '請問', '討論', '觀望', '看法', '思考', '想法', '怎麼看'
]

def load_articles():
    """載入所有社群文章"""
    articles = []
    files = glob.glob(os.path.join(SOCIAL_DIR, '*.json'))
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    articles.extend(data)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    return articles

def analyze_sentiment(text):
    """分析單篇文章情緒"""
    text_lower = text.lower()
    
    bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw.lower() in text_lower)
    bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw.lower() in text_lower)
    neutral_count = sum(1 for kw in NEUTRAL_KEYWORDS if kw.lower() in text_lower)
    
    if bullish_count > bearish_count:
        sentiment = 'bullish'
        score = bullish_count - bearish_count
    elif bearish_count > bullish_count:
        sentiment = 'bearish'
        score = bearish_count - bullish_count
    else:
        sentiment = 'neutral'
        score = 0
    
    return {
        'sentiment': sentiment,
        'score': score,
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
        'neutral_count': neutral_count
    }

def analyze_all(articles):
    """分析所有文章"""
    results = []
    
    for article in articles:
        title = article.get('title', '')
        sentiment_data = analyze_sentiment(title)
        
        results.append({
            'title': title,
            'url': article.get('url', ''),
            'source': article.get('source', ''),
            'sentiment': sentiment_data['sentiment'],
            'score': sentiment_data['score'],
            'timestamp': article.get('timestamp', '')
        })
    
    return results

def calculate_summary(analyzed_data):
    """計算情緒摘要"""
    total = len(analyzed_data)
    if total == 0:
        return {'error': 'No data'}
    
    bullish = sum(1 for d in analyzed_data if d['sentiment'] == 'bullish')
    bearish = sum(1 for d in analyzed_data if d['sentiment'] == 'bearish')
    neutral = sum(1 for d in analyzed_data if d['sentiment'] == 'neutral')
    
    avg_score = sum(d['score'] for d in analyzed_data) / total
    
    # 來源分布
    by_source = defaultdict(lambda: {'bullish': 0, 'bearish': 0, 'neutral': 0})
    for d in analyzed_data:
        by_source[d['source']][d['sentiment']] += 1
    
    return {
        'timestamp': datetime.now().isoformat(),
        'total_articles': total,
        'bullish_count': bullish,
        'bearish_count': bearish,
        'neutral_count': neutral,
        'bullish_pct': round(bullish / total * 100, 1),
        'bearish_pct': round(bearish / total * 100, 1),
        'neutral_pct': round(neutral / total * 100, 1),
        'average_score': round(avg_score, 2),
        'by_source': dict(by_source)
    }

def save_results(analyzed_data, summary):
    """儲存結果"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 儲存摘要
    summary_file = os.path.join(SENTIMENT_DIR, f'sentiment_summary_{timestamp}.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 儲存詳細資料
    detail_file = os.path.join(SENTIMENT_DIR, f'sentiment_detail_{timestamp}.json')
    with open(detail_file, 'w', encoding='utf-8') as f:
        json.dump(analyzed_data, f, ensure_ascii=False, indent=2)
    
    # 更新 latest.json
    latest_file = os.path.join(SENTIMENT_DIR, 'latest.json')
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"Saved summary to {summary_file}")
    print(f"Saved detail to {detail_file}")
    print(f"Updated {latest_file}")
    
    return summary_file, detail_file

def run_analysis():
    """執行完整分析流程"""
    print("Loading articles...")
    articles = load_articles()
    print(f"Loaded {len(articles)} articles")
    
    if not articles:
        print("No articles to analyze")
        return
    
    print("Analyzing sentiment...")
    analyzed = analyze_all(articles)
    
    print("Calculating summary...")
    summary = calculate_summary(analyzed)
    
    print("Saving results...")
    save_results(analyzed, summary)
    
    print("\n=== Sentiment Summary ===")
    print(f"Total: {summary['total_articles']}")
    print(f"Bullish: {summary['bullish_count']} ({summary['bullish_pct']}%)")
    print(f"Bearish: {summary['bearish_count']} ({summary['bearish_pct']}%)")
    print(f"Neutral: {summary['neutral_count']} ({summary['neutral_pct']}%)")
    print(f"Average Score: {summary['average_score']}")

if __name__ == '__main__':
    run_analysis()
