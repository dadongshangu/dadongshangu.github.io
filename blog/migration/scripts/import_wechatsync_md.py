#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 Wechatsync 导出的 Markdown 批量导入 Hexo：
- 输入目录：migration/data/wechatsync_md/*.md
- 输出目录：blog/source/_posts/*.md
- 规则：
  - 如果没有 front-matter，则自动补齐 title/date/tags
  - date 优先用 migration/data/articles_list.json 里同名文章的 timestamp
  - 清理文章末尾微信公众号引流（截断尾巴）
  - 避免重复：若现有 _posts 中已存在同名 title，则跳过
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
IN_DIR = os.path.join(DATA_DIR, "wechatsync_md")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")

BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")


PROMO_TAIL_PATTERNS = [
    r"感谢关注",
    r"感谢关注.*公众号",
    r"感谢.*关注",
    r"求关注.*公众号",
    r"原创推荐[：:]",
    r"近期原创文章推荐",
    r"近期.*原创.*文章.*推荐",
    r"关注公众号",
    r"长按.*(识别|关注)",
    r"点击.*(关注|进入|小程序)",
    r"点击.*小程序.*购买",
    r"↓.*点击.*小程序.*购买.*↓",
    r"小程序.*购买",
    r"微信公众",
    r"mp\.weixin\.qq\.com",
    r"往期精彩回顾",
    r"近期文章回顾",
    r"近期.*文章回顾",
    r"近期文章[，,].*猜.*喜欢",
    r"近期.*文章[，,].*猜.*喜欢",
    r"近期.*猜.*喜欢",
    r"近期回顾",
    r"文章推荐",
    r"推荐阅读",
    r"相关阅读",
    r"精彩回顾",
    r"往期回顾",
    r"历史文章",
    r"猜你喜欢",
    r"猜您喜欢",
    r"你可能喜欢",
    r"热门文章",
    r"精选文章",
    r"更多精彩",
    r"延伸阅读",
]

# 文章开头的推广模式
PROMO_HEAD_PATTERNS = [
    r"点击.*继续收到文章",
    r"点击.*关注",
    r"长按.*关注",
    r"扫码关注",
    r"识别二维码",
    r"关注.*公众号",
    r"文字.*©",
    r"图片.*©",
]


DATE_CN_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")


def normalize_title(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[“”\"'’]", "", s)
    # 去掉 WeChat/专辑常见编号前缀： "36." / "36．" / "36、"
    s = re.sub(r"^\s*\d+\s*[\.．、]\s*", "", s)
    # 再清一次空白
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_wechat_links(text: str) -> str:
    """清理微信公众号链接和广告内容"""
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # 跳过包含微信公众号链接的行
        if "mp.weixin.qq.com" in line or "__biz=" in line:
            continue
        # 删除行内的微信公众号链接，但保留其他内容
        line = re.sub(r'\[([^\]]+)\]\(https?://[^\)]*mp\.weixin\.qq\.com[^\)]*\)', r'\1', line)
        line = re.sub(r'https?://[^\s]*mp\.weixin\.qq\.com[^\s]*', '', line)
        
        # 删除行内的广告内容
        # 删除"↓点击小程序购买↓"等
        line = re.sub(r'↓.*点击.*小程序.*购买.*↓', '', line, flags=re.IGNORECASE)
        line = re.sub(r'点击.*小程序.*购买', '', line, flags=re.IGNORECASE)
        
        # 删除广告分界线
        line = re.sub(r'—+.*广告.*分界线.*—+', '', line, flags=re.IGNORECASE)
        line = re.sub(r'—{3,}.*—{3,}', '', line)  # 删除多个连续的分隔线
        
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def clean_separators(text: str) -> str:
    """清理分隔符（如 dadong*shangu, dadong1shangu 等）"""
    # 删除单独的分隔符行，以及行内的分隔符
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # 匹配分隔符模式：dadong + 数字/符号 + shangu（单独一行）
        if re.match(r'^dadong[\d\*\-_]*shangu$', stripped, re.IGNORECASE):
            continue
        # 删除行内的分隔符（dadong + 数字/符号 + shangu），包括前后可能有空格的情况
        # 匹配 dadong + 任意字符（数字、*、-、_等）+ shangu
        line = re.sub(r'\s*dadong[\d\*\-_]*shangu\s*', ' ', line, flags=re.IGNORECASE)
        # 清理多余空格
        line = re.sub(r'\s+', ' ', line).strip()
        if line:  # 如果删除分隔符后行不为空，保留
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def clean_extra_whitespace(text: str) -> str:
    """清理多余的空行和空白字符"""
    lines = text.split("\n")
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        # 删除单独的下划线行（通常是格式残留）
        if stripped == "_" or stripped == "__" or stripped == "___":
            continue
        # 删除只包含空格和下划线的行
        if stripped and all(c in " _-" for c in stripped) and len(stripped) <= 5:
            continue
        cleaned_lines.append(line.rstrip())
    
    # 将连续多个空行压缩为最多1个
    result_lines = []
    prev_empty = False
    for line in cleaned_lines:
        is_empty = not line.strip()
        if is_empty:
            if not prev_empty:  # 只保留第一个空行
                result_lines.append("")
            prev_empty = True
        else:
            result_lines.append(line)
            prev_empty = False
    
    # 删除开头和结尾的空行
    while result_lines and not result_lines[0].strip():
        result_lines.pop(0)
    while result_lines and not result_lines[-1].strip():
        result_lines.pop()
    
    return "\n".join(result_lines).strip()


def remove_empty_image_captions(text: str) -> str:
    """删除没有图片的图片说明"""
    lines = text.split("\n")
    cleaned_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 检查是否是图片说明（括号内的说明文字，如"（不同步的悬浮照|2018.06|大东山谷 摄）"）
        is_caption = False
        
        # 模式1: 括号内的说明文字（全角或半角括号）
        if re.match(r'^[（(].*[）)]$', stripped):
            # 检查是否包含图片说明关键词
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷']
            if any(keyword in stripped for keyword in caption_keywords):
                # 检查前后是否有图片链接
                has_image_before = False
                has_image_after = False
                # 检查前5行
                for j in range(max(0, i - 5), i):
                    if '![' in lines[j] or '<img' in lines[j] or '](http' in lines[j] or '](data:' in lines[j]:
                        has_image_before = True
                        break
                # 检查后5行
                for j in range(i + 1, min(len(lines), i + 6)):
                    if '![' in lines[j] or '<img' in lines[j] or '](http' in lines[j] or '](data:' in lines[j]:
                        has_image_after = True
                        break
                # 如果前后都没有图片，删除这个说明
                if not has_image_before and not has_image_after:
                    i += 1
                    continue
        
        # 模式1.5: 行内括号内的图片说明（如文本中的"（不同步的悬浮照|2018.06|大东山谷 摄）"）
        # 在行内查找并删除括号内的图片说明
        if not is_caption and stripped:
            # 查找括号内的图片说明并删除（更精确的匹配）
            # 匹配包含"摄"、"照"、"|"等关键词的括号内容
            line_cleaned = re.sub(r'[（(][^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子)[^）)]*[）)]', '', line)
            if line_cleaned != line:
                line = line_cleaned.strip()
                if not line:  # 如果删除后行为空，跳过
                    i += 1
                    continue
        
        # 模式2: 斜体或加粗的图片说明（原有逻辑）
        if not is_caption and i < len(lines) - 1:
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if (stripped and 
                len(stripped) < 50 and 
                (not next_line.strip() or next_line.strip().startswith(('#', '*', '-', '1.', '2.')))):
                caption_keywords = ['图片', '图', 'photo', 'image', '©', '来源', 'via']
                if any(keyword in stripped for keyword in caption_keywords):
                    is_caption = True
                    has_image_before = False
                    has_image_after = False
                    for j in range(max(0, i - 3), i):
                        if '![' in lines[j] or '<img' in lines[j] or '](http' in lines[j] or '](data:' in lines[j]:
                            has_image_before = True
                            break
                    for j in range(i + 1, min(len(lines), i + 3)):
                        if '![' in lines[j] or '<img' in lines[j] or '](http' in lines[j] or '](data:' in lines[j]:
                            has_image_after = True
                            break
                    if not has_image_before and not has_image_after:
                        i += 1
                        continue
        
        cleaned_lines.append(line)
        i += 1
    return "\n".join(cleaned_lines)


def strip_promo_head(md: str) -> str:
    """清理文章开头的推广内容"""
    lines = md.split("\n")
    start_idx = 0
    # 跳过 front-matter
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start_idx = i + 1
                break
    
    # 从开头开始查找，找到第一个非推广内容
    for idx in range(start_idx, min(start_idx + 10, len(lines))):  # 只检查前10行
        s = lines[idx].strip()
        if not s:
            continue
        # 检查是否是推广内容
        is_promo = False
        for pat in PROMO_HEAD_PATTERNS:
            if re.search(pat, s, re.IGNORECASE):
                is_promo = True
                break
        # 如果找到非推广内容，停止
        if not is_promo and len(s) > 5:  # 至少5个字符，避免误删
            break
        # 如果是推广内容，标记为删除
        if is_promo:
            start_idx = idx + 1
    
    return "\n".join(lines[start_idx:])


def strip_promo_tail(md: str) -> str:
    """清理文章末尾的推广内容"""
    lines = md.split("\n")
    cut_idx = None
    
    # 从后往前查找，找到第一个推广内容标记
    for idx in range(len(lines) - 1, -1, -1):
        s = lines[idx].strip()
        if not s:
            continue
        # 检查是否是推广标记
        for pat in PROMO_TAIL_PATTERNS:
            if re.search(pat, s, re.IGNORECASE):
                cut_idx = idx
                break
        # 额外检查：如果包含"感谢关注"或"求关注"且包含"近期"或"推荐"，也认为是推广内容
        if cut_idx is None:
            if ("感谢关注" in s or "求关注" in s) and ("近期" in s or "推荐" in s or "原创" in s):
                cut_idx = idx
                break
        if cut_idx is not None:
            break
    
    if cut_idx is None:
        # 如果没有找到明确的推广标记，检查是否有微信公众号链接或广告内容
        for idx in range(len(lines) - 1, max(0, len(lines) - 20), -1):  # 只检查最后20行
            s = lines[idx].strip()
            if "mp.weixin.qq.com" in s or "__biz=" in s:
                cut_idx = idx
                break
            # 检查是否包含"感谢关注"、"近期"等关键词（更宽松的匹配）
            if ("感谢关注" in s or "求关注" in s) and ("近期" in s or "推荐" in s or "原创" in s or "公众号" in s):
                cut_idx = idx
                break
    
    if cut_idx is None:
        return md.strip()
    
    # 向上查找，删除推广标记之前的所有空行和链接
    while cut_idx > 0:
        prev_line = lines[cut_idx - 1].strip()
        # 如果前一行是空行，继续向上
        if not prev_line:
            cut_idx -= 1
        # 如果前一行包含微信公众号链接，也删除
        elif "mp.weixin.qq.com" in prev_line or "__biz=" in prev_line:
            cut_idx -= 1
        # 如果前一行看起来像文章推荐标题（短行，可能是链接）
        elif len(prev_line) < 30 and ("[" in prev_line or "http" in prev_line):
            cut_idx -= 1
        else:
            break
    
    # 确保删除推广标记行本身
    result = "\n".join(lines[:cut_idx]).rstrip()
    
    # 再次检查，确保末尾没有推广内容残留
    result_lines = result.split("\n")
    for idx in range(len(result_lines) - 1, max(0, len(result_lines) - 5), -1):
        s = result_lines[idx].strip()
        if not s:
            continue
        for pat in PROMO_TAIL_PATTERNS:
            if re.search(pat, s, re.IGNORECASE):
                # 找到推广内容，删除从这一行开始的所有内容
                return "\n".join(result_lines[:idx]).rstrip()
        if "mp.weixin.qq.com" in s or "__biz=" in s:
            return "\n".join(result_lines[:idx]).rstrip()
    
    return result


def parse_front_matter(md: str):
    if md.startswith("---\n"):
        end = md.find("\n---\n", 4)
        if end != -1:
            fm = md[4:end].strip()
            body = md[end + 5 :]
            return fm, body
    return None, md


def get_title_from_md(body: str, fallback: str) -> str:
    # 优先找第一行 "# xxx"
    for line in body.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            return normalize_title(m.group(1))
        # 跳过空行/图片等
        if line.strip():
            break
    return normalize_title(fallback)


def load_article_dates():
    """从 articles_list.json 读取 title->timestamp 映射"""
    mapping = {}
    if not os.path.exists(ARTICLES_LIST_FILE):
        return mapping
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)
    for it in items:
        t = normalize_title(it.get("title", ""))
        ts = it.get("timestamp")
        if t and ts:
            mapping[t] = int(ts)
    return mapping


def get_existing_titles():
    titles = set()
    if not os.path.exists(POSTS_DIR):
        return titles
    for p in Path(POSTS_DIR).glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        m = re.search(r"^title:\s*(.+)\s*$", text, re.MULTILINE)
        if m:
            titles.add(normalize_title(m.group(1)))
    return titles


def safe_filename(s: str) -> str:
    s = normalize_title(s)
    s = re.sub(r"[\\/:*?\"<>|]", "_", s)
    s = s.replace(" ", "-")
    s = s[:80].strip("-_")
    return s or "post"


def main():
    os.makedirs(POSTS_DIR, exist_ok=True)

    date_map = load_article_dates()
    existing_titles = get_existing_titles()

    in_files = sorted(Path(IN_DIR).glob("*.md"))
    if not in_files:
        print(f"[ERROR] No markdown files found in: {IN_DIR}")
        print("请先用 Wechatsync 导出 Markdown 到该目录。")
        return 1

    imported = 0
    skipped = 0

    for fp in in_files:
        raw = fp.read_text(encoding="utf-8", errors="ignore")
        fm, body = parse_front_matter(raw)

        title_guess = fp.stem
        title = None
        if fm:
            m = re.search(r"^title:\s*(.+)\s*$", fm, re.MULTILINE)
            if m:
                title = normalize_title(m.group(1))
        if not title:
            title = get_title_from_md(body, title_guess)

        if title in existing_titles:
            print(f"[SKIP] duplicate title: {title}")
            skipped += 1
            continue

        # 处理日期：优先用列表映射；否则从正文中找中文日期；否则用文件mtime
        ts = date_map.get(title)
        if not ts:
            m = DATE_CN_RE.search(raw)
            if m:
                y, mo, d = map(int, m.groups())
                ts = int(datetime(y, mo, d, 0, 0, 0).timestamp())
        if not ts:
            ts = int(fp.stat().st_mtime)

        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

        # 清理文章内容
        # 1. 清理分隔符（dadong*shangu 等）
        body_clean = clean_separators(body)
        
        # 2. 清理开头的推广内容
        body_clean = strip_promo_head(body_clean)
        
        # 3. 清理末尾的推广内容
        body_clean = strip_promo_tail(body_clean)
        
        # 4. 清理微信公众号链接
        body_clean = clean_wechat_links(body_clean)
        
        # 5. 删除没有图片的图片说明
        body_clean = remove_empty_image_captions(body_clean)
        
        # 6. 若正文首行是 "# title"，去掉避免重复显示（可选）
        body_lines = body_clean.splitlines()
        if body_lines and re.match(r"^\s*#\s+", body_lines[0]):
            body_clean = "\n".join(body_lines[1:]).lstrip()
        
        # 7. 清理多余的空行和空白字符
        body_clean = clean_extra_whitespace(body_clean)

        if not fm:
            fm_out = "\n".join(
                [
                    "---",
                    f"title: {title}",
                    f"date: {date_str}",
                    "tags:",
                    "  - 大东山谷精选",
                    "---",
                    "",
                ]
            )
            out_text = fm_out + body_clean.strip() + "\n"
        else:
            # 保留原front-matter，但确保有 date/tags
            fm_lines = fm.splitlines()
            if not any(l.startswith("date:") for l in fm_lines):
                fm_lines.append(f"date: {date_str}")
            if not any(l.startswith("tags:") for l in fm_lines):
                fm_lines.append("tags:")
                fm_lines.append("  - 大东山谷精选")
            fm_out = "---\n" + "\n".join(fm_lines).strip() + "\n---\n\n"
            out_text = fm_out + body_clean.strip() + "\n"

        out_name = f"{datetime.fromtimestamp(ts).strftime('%Y-%m-%d')}-{safe_filename(title)}.md"
        out_path = Path(POSTS_DIR) / out_name
        # 避免文件名冲突
        if out_path.exists():
            suffix = 1
            while True:
                candidate = Path(POSTS_DIR) / f"{out_path.stem}-{suffix}{out_path.suffix}"
                if not candidate.exists():
                    out_path = candidate
                    break
                suffix += 1

        out_path.write_text(out_text, encoding="utf-8")
        existing_titles.add(title)
        imported += 1
        print(f"[OK] imported: {out_path.name}")

    print(f"\n[SUMMARY] imported={imported}, skipped={skipped}, input_files={len(in_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

