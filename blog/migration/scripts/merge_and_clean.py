#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
合并和清理文章数据
清理标题，提取时间戳，合并新旧数据
"""

import os
import sys
import json
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
NEW_ARTICLES_FILE = os.path.join(DATA_DIR, "articles_new.json")

def clean_title(title):
    """清理标题"""
    if not title:
        return '未命名文章'
    
    # 移除所有换行符和多余空格
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()
    
    # 移除开头的编号（如 "36. "）
    title = re.sub(r'^\d+\.\s*', '', title)
    
    # 移除重复的编号和标题（如 "36. 标题36. 标题" -> "标题"）
    match = re.match(r'^(\d+\.\s*)?(.+?)(?:\1\2)?', title)
    if match:
        title = match.group(2).strip()
    
    # 移除末尾的日期（如 "2025年09月14日"）
    title = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日\s*$', '', title)
    
    # 移除末尾的重复内容
    title = re.sub(r'(\d+\.\s*.+?)\1+$', r'\1', title)
    
    return title.strip() or '未命名文章'

def date_to_timestamp(date_str):
    """将日期字符串转换为时间戳"""
    if not date_str:
        return None
    
    # 提取日期（格式：2025年09月14日）
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
    if match:
        year, month, day = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return int(dt.timestamp())
        except:
            pass
    
    return None

def clean_article(article):
    """清理单篇文章数据"""
    title = article.get('title', '')
    url = article.get('url', '')
    date_str = article.get('title', '')  # 日期在title中
    
    # 清理标题
    clean_title_text = clean_title(title)
    
    # 提取时间戳
    timestamp = date_to_timestamp(date_str)
    if not timestamp:
        timestamp = article.get('timestamp')
    
    # 确保URL是https
    if url.startswith('http://'):
        url = url.replace('http://', 'https://')
    
    return {
        'title': clean_title_text,
        'url': url,
        'timestamp': timestamp
    }

def main():
    """主函数"""
    print("=" * 60)
    print("合并和清理文章数据")
    print("=" * 60)
    
    # 读取新提取的文章
    new_articles_json = input("\n请粘贴新提取的JSON数据（直接粘贴，然后按两次Enter）:\n")
    
    # 尝试解析JSON
    try:
        # 移除可能的换行和空格
        new_articles_json = new_articles_json.strip()
        new_articles = json.loads(new_articles_json)
    except json.JSONDecodeError as e:
        print(f"错误：JSON解析失败: {str(e)}")
        return
    
    print(f"\n读取到 {len(new_articles)} 篇文章，开始清理...\n")
    
    # 清理文章
    cleaned_articles = []
    for i, article in enumerate(new_articles, 1):
        cleaned = clean_article(article)
        cleaned_articles.append(cleaned)
        print(f"{i}. {cleaned['title']}")
        if cleaned['timestamp']:
            dt = datetime.fromtimestamp(cleaned['timestamp'])
            print(f"   日期: {dt.strftime('%Y-%m-%d')}")
        print(f"   URL: {cleaned['url'][:80]}...\n")
    
    # 读取现有文章（如果有）
    existing_articles = []
    if os.path.exists(ARTICLES_LIST_FILE):
        with open(ARTICLES_LIST_FILE, 'r', encoding='utf-8') as f:
            existing_articles = json.load(f)
        print(f"现有文章: {len(existing_articles)} 篇")
    
    # 合并并去重
    all_articles = {}
    for article in existing_articles + cleaned_articles:
        url = article['url'].split('#')[0].split('?')[0]  # 标准化URL
        if url not in all_articles:
            all_articles[url] = article
        else:
            # 如果已存在，保留更完整的数据
            if article.get('timestamp') and not all_articles[url].get('timestamp'):
                all_articles[url] = article
    
    final_articles = list(all_articles.values())
    
    # 按时间戳排序（最新的在前）
    final_articles.sort(key=lambda x: x.get('timestamp') or 0, reverse=True)
    
    # 保存
    with open(ARTICLES_LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_articles, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"合并完成！共 {len(final_articles)} 篇文章")
    print(f"文件已保存到: {ARTICLES_LIST_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    main()
