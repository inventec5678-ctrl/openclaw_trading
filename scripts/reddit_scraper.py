#!/usr/bin/env python3
"""
Reddit RSS Scraper - 爬取 Reddit 股票相關 RSS
"""

import feedparser
import json
import os
from datetime import datetime

REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/wallstreetbets/.rss",
    "https://www.reddit.com/r/stocks/.rss",
    "https://www.reddit.com/r/investing/.rss"
]

DATA_DIR = os.path.expanduser("~/openclaw_data/social")

def fetch_reddit_rss():
    """爬取 Reddit RSS 資料"""
    all_posts = []
    
    for url in REDDIT_RSS_URLS:
        try:
            feed = feedparser.parse(url)
            subreddit = url.split('/r/')[1].split('/')[0] if '/r/' in url else 'reddit'
            
            for entry in feed.entries[:20]:  # 每個 feed 取 20 篇
                all_posts.append({
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'author': entry.get('author', ''),
                    'published': entry.get('published', ''),
                    'subreddit': subreddit,
                    'source': 'reddit_rss',
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            continue
    
    return all_posts

def save_posts(posts):
    """儲存文章到 JSON"""
    if not posts:
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(DATA_DIR, f'reddit_rss_{timestamp}.json')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(posts)} Reddit posts to {filepath}")
    return filepath

if __name__ == '__main__':
    posts = fetch_reddit_rss()
    if posts:
        save_posts(posts)
    else:
        print("No posts fetched")
