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


def strip_promo_tail(md: str) -> str:
    lines = md.split("\n")
    cut_idx = None
    for idx in range(len(lines) - 1, -1, -1):
        s = lines[idx].strip()
        if not s:
            continue
        for pat in PROMO_TAIL_PATTERNS:
            if re.search(pat, s, re.IGNORECASE):
                cut_idx = idx
                break
        if cut_idx is not None:
            break
    if cut_idx is None:
        return md.strip()
    while cut_idx > 0 and not lines[cut_idx - 1].strip():
        cut_idx -= 1
    return "\n".join(lines[:cut_idx]).rstrip()


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

        # 清理尾部引流
        body_clean = strip_promo_tail(body)

        # 若正文首行是 "# title"，去掉避免重复显示（可选）
        body_lines = body_clean.splitlines()
        if body_lines and re.match(r"^\s*#\s+", body_lines[0]):
            body_clean = "\n".join(body_lines[1:]).lstrip()

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

