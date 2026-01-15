#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理特定文章中的重复图片说明
专门用于修复"夜宿星河"文章中的重复图片说明
"""

import os
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")


def clean_duplicate_captions(md_content):
    """清理重复的图片说明"""
    lines = md_content.split('\n')
    result = []
    seen_captions = set()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 检查是否是图片说明行
        if re.match(r'^[（(].*[）)]$', stripped):
            # 检查前一行是否是图片
            if len(result) > 0 and re.match(r'^!\[.*\]\(https?://mmbiz', result[-1]):
                # 紧跟在图片后面，保留（但只保留一次）
                if stripped not in seen_captions:
                    result.append(line)
                    seen_captions.add(stripped)
            else:
                # 检查是否是重复的图片说明
                if stripped not in seen_captions:
                    # 检查后面是否有对应的图片
                    has_image_after = False
                    for j in range(i + 1, min(i + 11, len(lines))):
                        if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                            has_image_after = True
                            break
                    
                    if has_image_after:
                        # 后面有图片，保留（但只保留一次）
                        result.append(line)
                        seen_captions.add(stripped)
                    # 否则删除
                # 跳过后续的重复图片说明
                while i + 1 < len(lines):
                    next_stripped = lines[i + 1].strip()
                    if next_stripped == stripped:
                        i += 1
                    elif not next_stripped:
                        i += 1
                    else:
                        break
            i += 1
            continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)


def process_article(post_file):
    """处理单篇文章"""
    print(f"处理: {post_file.name}")
    
    md_content = post_file.read_text(encoding='utf-8')
    original_length = len(md_content)
    
    new_content = clean_duplicate_captions(md_content)
    
    new_length = len(new_content)
    
    if new_content != md_content:
        post_file.write_text(new_content, encoding='utf-8')
        print(f"  [OK] 已清理重复图片说明 (从 {original_length} 字符减少到 {new_length} 字符)")
        return True
    
    print(f"  无需修复")
    return False


def main():
    """主函数"""
    # 只处理"夜宿星河"文章
    post_file = Path(POSTS_DIR) / "2019-11-10-夜宿星河.md"
    
    if not post_file.exists():
        print(f"[ERROR] 文件不存在: {post_file}")
        return 1
    
    try:
        if process_article(post_file):
            print(f"\n[OK] 修复完成")
        else:
            print(f"\n[OK] 无需修复")
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
