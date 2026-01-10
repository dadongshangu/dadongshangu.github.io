#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将浏览器提取的 articles_new_raw.json 清洗成标准 articles_list.json
输出字段：title / url(https) / timestamp(unix, 00:00:00)
"""

import json
import os
import re
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_FILE = os.path.join(DATA_DIR, "articles_new_raw.json")
OUT_FILE = os.path.join(DATA_DIR, "articles_list.json")


DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")


def to_https(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return url


def extract_date_timestamp(text: str):
    m = DATE_RE.search(text or "")
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    # 以 Asia/Shanghai 的日期 00:00:00 作为时间戳（避免时区偏差）
    dt = datetime(y, mo, d, 0, 0, 0)
    # 直接用本地时间戳（Windows本地一般是Asia/Shanghai；如需严格可改为pytz）
    return int(dt.timestamp())


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def clean_title(raw_title: str) -> str:
    s = normalize_ws(raw_title)
    # 去掉末尾日期
    s = DATE_RE.sub("", s).strip()
    # 去掉开头编号
    s = re.sub(r"^\d+\.\s*", "", s)
    # 去掉中间可能重复出现的“编号.”
    s = re.sub(r"\s+\d+\.\s*", " ", s).strip()
    # 再次压缩空格
    s = normalize_ws(s)

    # 去重：如果是 “标题 标题” 这种形式，保留一份
    tokens = s.split(" ")
    if len(tokens) >= 2 and len(tokens) % 2 == 0:
        half = len(tokens) // 2
        if tokens[:half] == tokens[half:]:
            s = " ".join(tokens[:half]).strip()

    return s or "未命名文章"


def main():
    if not os.path.exists(RAW_FILE):
        raise SystemExit(f"Missing {RAW_FILE}")

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    cleaned = []
    seen = set()
    for item in raw_items:
        url = to_https(item.get("url", ""))
        title_raw = item.get("title", "")
        title = clean_title(title_raw)
        ts = extract_date_timestamp(title_raw) or item.get("timestamp")

        # 用去掉参数的主链接做去重key（保持稳定）
        url_key = url.split("#", 1)[0]
        url_key = url_key.split("&chksm=", 1)[0]
        if url_key in seen:
            continue
        seen.add(url_key)

        cleaned.append(
            {
                "title": title,
                "url": url,
                "timestamp": ts,
            }
        )

    # 新的在前
    cleaned.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"[OK] cleaned articles: {len(cleaned)} -> {OUT_FILE}")


if __name__ == "__main__":
    main()

