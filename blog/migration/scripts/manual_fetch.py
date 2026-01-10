#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动辅助抓取工具
如果自动抓取失败，可以使用此工具手动输入文章链接进行抓取
"""

import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ARTICLES_LIST_FILE = os.path.join(OUTPUT_DIR, "articles_list.json")
ARTICLES_RAW_DIR = os.path.join(OUTPUT_DIR, "articles_raw")

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

def fetch_single_article(url, title=None):
    """抓取单篇文章"""
    try:
        print(f"\n正在抓取: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            if not title:
                title_elem = soup.find('h1', id='activity-name') or soup.find('h2', class_='rich_media_title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    title = "未命名文章"
            
            # 提取内容
            content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
            
            if content_div:
                # 提取发布日期
                date_elem = soup.find('em', class_='rich_media_meta_text') or soup.find('span', class_='publish_time')
                publish_date = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    try:
                        publish_date = datetime.strptime(date_text, '%Y-%m-%d %H:%M')
                    except:
                        pass
                
                # 保存HTML
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
                html_file = os.path.join(ARTICLES_RAW_DIR, f"{safe_title}.html")
                
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                return {
                    'title': title,
                    'url': url,
                    'content': str(content_div),
                    'html_file': html_file,
                    'publish_date': publish_date.isoformat() if publish_date else None
                }
            else:
                print("  错误：无法找到文章内容")
                return None
        else:
            print(f"  错误：访问失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  错误：{str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("手动辅助抓取工具")
    print("=" * 60)
    print("\n如果自动抓取失败，可以使用此工具手动输入文章链接")
    print("按回车键继续，输入 'q' 退出\n")
    
    articles = []
    
    while True:
        url = input("请输入文章链接（或输入 'q' 完成）: ").strip()
        
        if url.lower() == 'q':
            break
        
        if not url.startswith('http'):
            print("无效的链接，请重新输入")
            continue
        
        title = input("请输入文章标题（可选，直接回车跳过）: ").strip()
        if not title:
            title = None
        
        article = fetch_single_article(url, title)
        
        if article:
            articles.append(article)
            print(f"✓ 成功抓取: {article['title']}")
        else:
            print("✗ 抓取失败")
    
    if articles:
        # 保存文章列表
        if os.path.exists(ARTICLES_LIST_FILE):
            with open(ARTICLES_LIST_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            articles.extend(existing)
        
        with open(ARTICLES_LIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print(f"\n共抓取 {len(articles)} 篇文章")
        print(f"文章列表已保存到: {ARTICLES_LIST_FILE}")
    else:
        print("\n没有抓取到任何文章")

if __name__ == '__main__':
    main()
