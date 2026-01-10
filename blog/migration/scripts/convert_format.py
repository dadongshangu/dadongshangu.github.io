#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章格式转换脚本
将HTML内容转换为Hexo Markdown格式，并清理引流链接
"""

import os
import sys
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
import html2text

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
ARTICLES_MARKDOWN_DIR = os.path.join(DATA_DIR, "articles_markdown")

# 引流尾巴识别（只用于“截断文章末尾”，避免误删正文）
PROMO_TAIL_PATTERNS = [
    r'感谢关注',
    r'原创推荐[：:]',
    r'关注公众号',
    r'长按.*(识别|关注)',
    r'点击.*(关注|进入)',
    r'微信公众',
    r'mp\.weixin\.qq\.com',
]

def create_directories():
    """创建必要的目录"""
    os.makedirs(ARTICLES_MARKDOWN_DIR, exist_ok=True)

def strip_promo_tail(text: str) -> str:
    \"\"\"从底向上定位引流尾巴，截断其后所有内容。\"\"\"
    lines = text.split('\\n')
    cut_idx = None

    for idx in range(len(lines) - 1, -1, -1):
        s = lines[idx].strip()
        if not s:
            continue
        for pattern in PROMO_TAIL_PATTERNS:
            if re.search(pattern, s, re.IGNORECASE):
                cut_idx = idx
                break
        if cut_idx is not None:
            break

    if cut_idx is None:
        return text

    # 吞掉紧邻的空行
    while cut_idx > 0 and not lines[cut_idx - 1].strip():
        cut_idx -= 1

    return '\\n'.join(lines[:cut_idx]).rstrip()

def html_to_markdown(html_content):
    """
    将HTML内容转换为Markdown格式
    """
    # 使用html2text转换
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # 不换行
    h.unicode_snob = True
    
    # 转换
    markdown = h.handle(html_content)
    
    # 清理多余的空行
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    # 清理文章末尾引流
    markdown = strip_promo_tail(markdown)
    
    return markdown.strip()

def extract_title_from_html(html_content):
    """从HTML中提取标题"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 尝试多种方式获取标题
    title = None
    
    # 方法1: 查找h1或h2标签
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
    
    if not title:
        h2 = soup.find('h2')
        if h2:
            title = h2.get_text(strip=True)
    
    # 方法2: 查找strong标签
    if not title:
        strong = soup.find('strong')
        if strong:
            title = strong.get_text(strip=True)
    
    return title

def timestamp_to_datetime(timestamp):
    """将时间戳转换为日期时间字符串"""
    if timestamp:
        try:
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def generate_front_matter(article):
    """生成Hexo front-matter"""
    title = article.get('title', '未命名文章')
    url = article.get('url', '')
    
    # 处理日期
    date_str = article.get('publish_date')
    if not date_str and article.get('timestamp'):
        date_str = timestamp_to_datetime(article['timestamp'])
    elif not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    front_matter = f"""---
title: {title}
date: {date_str}
tags: 
  - 大东山谷精选
"""
    
    # 可选：添加原文链接（注释掉，因为用户要求不包含链接）
    # if url:
    #     front_matter += f"original_url: {url}\n"
    
    front_matter += "---\n"
    
    return front_matter

def convert_article(article):
    """转换单篇文章"""
    title = article.get('title', '未命名文章')
    print(f"正在转换: {title}")
    
    # 获取HTML内容
    html_content = article.get('content')
    if not html_content:
        # 尝试从文件读取
        html_file = article.get('html_file')
        if html_file and os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            print(f"  错误：无法获取文章内容")
            return None
    
    # 转换为Markdown
    markdown_content = html_to_markdown(html_content)
    
    # 生成front-matter
    front_matter = generate_front_matter(article)
    
    # 组合完整内容
    full_content = front_matter + "\n" + markdown_content
    
    # 保存Markdown文件
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '|')).strip()[:100]
    markdown_file = os.path.join(ARTICLES_MARKDOWN_DIR, f"{safe_title}.md")
    
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    print(f"  已保存: {markdown_file}")
    
    return {
        'title': title,
        'markdown_file': markdown_file,
        'original_article': article
    }

def main():
    """主函数"""
    print("=" * 60)
    print("文章格式转换工具")
    print("=" * 60)
    
    create_directories()
    
    # 读取文章列表
    if not os.path.exists(ARTICLES_LIST_FILE):
        print(f"错误：找不到文章列表文件: {ARTICLES_LIST_FILE}")
        print("请先运行 fetch_articles.py 获取文章列表")
        return
    
    with open(ARTICLES_LIST_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"\n找到 {len(articles)} 篇文章，开始转换...\n")
    
    converted_articles = []
    
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] ", end='')
        converted = convert_article(article)
        
        if converted:
            converted_articles.append(converted)
    
    # 保存转换后的文章列表
    converted_list_file = os.path.join(DATA_DIR, "articles_converted.json")
    with open(converted_list_file, 'w', encoding='utf-8') as f:
        json.dump(converted_articles, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"转换完成！共转换 {len(converted_articles)} 篇文章")
    print("=" * 60)

if __name__ == '__main__':
    main()
