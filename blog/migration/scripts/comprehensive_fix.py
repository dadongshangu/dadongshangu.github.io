#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合修复脚本
- 检查文章是否有文字内容
- 清理重复的图片说明
- 修复分段问题
- 清理多余空行
"""

import os
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")


def has_text_content(md_content):
    """检查文章是否有文字内容（不仅仅是图片和front-matter）"""
    lines = md_content.split('\n')
    
    # 跳过front-matter
    in_frontmatter = False
    text_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == '---':
            in_frontmatter = not in_frontmatter
            continue
        
        if in_frontmatter:
            continue
        
        # 跳过空行、图片、图片说明、标记
        if not stripped:
            continue
        
        if re.match(r'^!\[.*\]\(https?://', line):
            continue
        
        if re.match(r'^[（(].*[）)]$', stripped):
            continue
        
        if '全文完，以下图片待整理' in stripped:
            continue
        
        # 如果有其他内容，说明有文字
        text_lines.append(stripped)
    
    # 如果有超过50个字符的文字内容，认为有文字
    total_text = ' '.join(text_lines)
    return len(total_text) > 50


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
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南', '推荐', '假设', '价格', '母亲', '电话机', '安徽宁国', '山东农村', '两岁的你', '有模有样', '画警车', '爷爷奶奶', '生日礼物', '小时候', '散步', '石榴树', '爷爷', '院子', '睡着', '那时中考', '马扎', '爷', '父亲', '临朐方言', '饥困']
            if any(keyword in stripped for keyword in caption_keywords):
                # 检查前一行是否是图片
                if len(result) > 0 and re.match(r'^!\[.*\]\(https?://mmbiz', result[-1]):
                    # 紧跟在图片后面，保留（但只保留一次）
                    if stripped not in seen_captions:
                        result.append(line)
                        seen_captions.add(stripped)
                else:
                    # 不是紧跟在图片后面，检查是否是重复的
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
                i += 1
                # 跳过后续的重复图片说明
                while i < len(lines):
                    next_stripped = lines[i].strip()
                    if next_stripped == stripped:
                        i += 1
                    elif not next_stripped:
                        i += 1
                    else:
                        break
                continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)


def fix_paragraph_breaks(md_content):
    """修复段落分隔"""
    lines = md_content.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 跳过空行、front-matter、图片、列表、引用等
        if not stripped:
            result.append("")
            continue
        
        if stripped.startswith('---'):
            result.append(line)
            continue
        
        if stripped.startswith(('title:', 'date:', 'tags:')):
            result.append(line)
            continue
        
        if re.match(r'^!\[.*\]\(https?://', line):
            result.append(line)
            continue
        
        if stripped.startswith(('*', '-', '+', '1.', '2.', '3.', '4.', '5.', '>', '#')):
            result.append(line)
            continue
        
        if re.match(r'^[（(].*[）)]$', stripped):
            result.append(line)
            continue
        
        if '全文完，以下图片待整理' in stripped:
            result.append(line)
            continue
        
        # 检查是否是独立的对话行
        if re.match(r'^["''""].*["''""]$', stripped):
            # 独立对话行应该单独成段
            if result and result[-1].strip() and not re.match(r'^["''""].*["''""]$', result[-1].strip()):
                result.append("")
            result.append(line)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() and not re.match(r'^["''""].*["''""]$', next_line.strip()):
                    result.append("")
            continue
        
        # 检查上一行是否是独立对话行
        if result and result[-1].strip() and re.match(r'^["''""].*["''""]$', result[-1].strip()):
            if result[-1] != "":
                result.append("")
        
        # 检查是否是文本行
        # 如果上一行是文本且以标点结尾，且当前行也是文本，添加段落分隔
        if result and result[-1].strip():
            prev_line = result[-1].strip()
            # 上一行以标点结尾（句号、问号、感叹号、冒号）
            if prev_line and prev_line[-1] in ['。', '！', '？', '.', '!', '?', '：', ':']:
                # 当前行不是特殊格式，且上一行不是空行
                if (not stripped.startswith(('*', '-', '+', '1.', '2.', '3.', '4.', '5.', '>', '#')) and
                    not re.match(r'^[（(].*[）)]$', stripped) and
                    not re.match(r'^!\[.*\]\(https?://', line) and
                    result[-1] != ""):
                    # 检查是否需要添加段落分隔（如果上一行和当前行之间没有空行）
                    if result[-1] != "":
                        result.append("")
        
        result.append(line)
    
    return '\n'.join(result)


def clean_excessive_empty_lines(md_content):
    """清理多余的空行（连续3个以上空行压缩为2个）"""
    lines = md_content.split('\n')
    result = []
    empty_count = 0
    
    for line in lines:
        if not line.strip():
            empty_count += 1
            if empty_count <= 2:
                result.append("")
        else:
            empty_count = 0
            result.append(line)
    
    return '\n'.join(result)


def process_article(post_file):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    md_content = post_file.read_text(encoding='utf-8')
    original_length = len(md_content)
    
    issues = []
    
    # 1. 检查是否有文字内容
    if not has_text_content(md_content):
        issues.append("缺少文字内容")
        print(f"  [WARN] 文章缺少文字内容（只有图片）")
    
    # 2. 清理重复的图片说明
    new_content = clean_duplicate_captions(md_content)
    if new_content != md_content:
        issues.append("清理重复图片说明")
        md_content = new_content
    
    # 3. 修复段落分隔
    new_content = fix_paragraph_breaks(md_content)
    if new_content != md_content:
        issues.append("修复段落分隔")
        md_content = new_content
    
    # 4. 清理多余空行
    new_content = clean_excessive_empty_lines(md_content)
    if new_content != md_content:
        issues.append("清理多余空行")
        md_content = new_content
    
    new_length = len(md_content)
    
    if issues:
        post_file.write_text(md_content, encoding='utf-8')
        print(f"  [OK] 已修复: {', '.join(issues)} (从 {original_length} 字符减少到 {new_length} 字符)")
        return True
    
    print(f"  无需修复")
    return False


def main():
    """主函数"""
    fixed = 0
    processed = 0
    no_text = []
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            md_content = post_file.read_text(encoding='utf-8')
            if not has_text_content(md_content):
                no_text.append(post_file.name)
            
            if process_article(post_file):
                fixed += 1
            processed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n[SUMMARY] processed={processed}, fixed={fixed}")
    if no_text:
        print(f"\n[WARN] 以下文章缺少文字内容（只有图片）:")
        for name in no_text:
            print(f"  - {name}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
