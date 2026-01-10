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
    r"原创推荐[：:]",
    r"关注公众号",
    r"长按.*(识别|关注)",
    r"点击.*(关注|进入)",
    r"微信公众",
    r"mp\.weixin\.qq\.com",
    r"往期精彩回顾",
    r"文章推荐",
    r"推荐阅读",
    r"相关阅读",
    r"精彩回顾",
    r"往期回顾",
    r"历史文章",
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
    """清理微信公众号链接"""
    # 删除包含 mp.weixin.qq.com 的链接行
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # 跳过包含微信公众号链接的行
        if "mp.weixin.qq.com" in line or "__biz=" in line:
            continue
        # 删除行内的微信公众号链接，但保留其他内容
        line = re.sub(r'\[([^\]]+)\]\(https?://[^\)]*mp\.weixin\.qq\.com[^\)]*\)', r'\1', line)
        line = re.sub(r'https?://[^\s]*mp\.weixin\.qq\.com[^\s]*', '', line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def remove_empty_image_captions(text: str) -> str:
    """删除没有图片的图片说明"""
    lines = text.split("\n")
    cleaned_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 检查是否是图片说明（通常是单独一行，可能是斜体或加粗）
        is_caption = False
        if i < len(lines) - 1:
            # 检查下一行是否是空行或新段落
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            # 如果当前行看起来像图片说明（短行，可能包含图片相关文字），且下一行是空行或新内容
            if (line.strip() and 
                len(line.strip()) < 50 and 
                (not next_line.strip() or next_line.strip().startswith(('#', '*', '-', '1.', '2.')))):
                # 检查是否包含图片说明关键词
                caption_keywords = ['图片', '图', 'photo', 'image', '©', '来源', 'via']
                if any(keyword in line for keyword in caption_keywords):
                    is_caption = True
                    # 检查前后是否有图片链接
                    has_image_before = False
                    has_image_after = False
                    # 检查前几行
                    for j in range(max(0, i - 3), i):
                        if '![' in lines[j] or '<img' in lines[j] or '](http' in lines[j]:
                            has_image_before = True
                            break
                    # 检查后几行
                    for j in range(i + 1, min(len(lines), i + 3)):
                        if '![' in lines[j] or '<img' in lines[j] or '](http' in lines[j]:
                            has_image_after = True
                            break
                    # 如果前后都没有图片，删除这个说明
                    if not has_image_before and not has_image_after:
                        i += 1
                        continue
        if not is_caption:
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
        if cut_idx is not None:
            break
    
    if cut_idx is None:
        # 如果没有找到明确的推广标记，检查是否有微信公众号链接
        for idx in range(len(lines) - 1, max(0, len(lines) - 20), -1):  # 只检查最后20行
            s = lines[idx].strip()
            if "mp.weixin.qq.com" in s or "__biz=" in s:
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
        # 1. 清理开头的推广内容
        body_clean = strip_promo_head(body)
        
        # 2. 清理末尾的推广内容
        body_clean = strip_promo_tail(body_clean)
        
        # 3. 清理微信公众号链接
        body_clean = clean_wechat_links(body_clean)
        
        # 4. 删除没有图片的图片说明
        body_clean = remove_empty_image_captions(body_clean)
        
        # 5. 若正文首行是 "# title"，去掉避免重复显示（可选）
        body_lines = body_clean.splitlines()
        if body_lines and re.match(r"^\s*#\s+", body_lines[0]):
            body_clean = "\n".join(body_lines[1:]).lstrip()
        
        # 6. 清理多余的空行
        body_clean = re.sub(r"\n{3,}", "\n\n", body_clean).strip()

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

