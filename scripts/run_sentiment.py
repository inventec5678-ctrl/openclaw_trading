#!/usr/bin/env python3
"""
社群情緒分析主程式 - 整合爬蟲與情緒分析
每小時執行: crontab -e
0 * * * * /usr/bin/python3 /Users/changrunlin/.openclaw/workspace/scripts/run_sentiment.py
"""

import os
import sys

# 加入 scripts 目錄
sys.path.insert(0, '/Users/changrunlin/.openclaw/workspace/scripts')

import ptt_scraper
import reddit_scraper
import sentiment_analysis

def main():
    print("=" * 50)
    print("Starting Social Sentiment Analysis")
    print("=" * 50)
    
    # Step 1: 爬取 PTT Stock
    print("\n[1/3] Fetching PTT Stock...")
    ptt_articles = ptt_scraper.fetch_stock_board(pages=3)
    if ptt_articles:
        ptt_scraper.save_articles(ptt_articles)
    print(f"   Got {len(ptt_articles)} PTT articles")
    
    # Step 2: 爬取 Reddit RSS
    print("\n[2/3] Fetching Reddit RSS...")
    reddit_posts = reddit_scraper.fetch_reddit_rss()
    if reddit_posts:
        reddit_scraper.save_posts(reddit_posts)
    print(f"   Got {len(reddit_posts)} Reddit posts")
    
    # Step 3: 情緒分析
    print("\n[3/3] Running Sentiment Analysis...")
    sentiment_analysis.run_analysis()
    
    print("\n" + "=" * 50)
    print("Analysis Complete!")
    print("=" * 50)

if __name__ == '__main__':
    main()
