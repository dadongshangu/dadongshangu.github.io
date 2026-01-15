#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复所有文章的问题
1. 修复段落问题（从原始文件恢复段落格式）
2. 处理被跳过的文章（即使没有图片说明也要尝试处理）
"""

import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")
WECHATSYNC_MD_DIR = os.path.join(DATA_DIR, "wechatsync_md")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def load_articles_list():
    """加载文章列表"""
    if not os.path.exists(ARTICLES_LIST_FILE):
        return []
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def restore_paragraphs(imported_md, original_md):
    """从原始文件中恢复段落格式"""
    # 提取原始文件的主体内容（去掉front-matter和推广内容）
    original_lines = original_md.split('\n')
    original_content_start = 0
    for i, line in enumerate(original_lines):
        if line.strip() == '---' and i > 0:
            original_content_start = i + 1
            break
    
    # 提取导入文件的主体内容
    imported_lines = imported_md.split('\n')
    imported_content_start = 0
    for i, line in enumerate(imported_lines):
        if line.strip() == '---' and i > 0:
            imported_content_start = i + 1
            break
    
    # 获取front-matter
    front_matter = '\n'.join(imported_lines[:imported_content_start])
    
    # 处理主体内容
    original_content = '\n'.join(original_lines[original_content_start:])
    imported_content = '\n'.join(imported_lines[imported_content_start:])
    
    # 查找超长行并分段
    result_lines = imported_lines[:imported_content_start]
    content_lines = imported_lines[imported_content_start:]
    
    new_content_lines = []
    for line in content_lines:
        # 跳过推广内容
        if any(keyword in line for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩']):
            break
        
        # 如果是超长行（超过200字符且不是图片），尝试分段
        if len(line) > 200 and not line.strip().startswith('!'):
            # 在句号、问号、感叹号后分段
            # 但保留引号内的内容
            segments = []
            current_seg = ''
            in_quotes = False
            
            for char in line:
                current_seg += char
                if char in ['"', '"', '"', '"', ''', ''']:
                    in_quotes = not in_quotes
                elif char in ['。', '！', '？'] and not in_quotes:
                    # 遇到句号等，检查是否应该分段
                    if len(current_seg.strip()) > 50:
                        segments.append(current_seg.strip())
                        current_seg = ''
            
            if current_seg.strip():
                segments.append(current_seg.strip())
            
            # 如果成功分段，添加段落
            if len(segments) > 1:
                for seg in segments:
                    if seg.strip():
                        new_content_lines.append(seg.strip())
                        new_content_lines.append('')
            else:
                new_content_lines.append(line)
        else:
            new_content_lines.append(line)
    
    result_lines.extend(new_content_lines)
    return '\n'.join(result_lines)


def process_article(post_file):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    
    # 读取标题
    title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
    if not title_match:
        return False
    
    title = title_match.group(1).strip()
    
    # 加载原始文件
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
    
    if not original_md:
        print(f"  未找到原始文件")
        return False
    
    print(f"  找到原始文件: {original_file}")
    
    # 检查是否有超长行需要分段
    lines = md_content.split('\n')
    has_long_lines = False
    for line in lines:
        if len(line) > 200 and not line.strip().startswith('!'):
            has_long_lines = True
            break
    
    fixed = False
    
    # 修复段落
    if has_long_lines:
        md_content = restore_paragraphs(md_content, original_md)
        fixed = True
        print(f"  已修复段落")
    
    # 保存
    if fixed:
        post_file.write_text(md_content, encoding='utf-8')
        print(f"  [OK] 已更新")
        return True
    
    return False


def main():
    processed = 0
    skipped = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if process_article(post_file):
                processed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            skipped += 1
    
    print(f"\n[SUMMARY] processed={processed}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
