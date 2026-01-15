#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
找出被跳过的文章并尝试处理
"""

import os
import re
import json
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")
WECHATSYNC_MD_DIR = os.path.join(DATA_DIR, "wechatsync_md")


def load_articles_list():
    """加载文章列表"""
    if not os.path.exists(ARTICLES_LIST_FILE):
        return []
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_skipped_articles():
    """找出被跳过的文章"""
    articles_list = load_articles_list()
    
    skipped = []
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        # 读取文章
        md_content = post_file.read_text(encoding='utf-8')
        
        # 读取标题
        title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
        if not title_match:
            continue
        
        title = title_match.group(1).strip()
        
        # 检查是否有原始文件
        title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', title)
        original_md = None
        original_file = None
        
        for md_file in Path(WECHATSYNC_MD_DIR).glob("*.md"):
            if md_file.stem.endswith('-1'):
                continue
            file_stem_normalized = re.sub(r'[|_\-：:，,。.\s]', '', md_file.stem)
            if (title_normalized in file_stem_normalized or 
                file_stem_normalized in title_normalized or
                title in md_file.stem or
                md_file.stem in title):
                try:
                    original_md = md_file.read_text(encoding='utf-8')
                    original_file = md_file.name
                    break
                except:
                    pass
        
        # 检查是否有图片
        has_images = bool(re.search(r'!\[.*\]\(https?://mmbiz', md_content))
        
        reason = []
        if not original_md:
            reason.append("未找到原始文件")
        if not has_images:
            reason.append("没有图片")
        
        if reason:
            # 检查是否在文章列表中
            article_url = None
            for item in articles_list:
                if item.get('title') and re.sub(r'[|_\-：:，,。.\s]', '', item['title']) == title_normalized:
                    article_url = item['url']
                    break
            
            skipped.append({
                'file': post_file.name,
                'title': title,
                'reason': ', '.join(reason),
                'has_url': article_url is not None,
                'url': article_url
            })
    
    return skipped


def main():
    skipped = find_skipped_articles()
    
    print(f"\n找到 {len(skipped)} 篇被跳过的文章：\n")
    for item in skipped:
        print(f"文件: {item['file']}")
        print(f"标题: {item['title']}")
        print(f"原因: {item['reason']}")
        print(f"有URL: {item['has_url']}")
        if item['url']:
            print(f"URL: {item['url']}")
        print()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
