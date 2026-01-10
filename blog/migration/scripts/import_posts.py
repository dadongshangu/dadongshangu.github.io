#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章导入脚本
将转换后的文章导入到Hexo博客的_posts目录
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
BLOG_POSTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "source", "_posts")
ARTICLES_FINAL_FILE = os.path.join(DATA_DIR, "articles_final.json")
ARTICLES_MARKDOWN_DIR = os.path.join(DATA_DIR, "articles_markdown")

def sanitize_filename(title):
    """生成安全的文件名"""
    # 移除或替换不安全的字符
    safe_name = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '|', '，', '。', '？', '！', '：'))
    safe_name = safe_name.replace(' ', '-')
    safe_name = safe_name.replace('|', '-')
    safe_name = safe_name[:100]  # 限制长度
    return safe_name.strip()

def generate_filename(article):
    """根据文章信息生成文件名"""
    title = article.get('title', '未命名文章')
    markdown_file = article.get('markdown_file', '')
    
    # 如果已有markdown文件，使用其文件名
    if markdown_file and os.path.exists(markdown_file):
        base_name = os.path.basename(markdown_file)
        return base_name
    
    # 否则根据标题生成
    safe_name = sanitize_filename(title)
    
    # 尝试从文章信息中获取日期
    original_article = article.get('original_article', {})
    date_str = None
    
    if original_article.get('publish_date'):
        try:
            dt = datetime.fromisoformat(original_article['publish_date'])
            date_str = dt.strftime('%Y-%m-%d')
        except:
            pass
    
    if original_article.get('timestamp'):
        try:
            dt = datetime.fromtimestamp(int(original_article['timestamp']))
            date_str = dt.strftime('%Y-%m-%d')
        except:
            pass
    
    if date_str:
        filename = f"{date_str}-{safe_name}.md"
    else:
        filename = f"{safe_name}.md"
    
    return filename

def import_article(article):
    """导入单篇文章"""
    title = article.get('title', '未命名文章')
    markdown_file = article.get('markdown_file', '')
    
    if not markdown_file or not os.path.exists(markdown_file):
        print(f"  错误：找不到Markdown文件: {markdown_file}")
        return None
    
    # 生成目标文件名
    target_filename = generate_filename(article)
    target_path = os.path.join(BLOG_POSTS_DIR, target_filename)
    
    # 如果文件已存在，添加序号
    if os.path.exists(target_path):
        base_name = os.path.splitext(target_filename)[0]
        ext = os.path.splitext(target_filename)[1]
        counter = 1
        while os.path.exists(target_path):
            target_filename = f"{base_name}-{counter}{ext}"
            target_path = os.path.join(BLOG_POSTS_DIR, target_filename)
            counter += 1
    
    # 复制文件
    try:
        shutil.copy2(markdown_file, target_path)
        print(f"  ✓ 已导入: {target_filename}")
        return target_path
    except Exception as e:
        print(f"  ✗ 导入失败: {str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("文章导入工具")
    print("=" * 60)
    
    # 检查目标目录
    if not os.path.exists(BLOG_POSTS_DIR):
        os.makedirs(BLOG_POSTS_DIR, exist_ok=True)
        print(f"已创建目录: {BLOG_POSTS_DIR}")
    
    # 读取最终文章列表
    if not os.path.exists(ARTICLES_FINAL_FILE):
        print(f"错误：找不到最终文章列表: {ARTICLES_FINAL_FILE}")
        print("请先运行 check_duplicates.py 检查重复")
        return
    
    with open(ARTICLES_FINAL_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"\n准备导入 {len(articles)} 篇文章到: {BLOG_POSTS_DIR}\n")
    
    # 非交互模式默认继续（Cursor/CI 运行时 stdin 可能不可用）
    try:
        response = input("是否继续？(y/n): ").strip().lower()
        if response not in ("y", "yes"):
            print("已取消")
            return
    except EOFError:
        print("检测到非交互环境，默认继续导入。")
    
    # 导入文章
    imported = []
    failed = []
    
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {article.get('title', '未命名文章')}")
        result = import_article(article)
        
        if result:
            imported.append(result)
        else:
            failed.append(article.get('title', '未命名文章'))
    
    # 输出结果
    print("\n" + "=" * 60)
    print("导入完成")
    print("=" * 60)
    print(f"成功导入: {len(imported)} 篇")
    print(f"导入失败: {len(failed)} 篇")
    
    if failed:
        print("\n失败的文章:")
        for title in failed:
            print(f"  - {title}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
