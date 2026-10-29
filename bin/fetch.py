#!/usr/bin/env python3
"""拉取 RSS/Atom 源，标准化成统一结构。

职责边界：只做 IO 和格式归一。
不做判断、不做排序以外的加工、不写文案。
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
import zlib
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

import config

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "sources.toml"
DATA = ROOT / "data"

ATOM = "{http://www.w3.org/2005/Atom}"
NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def strip_html(raw: str) -> str:
    if not raw:
        return ""
    s = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", unescape(s)).strip()


def parse_date(raw: str | None) -> datetime | None:
    """RSS 用 RFC 2822，Atom 用 ISO 8601。解析不出来就返回 None，不要猜。"""
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def fetch_bytes(url: str, timeout: int, ua: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": ua, "Accept": "application/rss+xml, application/xml, text/xml, */*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        blob = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
    # 有些源即使没请求压缩也会返回 gzip，urllib 不会自动解压。
    # 不解压的话 XML 解析会在第 1 字节就失败，整个源被静默丢掉。
    if enc == "gzip":
        blob = gzip.decompress(blob)
    elif enc == "deflate":
        try:
            blob = zlib.decompress(blob)
        except zlib.error:
            blob = zlib.decompress(blob, -zlib.MAX_WBITS)
    return blob


def parse_feed(blob: bytes) -> list[dict]:
    """同时支持 RSS 2.0 与 Atom。"""
    try:
        root = ET.fromstring(blob)
    except ET.ParseError as exc:
        raise ValueError(f"XML 解析失败：{exc}") from exc

    out: list[dict] = []

    if root.tag.endswith("feed"):  # Atom
        for entry in root.findall(f"{ATOM}entry"):
            title = strip_html(entry.findtext(f"{ATOM}title") or "")
            link = ""
            for ln in entry.findall(f"{ATOM}link"):
                if ln.get("rel", "alternate") == "alternate" and ln.get("href"):
                    link = ln.get("href", "")
                    break
            if not link:
                link = entry.findtext(f"{ATOM}id") or ""
            date = parse_date(
                entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated")
            )
            summary = strip_html(
                entry.findtext(f"{ATOM}summary") or entry.findtext(f"{ATOM}content") or ""
            )
            out.append({"title": title, "url": link, "published": date, "summary": summary})
        return out

    channel = root.find("channel")
    if channel is None:
        raise ValueError("既不是 Atom feed，也找不到 channel")

    for item in channel.findall("item"):
        title = strip_html(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        if not link:
            guid = item.findtext("guid")
            if guid and guid.startswith("http"):
                link = guid.strip()
        date = parse_date(item.findtext("pubDate") or item.findtext(f"{{{NS['dc']}}}date"))
        body = item.findtext(f"{{{NS['content']}}}encoded") or item.findtext("description") or ""
        out.append(
            {"title": title, "url": link, "published": date, "summary": strip_html(body)[:400]}
        )
    return out


def canon_url(url: str) -> str:
    url = url.split("#")[0]
    return re.sub(r"[?&](utm_[^=&]+|ref|source)=[^&]*", "", url).rstrip("/?")


def title_key(title: str) -> str:
    return re.sub(r"[\s\W_]+", "", title.lower())[:40]


def load_config() -> dict:
    with CONFIG.open("rb") as fh:
        return tomllib.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=None, help="覆盖 sources.toml 里的时间窗")
    ap.add_argument("--out", default=str(DATA / "items.json"))
    args = ap.parse_args()

    cfg = load_config()
    fc = cfg.get("fetch", {})
    settings = config.load(require_base_url=False)
    days = args.days if args.days is not None else fc.get("days", settings.fetch_days)
    timeout = fc.get("timeout", 20)
    ua = fc.get("user_agent") or settings.user_agent
    cap = fc.get("max_per_source", 15)
    blacklist = [w.lower() for w in cfg.get("filter", {}).get("blacklist", [])]

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=days)

    items: list[dict] = []
    source_report: list[dict] = []

    for src in cfg.get("source", []):
        sid = src["id"]
        rec = {"id": sid, "name": src["name"], "ok": False, "fetched": 0, "kept": 0, "error": None}
        try:
            blob = fetch_bytes(src["url"], timeout, ua)
            entries = parse_feed(blob)
            rec["ok"] = True
            rec["fetched"] = len(entries)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as exc:
            rec["error"] = f"{type(exc).__name__}: {exc}"
            source_report.append(rec)
            print(f"[FAIL] {sid}: {rec['error']}", file=sys.stderr)
            continue

        kept = 0
        for e in entries:
            if not e["title"] or not e["url"]:
                continue
            pub = e["published"]
            if pub is not None and pub < cutoff:
                continue
            hay = (e["title"] + " " + e["summary"]).lower()
            if any(w in hay for w in blacklist):
                continue
            if kept >= cap:
                break
            kept += 1
            items.append(
                {
                    "source_id": sid,
                    "source_name": src["name"],
                    "tier": src.get("tier", "media"),
                    "weight": src.get("weight", 0.5),
                    "title": e["title"],
                    "url": e["url"],
                    "published": pub.isoformat() if pub else None,
                    "summary": e["summary"][:400],
                    "fetched_at": now.isoformat(),
                }
            )
        rec["kept"] = kept
        source_report.append(rec)
        flag = "ok  " if kept else "zero"
        print(f"[{flag}] {sid:<16} 拉到 {rec['fetched']:>3} 条，窗口内保留 {kept:>2} 条")

    # 去重：先按 URL，再按标题指纹
    seen_url, seen_title, deduped = set(), set(), []
    for it in items:
        u, t = canon_url(it["url"]), title_key(it["title"])
        if u in seen_url or t in seen_title:
            continue
        seen_url.add(u)
        seen_title.add(t)
        deduped.append(it)

    deduped.sort(
        key=lambda x: (x["published"] is None, _neg_str(x["published"] or ""), -x["weight"])
    )

    payload = {
        "generated_at": now.isoformat(),
        "window_days": days,
        "cutoff": cutoff.isoformat(),
        "stats": {
            "sources_total": len(source_report),
            "sources_ok": sum(1 for r in source_report if r["ok"]),
            "raw_items": len(items),
            "after_dedup": len(deduped),
        },
        "sources": source_report,
        "items": deduped,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    s = payload["stats"]
    print(
        f"\n源 {s['sources_ok']}/{s['sources_total']} 正常 | 原始 {s['raw_items']} 条 | 去重后 {s['after_dedup']} 条"
    )
    print(f"写入 {out_path}")
    return 0 if s["sources_ok"] else 1


def _neg_str(s: str) -> str:
    """让字符串按倒序参与排序（时间新的在前）。"""
    return "".join(chr(0x10FFFF - ord(c)) for c in s)


if __name__ == "__main__":
    raise SystemExit(main())
