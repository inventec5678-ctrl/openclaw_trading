#!/usr/bin/env python3
"""
PTT Stock Scraper - 爬取 PTT Stock 看板文章
"""

import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

PTT_URL = "https://www.ptt.cc/bbs/Stock/index.html"
DATA_DIR = os.path.expanduser("~/openclaw_data/social")

def get_cookies():
    """取得 PTT cookies (年齡確認)"""
    return {'over18': '1'}

def fetch_stock_board(pages=3):
    """爬取 Stock 看板最新文章"""
    articles = []
    url = PTT_URL
    
    for _ in range(pages):
        try:
            resp = requests.get(url, cookies=get_cookies(), timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            for article in soup.select('div.r-ent'):
                try:
                    title = article.select_one('div.title a')
                    if title and '股票' in title.text:
                        articles.append({
                            'title': title.text.strip(),
                            'url': 'https://www.ptt.cc' + title['href'],
                            'author': article.select_one('div.author').text if article.select_one('div.author') else '',
                            'date': article.select_one('div.date').text if article.select_one('div.date') else '',
                            'source': 'ptt_stock',
                            'timestamp': datetime.now().isoformat()
                        })
                except Exception:
                    continue
            
            # 上一頁
            prev_link = soup.select_one('a.w.btn[href*="index"]')
            if prev_link:
                url = 'https://www.ptt.cc' + prev_link['href']
            else:
                break
        except Exception as e:
            print(f"Error fetching PTT: {e}")
            break
    
    return articles

def save_articles(articles):
    """儲存文章到 JSON"""
    if not articles:
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(DATA_DIR, f'ptt_stock_{timestamp}.json')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(articles)} PTT articles to {filepath}")
    return filepath

if __name__ == '__main__':
    articles = fetch_stock_board(pages=3)
    if articles:
        save_articles(articles)
    else:
        print("No articles fetched")
