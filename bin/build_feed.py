#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_feed.py —— 把自己的情报池发布成标准 RSS 2.0

读 data/items.json，写 out/feed.xml。
out/ 里同时有 index.html 和 feed.xml —— **整个目录就是一个可部署站点**，
扔到 Cloudflare Pages / 任意静态托管就能被订阅。

用法：
    export AINFORMER_BASE_URL=https://your-site.pages.dev
    uv run python bin/build_feed.py
    uv run python bin/build_feed.py --limit 100
    uv run python bin/build_feed.py --days 3
    uv run python bin/build_feed.py --tier official
    uv run python bin/build_feed.py --base-url https://intel.example.com

设计说明：
    - 不做价值筛选。喂什么发什么，判断权不在这层。
    - 但按源设配额（--per-source，默认 10）。这不是判断重要性，是**结构平衡**：
      纯按时间排序会奖励更新频率高的源（AIHOT 两天发 50 条，会把官方源全挤出去），
      按源配额反而更中立 —— 每个源拿一样的份额。
    - 每条带 category，标出源名和层级，订阅方能自己按可信度处理。
    - 只按时间倒序，不按"重要性"排序 —— 那是我做不了的事。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "data" / "items.json"
OUT_PATH = ROOT / "out" / "feed.xml"

DEFAULT_TITLE = "AI 情报池"
DEFAULT_DESC = "由 AInformer 从多个一手源与中文源聚合而成。不做重要性筛选，只按时间排序。"

# 线上地址不写死：atom:link self 必须指向真实部署地址，
# 猜错一次订阅器就拿到错的 URL。由 --base-url 或环境变量提供，缺了直接报错。
BASE_URL_ENV = "AINFORMER_BASE_URL"


def _pub_dt(item: dict) -> datetime | None:
    raw = item.get("published")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def build(items: list[dict], *, title: str, link: str, desc: str, limit: int) -> str:
    now = datetime.now(timezone.utc)
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        f"<title>{escape(title)}</title>",
        f"<link>{escape(link)}</link>",
        f"<description>{escape(desc)}</description>",
        "<language>zh-CN</language>",
        f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>",
        "<generator>ainformer build_feed.py</generator>",
        f'<atom:link href="{escape(link.rstrip("/") + "/feed.xml")}" '
        'rel="self" type="application/rss+xml"/>',
    ]

    for it in items[:limit]:
        dt = _pub_dt(it)
        url = it.get("url") or ""
        if not url:
            continue
        parts.append("<item>")
        parts.append(f"<title>{escape(it.get('title') or '')}</title>")
        parts.append(f"<link>{escape(url)}</link>")
        parts.append(f'<guid isPermaLink="true">{escape(url)}</guid>')
        if dt:
            parts.append(f"<pubDate>{format_datetime(dt)}</pubDate>")
        summary = (it.get("summary") or "").strip()
        if summary:
            parts.append(f"<description>{escape(summary)}</description>")
        # 源名与层级都进 category，订阅方可以据此自己降权聚合源
        parts.append(f"<category>{escape(it.get('source_name') or '')}</category>")
        if it.get("tier"):
            parts.append(f"<category>{escape(it['tier'])}</category>")
        parts.append("</item>")

    parts += ["</channel>", "</rss>", ""]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="把情报池发布成 RSS")
    ap.add_argument("--limit", type=int, default=100, help="最多输出多少条（默认 100）")
    ap.add_argument("--per-source", type=int, default=10,
                    help="单个源最多占多少条（默认 10，0 = 不限）")
    ap.add_argument("--days", type=int, default=0, help="只发最近 N 天（默认不限）")
    ap.add_argument("--tier", default="", help="只要某些层级，逗号分隔：official,media,aggregator")
    ap.add_argument("--title", default=DEFAULT_TITLE)
    ap.add_argument("--desc", default=DEFAULT_DESC)
    ap.add_argument("--base-url", default=None,
                    help=f"部署后的站点根地址，用于 atom:link self（默认取 {BASE_URL_ENV}）")
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    base_url = (args.base_url or os.environ.get(BASE_URL_ENV, "")).strip().rstrip("/")
    if not base_url:
        print(f"缺少站点根地址。设环境变量 {BASE_URL_ENV}，或传 --base-url。", file=sys.stderr)
        print("feed 的 atom:link self 必须指向真实地址，所以这里没有默认值。", file=sys.stderr)
        return 2

    if not ITEMS_PATH.exists():
        print(f"找不到 {ITEMS_PATH}，先跑 bin/fetch.py", file=sys.stderr)
        return 1

    items = json.loads(ITEMS_PATH.read_text(encoding="utf-8")).get("items", [])
    if not items:
        print("items.json 里没有条目", file=sys.stderr)
        return 1

    tiers = {t.strip() for t in args.tier.split(",") if t.strip()}
    if tiers:
        items = [x for x in items if x.get("tier") in tiers]

    if args.days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        items = [x for x in items if (_pub_dt(x) or cutoff) >= cutoff]

    # 有日期的按时间倒序，没日期的垫底 —— 绝不用抓取时间冒充发布时间
    def sort_key(x: dict) -> tuple:
        dt = _pub_dt(x)
        return (dt is None, -(dt.timestamp() if dt else 0.0))

    items.sort(key=sort_key)

    if args.per_source > 0:
        seen: dict[str, int] = {}
        balanced: list[dict] = []
        for x in items:
            sid = x.get("source_id") or ""
            if seen.get(sid, 0) >= args.per_source:
                continue
            seen[sid] = seen.get(sid, 0) + 1
            balanced.append(x)
        items = balanced

    xml = build(items, title=args.title, link=base_url, desc=args.desc, limit=args.limit)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding="utf-8")

    n = min(len(items), args.limit)
    span = ""
    dts = [_pub_dt(x) for x in items[:n] if _pub_dt(x)]
    if dts:
        span = f"，{min(dts):%m-%d %H:%M} → {max(dts):%m-%d %H:%M}"
    srcs = len({x.get("source_id") for x in items[:n]})
    print(f"已写入 {out}")
    print(f"  {n} 条 / {srcs} 个源{span}，{len(xml.encode('utf-8')) / 1024:.1f} KB")
    print(f"  atom:link self = {base_url}/feed.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
