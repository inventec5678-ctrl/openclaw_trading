#!/usr/bin/env python3
"""
新聞情緒分析整合
- 讀取 Jason 收集的新聞
- 根據新聞調整訊號
- 重大事件影響系數
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

NEWS_DIR = os.path.expanduser("~/openclaw_data/news")


def load_news_files(days: int = 7) -> List[Dict]:
    """
    載入最近的新聞檔案
    
    Args:
        days: 要載入的天數
    
    Returns:
        新聞列表
    """
    news_list = []
    
    if not os.path.exists(NEWS_DIR):
        return news_list
    
    # 取得檔案列表
    files = sorted(os.listdir(NEWS_DIR), reverse=True)
    
    for filename in files[:days]:
        if not filename.endswith('.json'):
            continue
        
        filepath = os.path.join(NEWS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    news_list.extend(data)
                elif isinstance(data, dict):
                    news_list.append(data)
        except Exception as e:
            print(f"載入 {filename} 失敗: {e}")
    
    return news_list


def analyze_sentiment(news_item: Dict) -> Tuple[str, float]:
    """
    分析單則新聞的情緒
    
    Args:
        news_item: 新聞內容
    
    Returns:
        (情緒類型, 分數) - 分數範圍 -1 到 1
    """
    title = news_item.get('title', '').lower()
    content = news_item.get('content', '').lower()
    text = title + ' ' + content
    
    # 正面關鍵詞
    positive_keywords = [
        '漲', '漲幅', '上漲', '大漲', '飆漲', '創新高', '突破', '利多', 
        '看好', '買進', '推薦', '樂觀', '成長', '獲利', '增加', '擴大',
        'bullish', 'up', 'gain', 'rise', 'growth', 'profit', 'buy'
    ]
    
    # 負面關鍵詞
    negative_keywords = [
        '跌', '跌幅', '下跌', '大跌', '暴跌', '崩跌', '創新低', '跌破',
        '看衰', '賣出', '減持', '保守', '衰退', '虧損', '減少', '縮小',
        'bearish', 'down', 'fall', 'drop', 'loss', 'sell', 'weak'
    ]
    
    # 計算分數
    pos_count = sum(1 for kw in positive_keywords if kw in text)
    neg_count = sum(1 for kw in negative_keywords if kw in text)
    
    total = pos_count + neg_count
    
    if total == 0:
        return 'neutral', 0.0
    
    score = (pos_count - neg_count) / total
    
    if score > 0.2:
        sentiment = 'positive'
    elif score < -0.2:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    
    return sentiment, score


def extract_key_events(news_list: List[Dict]) -> List[Dict]:
    """
    提取重大事件
    
    Args:
        news_list: 新聞列表
    
    Returns:
        重大事件列表
    """
    events = []
    
    # 重大事件關鍵詞
    major_keywords = [
        '制裁', '戰爭', '衝突', '危機', '倒閉', '破產', '裁員',
        '併購', '收購', '上市', 'IPO', '增資', '募資',
        '殖利率', '央行', '升息', '降息', '通膨', '失業率',
        'sanction', 'war', 'crisis', 'bankruptcy', 'merger'
    ]
    
    for news in news_list:
        title = news.get('title', '')
        text = (title + ' ' + news.get('content', '')).lower()
        
        is_major = any(kw in text for kw in major_keywords)
        
        if is_major:
            sentiment, score = analyze_sentiment(news)
            events.append({
                "title": news.get('title', ''),
                "source": news.get('source', ''),
                "sentiment": sentiment,
                "impact_score": score,
                "is_major": True
            })
    
    return events


def calculate_news_sentiment(ticker_symbol: str = None) -> Dict:
    """
    計算新聞情緒指標
    
    Args:
        ticker_symbol: 股票代碼（可選，用於過濾相關新聞）
    
    Returns:
        情緒分析結果
    """
    # 載入最近新聞
    news_list = load_news_files(days=7)
    
    if not news_list:
        return {
            "sentiment": "neutral",
            "score": 0,
            "news_count": 0,
            "events": [],
            "impact_factor": 1.0
        }
    
    # 計算整體情緒
    sentiments = []
    scores = []
    
    for news in news_list:
        # 如果有指定股票，檢查相關性
        if ticker_symbol:
            ticker = ticker_symbol.replace('.TW', '')
            title = news.get('title', '').lower()
            if ticker.lower() not in title and ticker_symbol not in title:
                continue
        
        sentiment, score = analyze_sentiment(news)
        sentiments.append(sentiment)
        scores.append(score)
    
    if not scores:
        return {
            "sentiment": "neutral",
            "score": 0,
            "news_count": 0,
            "events": [],
            "impact_factor": 1.0
        }
    
    # 計算平均分數
    avg_score = sum(scores) / len(scores)
    
    # 情緒分類
    if avg_score > 0.3:
        sentiment = "positive"
    elif avg_score < -0.3:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # 提取重大事件
    events = extract_key_events(news_list)
    
    # 計算影響系數
    # 重大事件數量越多，分數越高
    event_impact = len(events) * 0.1
    sentiment_impact = abs(avg_score) * 0.2
    
    # 如果有重大負面事件，大幅影響
    major_negative = sum(1 for e in events if e['sentiment'] == 'negative' and e.get('is_major'))
    if major_negative > 0:
        impact_factor = 1.0 - (major_negative * 0.15)  # 每次重大負面事件降低 15%
    else:
        impact_factor = 1.0 + sentiment_impact
    
    impact_factor = max(0.5, min(1.5, impact_factor))
    
    return {
        "sentiment": sentiment,
        "score": round(avg_score, 3),
        "news_count": len(news_list),
        "filtered_count": len(scores),
        "events": events[:5],  # 最近 5 個重大事件
        "impact_factor": round(impact_factor, 2),
        "interpretation": interpret_sentiment(sentiment, avg_score, impact_factor)
    }


def interpret_sentiment(sentiment: str, score: float, impact_factor: float) -> str:
    """解讀新聞情緒"""
    
    if sentiment == "positive":
        base = "🟢 新聞情緒偏多"
    elif sentiment == "negative":
        base = "🔴 新新聞情緒偏空"
    else:
        base = "⚪ 新聞情緒中性"
    
    if impact_factor < 0.9:
        factor_text = " | 重大事件影響負面訊號"
    elif impact_factor > 1.1:
        factor_text = " | 重大事件增強正面訊號"
    else:
        factor_text = ""
    
    return f"{base} (score: {score:.2f}){factor_text}"


def adjust_signal_with_news(base_signal: str, news_sentiment: Dict) -> Dict:
    """
    根據新聞調整交易訊號
    
    Args:
        base_signal: 基礎訊號 (bullish, bearish, neutral)
        news_sentiment: 新聞情緒分析結果
    
    Returns:
        調整後的訊號
    """
    impact = news_sentiment.get("impact_factor", 1.0)
    sentiment = news_sentiment.get("sentiment", "neutral")
    
    # 調整邏輯
    adjusted = {
        "original_signal": base_signal,
        "news_sentiment": sentiment,
        "news_score": news_sentiment.get("score", 0),
        "impact_factor": impact,
        "adjusted_signal": base_signal,
        "confidence": 1.0,
        "notes": []
    }
    
    # 根據新聞調整信心度
    if sentiment == "positive" and base_signal == "bullish":
        adjusted["confidence"] = min(1.0, impact)
        adjusted["notes"].append("新聞支持多頭訊號")
    elif sentiment == "negative" and base_signal == "bearish":
        adjusted["confidence"] = min(1.0, impact)
        adjusted["notes"].append("新聞支持空頭訊號")
    elif sentiment == "positive" and base_signal == "bearish":
        adjusted["adjusted_signal"] = "neutral"
        adjusted["confidence"] = 0.5
        adjusted["notes"].append("⚠️ 新聞與技術訊號衝突")
    elif sentiment == "negative" and base_signal == "bullish":
        adjusted["adjusted_signal"] = "neutral"
        adjusted["confidence"] = 0.5
        adjusted["notes"].append("⚠️ 新聞與技術訊號衝突")
    
    return adjusted


def main():
    """測試函數"""
    print("=" * 60)
    print("新聞情緒分析")
    print("=" * 60)
    
    # 整體新聞情緒
    overall = calculate_news_sentiment()
    print(f"\n整體市場情緒:")
    print(f"  情緒: {overall['sentiment']}")
    print(f"  分數: {overall['score']}")
    print(f"  新聞數: {overall['news_count']}")
    print(f"  影響系數: {overall['impact_factor']}")
    print(f"  解讀: {overall['interpretation']}")
    
    if overall['events']:
        print(f"\n重大事件:")
        for event in overall['events'][:3]:
            print(f"  - {event['title'][:40]}... ({event['sentiment']})")
    
    # 測試訊號調整
    print(f"\n訊號調整測試:")
    for signal in ["bullish", "bearish", "neutral"]:
        adjusted = adjust_signal_with_news(signal, overall)
        print(f"  原始 {signal} → 調整後 {adjusted['adjusted_signal']} (信心度: {adjusted['confidence']})")


if __name__ == "__main__":
    main()
