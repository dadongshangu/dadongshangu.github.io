#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
去重检查脚本
检查哪些文章已经存在于博客中，避免重复导入
"""

import os
import sys
import json
import re
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
BLOG_POSTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "source", "_posts")
ARTICLES_CONVERTED_FILE = os.path.join(DATA_DIR, "articles_converted.json")
ARTICLES_FINAL_FILE = os.path.join(DATA_DIR, "articles_final.json")

def normalize_title(title):
    """标准化标题，用于比较"""
    # 移除特殊字符，转换为小写
    normalized = re.sub(r'[^\w\s]', '', title.lower())
    # 移除多余空格
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def get_existing_posts():
    """获取现有博客文章列表"""
    existing_posts = []
    
    if not os.path.exists(BLOG_POSTS_DIR):
        print(f"警告：博客文章目录不存在: {BLOG_POSTS_DIR}")
        return existing_posts
    
    for file_path in Path(BLOG_POSTS_DIR).glob('*.md'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 提取front-matter中的title
                title_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip()
                    existing_posts.append({
                        'file': file_path.name,
                        'title': title,
                        'normalized_title': normalize_title(title)
                    })
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {str(e)}")
    
    return existing_posts

def check_duplicates(articles, existing_posts):
    """检查重复文章"""
    existing_titles = {post['normalized_title'] for post in existing_posts}
    
    new_articles = []
    duplicate_articles = []
    
    for article in articles:
        title = article.get('title', '')
        normalized_title = normalize_title(title)
        
        if normalized_title in existing_titles:
            duplicate_articles.append({
                'title': title,
                'reason': '标题匹配'
            })
            print(f"发现重复: {title}")
        else:
            new_articles.append(article)
    
    return new_articles, duplicate_articles

def main():
    """主函数"""
    print("=" * 60)
    print("去重检查工具")
    print("=" * 60)
    
    # 读取现有文章
    print("\n正在读取现有博客文章...")
    existing_posts = get_existing_posts()
    print(f"找到 {len(existing_posts)} 篇现有文章:")
    for post in existing_posts:
        print(f"  - {post['title']}")
    
    # 读取待导入文章
    if not os.path.exists(ARTICLES_CONVERTED_FILE):
        print(f"\n错误：找不到转换后的文章列表: {ARTICLES_CONVERTED_FILE}")
        print("请先运行 convert_format.py 转换文章格式")
        return
    
    with open(ARTICLES_CONVERTED_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"\n待导入文章: {len(articles)} 篇")
    
    # 检查重复
    print("\n正在检查重复...")
    new_articles, duplicates = check_duplicates(articles, existing_posts)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("检查结果")
    print("=" * 60)
    print(f"现有文章: {len(existing_posts)} 篇")
    print(f"待导入文章: {len(articles)} 篇")
    print(f"重复文章: {len(duplicates)} 篇")
    print(f"新文章: {len(new_articles)} 篇")
    
    if duplicates:
        print("\n重复文章列表:")
        for dup in duplicates:
            print(f"  - {dup['title']}")
    
    # 保存最终导入列表
    with open(ARTICLES_FINAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_articles, f, ensure_ascii=False, indent=2)
    
    print(f"\n最终导入列表已保存到: {ARTICLES_FINAL_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    main()
