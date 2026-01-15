#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面检查所有文章的状态
- 检查文字内容
- 检查重复内容
- 检查段落分隔
- 检查图片格式
- 检查结束标记
"""

import os
import re
from pathlib import Path
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")

END_MARKER = "全文完，以下图片待整理"


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
        
        if END_MARKER in stripped:
            continue
        
        # 如果有其他内容，说明有文字
        text_lines.append(stripped)
    
    # 如果有超过50个字符的文字内容，认为有文字
    total_text = ' '.join(text_lines)
    return len(total_text) > 50


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


def check_duplicate_paragraphs(md_content):
    """检查是否有重复段落"""
    lines = md_content.split('\n')
    
    # 跳过front-matter
    in_frontmatter = False
    paragraphs = []
    current_para = []
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == '---':
            in_frontmatter = not in_frontmatter
            continue
        
        if in_frontmatter:
            continue
        
        # 跳过空行、图片、图片说明、标记
        if not stripped:
            if current_para:
                para_text = ' '.join(current_para).strip()
                if len(para_text) > 20:  # 只检查较长的段落
                    paragraphs.append(para_text)
                current_para = []
            continue
        
        if re.match(r'^!\[.*\]\(https?://', line):
            continue
        
        if re.match(r'^[（(].*[）)]$', stripped):
            continue
        
        if END_MARKER in stripped:
            continue
        
        current_para.append(stripped)
    
    # 检查最后一段
    if current_para:
        para_text = ' '.join(current_para).strip()
        if len(para_text) > 20:
            paragraphs.append(para_text)
    
    # 统计重复段落
    para_counts = Counter(paragraphs)
    duplicates = {para: count for para, count in para_counts.items() if count > 1}
    
    return duplicates


def check_article(post_file):
    """检查单篇文章"""
    issues = []
    warnings = []
    
    md_content = post_file.read_text(encoding='utf-8')
    
    # 1. 检查文字内容
    if not has_text_content(md_content):
        issues.append("缺少文字内容（只有图片）")
    
    # 2. 检查重复段落
    duplicates = check_duplicate_paragraphs(md_content)
    if duplicates:
        warnings.append(f"发现 {len(duplicates)} 处重复段落")
    
    # 3. 检查结束标记
    end_image_index = find_end_images(md_content)
    if end_image_index is not None:
        # 有末尾图片，检查是否有结束标记
        lines = md_content.split('\n')
        has_marker = False
        for i in range(max(0, end_image_index - 5), end_image_index):
            if END_MARKER in lines[i]:
                has_marker = True
                break
        
        if not has_marker:
            issues.append("有末尾图片但缺少结束标记")
    
    # 4. 检查图片格式
    lines = md_content.split('\n')
    image_count = 0
    invalid_images = 0
    for line in lines:
        if re.match(r'^!\[.*\]\(https?://mmbiz', line):
            image_count += 1
            # 检查图片格式是否正确
            if not re.match(r'^!\[.*\]\(https?://mmbiz[^)]+\)$', line):
                invalid_images += 1
    
    if invalid_images > 0:
        issues.append(f"发现 {invalid_images} 个格式不正确的图片")
    
    # 5. 检查多余空行（连续3个以上）
    empty_line_count = 0
    max_empty = 0
    for line in lines:
        if not line.strip():
            empty_line_count += 1
            max_empty = max(max_empty, empty_line_count)
        else:
            empty_line_count = 0
    
    if max_empty > 2:
        warnings.append(f"发现连续 {max_empty} 个空行（应压缩为2个）")
    
    return issues, warnings, image_count


def main():
    """主函数"""
    all_issues = []
    all_warnings = []
    no_text_articles = []
    total_images = 0
    
    print("=" * 60)
    print("文章检查报告")
    print("=" * 60)
    
    for post_file in sorted(Path(POSTS_DIR).glob("*.md")):
        try:
            issues, warnings, image_count = check_article(post_file)
            total_images += image_count
            
            if issues or warnings:
                print(f"\n[检查] {post_file.name}")
                if issues:
                    for issue in issues:
                        print(f"  [ERROR] {issue}")
                        all_issues.append((post_file.name, issue))
                if warnings:
                    for warning in warnings:
                        print(f"  [WARN] {warning}")
                        all_warnings.append((post_file.name, warning))
            
            if not has_text_content(post_file.read_text(encoding='utf-8')):
                no_text_articles.append(post_file.name)
                
        except Exception as e:
            print(f"\n[检查] {post_file.name}")
            print(f"  [ERROR] 检查失败: {e}")
            all_issues.append((post_file.name, f"检查失败: {e}"))
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("[SUMMARY] 检查统计")
    print("=" * 60)
    print(f"总文章数: {len(list(Path(POSTS_DIR).glob('*.md')))}")
    print(f"总图片数: {total_images}")
    print(f"发现问题: {len(all_issues)} 个")
    print(f"发现警告: {len(all_warnings)} 个")
    
    if no_text_articles:
        print(f"\n[WARN] 以下文章缺少文字内容（只有图片）:")
        for name in no_text_articles:
            print(f"  - {name}")
    
    if all_issues:
        print(f"\n[ERROR] 需要修复的问题:")
        for name, issue in all_issues:
            print(f"  - {name}: {issue}")
    
    if all_warnings:
        print(f"\n[WARN] 建议修复的警告:")
        for name, warning in all_warnings:
            print(f"  - {name}: {warning}")
    
    if not all_issues and not all_warnings:
        print("\n[OK] 所有文章检查通过，未发现需要修复的问题！")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
