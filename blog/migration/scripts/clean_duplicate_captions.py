#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理重复的图片说明
- 删除连续重复的图片说明
- 只保留紧跟在图片后面的图片说明
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
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 检查是否是图片说明行
        if re.match(r'^[（(].*[）)]$', stripped):
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南', '推荐', '假设', '价格', '母亲', '电话机', '安徽宁国', '山东农村', '两岁的你', '有模有样', '画警车', '爷爷奶奶', '生日礼物', '小时候', '散步', '石榴树']
            if any(keyword in stripped for keyword in caption_keywords):
                # 检查前一行是否是图片
                if len(result) > 0 and re.match(r'^!\[.*\]\(https?://mmbiz', result[-1]):
                    # 紧跟在图片后面，保留
                    result.append(line)
                    i += 1
                    # 跳过后续的重复图片说明和空行
                    while i < len(lines):
                        next_stripped = lines[i].strip()
                        if next_stripped == stripped:
                            i += 1
                        elif not next_stripped:
                            i += 1
                        else:
                            break
                    continue
                else:
                    # 不是紧跟在图片后面，检查后面是否有图片
                    has_image_after = False
                    # 检查后面10行是否有对应的图片
                    for j in range(i + 1, min(i + 11, len(lines))):
                        if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                            # 检查图片的alt文本是否包含图片说明的内容
                            alt_match = re.match(r'^!\[([^\]]+)\]', lines[j])
                            if alt_match:
                                alt_text = alt_match.group(1)
                                # 提取图片说明的文本（去掉括号）
                                caption_text = stripped.strip('（）()')
                                # 更宽松的匹配
                                if (caption_text in alt_text or 
                                    alt_text in caption_text or
                                    any(word in alt_text for word in caption_text.split() if len(word) > 2)):
                                    has_image_after = True
                                    break
                    
                    if not has_image_after:
                        # 后面没有对应的图片，删除这个图片说明
                        # 跳过当前行和后续的重复图片说明
                        current_caption = stripped
                        i += 1
                        while i < len(lines):
                            next_stripped = lines[i].strip()
                            if next_stripped == current_caption:
                                i += 1
                            elif not next_stripped:
                                i += 1
                            else:
                                break
                        continue
                    else:
                        # 后面有对应的图片，但不在紧邻位置，也删除（因为图片会在后面插入）
                        current_caption = stripped
                        i += 1
                        while i < len(lines):
                            next_stripped = lines[i].strip()
                            if next_stripped == current_caption:
                                i += 1
                            elif not next_stripped:
                                i += 1
                            else:
                                break
                        continue
        
        result.append(line)
        i += 1
    
    # 清理多余的空行（连续3个以上空行压缩为2个）
    cleaned_result = []
    empty_count = 0
    for line in result:
        if not line.strip():
            empty_count += 1
            if empty_count <= 2:
                cleaned_result.append("")
        else:
            empty_count = 0
            cleaned_result.append(line)
    
    return '\n'.join(cleaned_result)


def process_article(post_file):
    """处理单篇文章"""
    print(f"处理: {post_file.name}")
    
    md_content = post_file.read_text(encoding='utf-8')
    new_content = clean_duplicate_captions(md_content)
    
    if new_content != md_content:
        post_file.write_text(new_content, encoding='utf-8')
        print(f"  [OK] 已清理重复的图片说明")
        return True
    
    print(f"  无需清理")
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
