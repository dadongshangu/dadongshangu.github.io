#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在文章末尾图片前添加结束标记
- 检测文章末尾的图片（在最后30行内）
- 在第一个图片前插入"全文完，以下图片待整理"
"""

import os
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")

END_MARKER = "全文完，以下图片待整理"


def find_end_images(md_content):
    """查找文章末尾的图片位置"""
    lines = md_content.split('\n')
    
    # 检查最后30行
    check_range = min(30, len(lines))
    end_start = len(lines) - check_range
    
    # 找到第一个图片的位置
    first_image_index = None
    for i in range(end_start, len(lines)):
        if re.match(r'^!\[.*\]\(https?://mmbiz', lines[i]):
            first_image_index = i
            break
    
    return first_image_index


def add_end_marker(md_content):
    """在文章末尾图片前添加结束标记"""
    lines = md_content.split('\n')
    
    # 查找末尾图片位置
    first_image_index = find_end_images(md_content)
    
    if first_image_index is None:
        return None  # 没有找到末尾图片
    
    # 检查是否已经有结束标记
    # 检查图片前5行是否有结束标记
    for i in range(max(0, first_image_index - 5), first_image_index):
        if END_MARKER in lines[i]:
            return None  # 已经有结束标记了
    
    # 在图片前插入结束标记
    # 如果图片前有空行，在空行后插入；否则在图片前插入，并添加空行
    result_lines = lines[:]
    
    # 检查图片前是否有空行
    if first_image_index > 0 and not result_lines[first_image_index - 1].strip():
        # 有空行，在空行后插入
        result_lines.insert(first_image_index, END_MARKER)
    else:
        # 没有空行，先插入空行，再插入标记
        result_lines.insert(first_image_index, "")
        result_lines.insert(first_image_index + 1, END_MARKER)
        first_image_index += 2
    
    return '\n'.join(result_lines)


def process_article(post_file):
    """处理单篇文章"""
    print(f"处理: {post_file.name}")
    
    md_content = post_file.read_text(encoding='utf-8')
    new_content = add_end_marker(md_content)
    
    if new_content and new_content != md_content:
        post_file.write_text(new_content, encoding='utf-8')
        print(f"  [OK] 已添加结束标记")
        return True
    
    print(f"  无需修复（没有末尾图片或已有标记）")
    return False


def main():
    """主函数"""
    fixed = 0
    processed = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if process_article(post_file):
                fixed += 1
            processed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n[SUMMARY] processed={processed}, fixed={fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
