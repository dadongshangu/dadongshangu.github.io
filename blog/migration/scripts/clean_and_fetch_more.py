#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理已获取的文章数据并尝试获取更多
"""

import os
import sys
import json
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")

def clean_title(title):
    """清理标题，提取时间戳"""
    # 移除重复部分，提取时间戳
    # 格式类似: "36.我的一个臭毛病36.我的一个臭毛病1757820316"
    
    # 提取时间戳（末尾的数字）
    timestamp_match = re.search(r'(\d{10})$', title)
    timestamp = None
    if timestamp_match:
        timestamp = int(timestamp_match.group(1))
        # 移除时间戳
        title = title[:timestamp_match.start()].strip()
    
    # 移除重复的编号和标题
    # 格式: "36.标题36.标题" -> "标题"
    match = re.match(r'^\d+\.(.+?)(?:\d+\.\1)?$', title)
    if match:
        title = match.group(1).strip()
    
    # 移除开头的编号
    title = re.sub(r'^\d+\.\s*', '', title)
    
    return title, timestamp

def main():
    """主函数"""
    if not os.path.exists(ARTICLES_LIST_FILE):
        print("错误：找不到文章列表文件")
        return
    
    with open(ARTICLES_LIST_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"找到 {len(articles)} 篇文章，开始清理...\n")
    
    cleaned_articles = []
    for article in articles:
        title = article.get('title', '')
        url = article.get('url', '')
        
        # 清理标题并提取时间戳
        clean_title_text, timestamp = clean_title(title)
        
        # 确保URL是https
        if url.startswith('http://'):
            url = url.replace('http://', 'https://')
        
        cleaned_articles.append({
            'title': clean_title_text,
            'url': url,
            'timestamp': timestamp
        })
        
        print(f"清理: {title[:50]}...")
        print(f"  -> {clean_title_text}")
        print(f"  时间戳: {timestamp}\n")
    
    # 保存清理后的数据
    with open(ARTICLES_LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned_articles, f, ensure_ascii=False, indent=2)
    
    print(f"清理完成！共 {len(cleaned_articles)} 篇文章")
    print(f"\n注意：只获取到 {len(cleaned_articles)} 篇，应该有36篇")
    print("剩余文章可能需要：")
    print("1. 在浏览器中滚动页面加载更多")
    print("2. 或使用浏览器控制台脚本提取")
    print("3. 或手动添加剩余文章链接")

if __name__ == '__main__':
    main()
