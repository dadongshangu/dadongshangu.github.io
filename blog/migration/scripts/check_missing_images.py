#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查所有文章，找出有图片说明但没有对应图片的文章
"""

import os
import re
from pathlib import Path

BLOG_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")

def check_article(post_file):
    """检查单篇文章"""
    md_content = post_file.read_text(encoding='utf-8')
    lines = md_content.split('\n')
    
    # 查找所有图片说明
    captions = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.search(r'_[（(]([^）)]+)[）)]_', stripped):
            match = re.search(r'[（(]([^）)]+)[）)]', stripped)
            if match:
                captions.append({
                    'line': i,
                    'text': match.group(0)
                })
    
    if not captions:
        return None
    
    # 检查每个图片说明后面是否有图片
    missing = []
    for cap in captions:
        has_image = False
        line_idx = cap['line']
        # 检查后面5行是否有图片
        for j in range(line_idx + 1, min(line_idx + 6, len(lines))):
            if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                has_image = True
                break
        if not has_image:
            missing.append(cap)
    
    if missing:
        return {
            'file': post_file.name,
            'total_captions': len(captions),
            'missing_count': len(missing),
            'missing': missing
        }
    
    return None

def main():
    issues = []
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        result = check_article(post_file)
        if result:
            issues.append(result)
    
    if issues:
        print(f"\n找到 {len(issues)} 篇文章有图片说明缺失图片：\n")
        for issue in issues:
            print(f"文件: {issue['file']}")
            print(f"  共 {issue['total_captions']} 个图片说明，缺失 {issue['missing_count']} 个图片")
            for cap in issue['missing']:
                print(f"    - 第 {cap['line'] + 1} 行: {cap['text']}")
            print()
    else:
        print("\n所有文章的图片说明都有对应的图片！")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
