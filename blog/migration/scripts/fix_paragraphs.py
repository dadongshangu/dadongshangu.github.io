#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复文章的段落分隔
- 在句号、问号、感叹号后添加段落分隔
- 识别对话并正确分段
- 保留列表、引用等特殊格式
"""

import os
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")


def is_dialogue_line(line):
    """检查是否是对话行（以引号开头）"""
    stripped = line.strip()
    # 检查是否以引号开头（中文引号或英文引号）
    if stripped.startswith(('"', '"', ''', ''')):
        return True
    # 检查是否以引号开头（去除前导空格后）
    if re.match(r'^\s*["''""]', stripped):
        return True
    return False


def is_standalone_dialogue(line):
    """检查是否是独立的对话行（整行只有引号内容）"""
    stripped = line.strip()
    # 检查是否整行都是引号内容（以引号开头和结尾）
    if re.match(r'^["''""].*["''""]$', stripped):
        return True
    return False


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
        
        # 检查是否是独立的对话行（整行只有引号内容）
        is_standalone = is_standalone_dialogue(line)
        
        if is_standalone:
            # 独立对话行应该单独成段
            # 如果上一行不是空行且不是独立对话行，添加空行
            if result and result[-1].strip() and not is_standalone_dialogue(result[-1]):
                result.append("")
            result.append(line)
            # 独立对话行后也应该有空行（除非下一行也是独立对话行）
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = next_line.strip()
                if next_stripped and not is_standalone_dialogue(next_line):
                    result.append("")
            continue
        
        # 检查是否是对话行（以引号开头，但可能包含其他内容）
        is_dialogue = is_dialogue_line(line)
        
        if is_dialogue:
            # 对话行应该单独成段
            # 如果上一行不是空行且不是对话行，添加空行
            if result and result[-1].strip() and not is_dialogue_line(result[-1]):
                result.append("")
            result.append(line)
            # 对话行后也应该有空行（除非下一行也是对话行）
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = next_line.strip()
                if next_stripped and not is_dialogue_line(next_line):
                    result.append("")
            continue
        
        # 检查上一行是否是对话行
        if result and result[-1].strip() and is_dialogue_line(result[-1]):
            # 上一行是对话，当前行不是对话，添加空行
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
                    not is_dialogue and
                    result[-1] != ""):
                    # 检查是否需要添加段落分隔（如果上一行和当前行之间没有空行）
                    if result[-1] != "":
                        result.append("")
        
        result.append(line)
    
    return '\n'.join(result)


def process_article(post_file):
    """处理单篇文章"""
    print(f"处理: {post_file.name}")
    
    md_content = post_file.read_text(encoding='utf-8')
    new_content = fix_paragraph_breaks(md_content)
    
    if new_content != md_content:
        post_file.write_text(new_content, encoding='utf-8')
        print(f"  [OK] 已修复段落分隔")
        return True
    
    print(f"  无需修复")
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
