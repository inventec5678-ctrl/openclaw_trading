#!/usr/bin/env python3
"""
社群爬蟲 - PTT、Dcard、Reddit
使用 cloudscraper 繞過 Cloudflare 保護
"""

import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import time
import random
from datetime import datetime as dt

# 設定路徑
NEWS_DIR = os.path.expanduser("~/openclaw_data/news")
os.makedirs(NEWS_DIR, exist_ok=True)

# 預設 Headers
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

def create_scraper():
    """建立 cloudscraper 實例"""
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'darwin',
            'desktop': True
        }
    )

def delay():
    """隨機延遲 2-4 秒"""
    time.sleep(random.uniform(2, 4))

def collect_ptt_stock():
    """收集 PTT 股市版文章"""
    print("🔍 正在收集 PTT 股市版...")
    posts = []
    
    try:
        url = "https://www.ptt.cc/bbs/Stock/index.html"
        scraper = create_scraper()
        
        response = scraper.get(url, headers=DEFAULT_HEADERS, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            
            # PTT 文章結構
            articles = soup.select('div.r-ent')[:20]
            
            for article in articles:
                try:
                    title_elem = article.select_one('div.title a')
                    author_elem = article.select_one('div.author')
                    date_elem = article.select_one('div.date')
                    link_elem = article.select_one('div.title a')
                    
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    author = author_elem.get_text(strip=True) if author_elem else ""
                    date = date_elem.get_text(strip=True) if date_elem else ""
                    link = link_elem.get('href', '') if link_elem else ""
                    
                    # 排除已被刪除的文章
                    if title and '[公告]' not in title and link:
                        posts.append({
                            "source": "PTT 股市版",
                            "title": title.replace("'", "").replace('"', ''),
                            "author": author,
                            "date": date,
                            "url": f"https://www.ptt.cc{link}",
                            "collected_at": dt.now().isoformat()
                        })
                except Exception as e:
                    continue
            
            print(f"✅ PTT 股市版: 收集到 {len(posts)} 篇文章")
        else:
            print(f"⚠️ PTT 股市版: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ PTT 股市版錯誤: {e}")
    
    return posts

def collect_dcard_invest():
    """收集 Dcard 投資版文章
    
    注意：Dcard 有嚴格的 Cloudflare 保護，可能需要:
    - 使用付費代理服務
    - 使用瀏覽器自動化 (Selenium/Playwright)
    - RSS feed (如果有的話)
    """
    print("🔍 正在收集 Dcard 投資版...")
    posts = []
    
    try:
        # 嘗試多個 Dcard 看板網址
        urls_to_try = [
            "https://www.dcard.tw/f/invest",
            "https://dcard.tw/f/invest", 
            "https://www.dcard.tw/f/news/investing"
        ]
        
        scraper = create_scraper()
        dcard_headers = DEFAULT_HEADERS.copy()
        dcard_headers['Referer'] = 'https://www.dcard.tw/'
        
        success = False
        for url in urls_to_try:
            if success:
                break
            response = scraper.get(url, headers=dcard_headers, timeout=15)
            
            if response.status_code == 200:
                success = True
                soup = BeautifulSoup(response.text, 'lxml')
                
                articles = soup.select('article')[:20]
                
                for article in articles:
                    try:
                        title_elem = article.select_one('h2, h3, a[href*="/p/"]')
                        link_elem = article.select_one('a[href*="/p/"]')
                        
                        title = title_elem.get_text(strip=True) if title_elem else ""
                        link = link_elem.get('href', '') if link_elem else ""
                        
                        if title and link and len(title) > 5:
                            posts.append({
                                "source": "Dcard 投資版",
                                "title": title.replace("'", "").replace('"', ''),
                                "url": f"https://www.dcard.tw{link}" if link.startswith('/') else link,
                                "collected_at": dt.now().isoformat()
                            })
                    except:
                        continue
        
        if posts:
            print(f"✅ Dcard 投資版: 收集到 {len(posts)} 篇文章")
        elif not success:
            # 全部失敗 - 使用替代方案標記
            print(f"⚠️ Dcard 投資版: 被 Cloudflare 擋住 (HTTP 403/404)")
            print("   💡 解決方案: 使用付費代理、瀏覽器自動化或跳過")
            posts.append({
                "source": "Dcard 投資版",
                "title": "[跳過] Dcard 被 Cloudflare 保護，需使用其他方法",
                "url": "",
                "collected_at": dt.now().isoformat(),
                "blocked": True
            })
        else:
            print(f"⚠️ Dcard 投資版: 無文章")
            
    except Exception as e:
        print(f"❌ Dcard 投資版錯誤: {e}")
    
    return posts

def collect_reddit_wsb():
    """收集 Reddit WallStreetBets 版文章"""
    print("🔍 正在收集 Reddit WallStreetBets...")
    posts = []
    
    try:
        # 使用 Reddit 的 JSON API
        url = "https://www.reddit.com/r/wallstreetbets/new.json?limit=25"
        scraper = create_scraper()
        
        reddit_headers = DEFAULT_HEADERS.copy()
        reddit_headers['Accept'] = 'application/json'
        
        response = scraper.get(url, headers=reddit_headers, timeout=15)
        
        if response.status_code == 200:
            try:
                data = response.json()
                children = data.get('data', {}).get('children', [])
                
                for item in children[:20]:
                    post = item.get('data', {})
                    title = post.get('title', '')
                    permalink = post.get('permalink', '')
                    author = post.get('author', '')
                    score = post.get('score', 0)
                    num_comments = post.get('num_comments', 0)
                    
                    if title:
                        posts.append({
                            "source": "Reddit WSB",
                            "title": title.replace("'", "").replace('"', ''),
                            "author": author,
                            "score": score,
                            "comments": num_comments,
                            "url": f"https://www.reddit.com{permalink}",
                            "collected_at": dt.now().isoformat()
                        })
                
                print(f"✅ Reddit WSB: 收集到 {len(posts)} 篇文章")
            except json.JSONDecodeError:
                print("⚠️ Reddit: JSON 解析失敗")
        else:
            print(f"⚠️ Reddit WSB: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Reddit WSB 錯誤: {e}")
    
    return posts

def save_social_posts(all_posts):
    """儲存社群貼文到檔案"""
    if not all_posts:
        print("⚠️ 無貼文可儲存")
        return
    
    # 去除重複
    seen = set()
    unique_posts = []
    for post in all_posts:
        if post['title'] not in seen:
            seen.add(post['title'])
            unique_posts.append(post)
    
    today = dt.now().strftime('%Y-%m-%d')
    filepath = os.path.join(NEWS_DIR, f"social_{today}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "date": today,
            "count": len(unique_posts),
            "posts": unique_posts
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已儲存: {filepath}")
    
    return filepath

def main():
    print("="*50)
    print("社群爬蟲 (PTT、Dcard、Reddit)")
    print("="*50)
    
    all_posts = []
    
    # 收集各社群平台
    all_posts.extend(collect_ptt_stock())
    delay()
    
    all_posts.extend(collect_dcard_invest())
    delay()
    
    all_posts.extend(collect_reddit_wsb())
    
    # 儲存
    if all_posts:
        save_social_posts(all_posts)
        print(f"\n共收集 {len(all_posts)} 篇貼文")
    else:
        print("\n⚠️ 無法獲取任何貼文")
    
    print("\n完成!")

if __name__ == "__main__":
    main()
