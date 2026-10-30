#!/usr/bin/env python3
"""daily.py —— 生成当天日报：把最新一天的事件按主题分五类，每类配一段概述。

分类和概述有两种模式：
    - 配置了 LLM_API_KEY：用模型分类 + 写概述（推荐，更准）
    - 没配 key：退回关键词启发式分类，概述留空（不阻断，站点仍可用）

职责边界：只做「选今天 + 分类 + 概述 + 组装」，不筛条目、不打重要性分。

用法：
    python3 bin/daily.py                  # 自动取数据里最新的一天
    python3 bin/daily.py --date 2026-10-29
    python3 bin/daily.py --dry-run        # 只打印要发给模型的请求，不调用

产物：
    data/daily/2026-10-29.json   归档（不入库）
    web/public/data/daily.json   前端「今日」入口固定读这份
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import config
import llm

ROOT = Path(__file__).resolve().parent.parent
CLUSTERS_PATH = ROOT / "data" / "clusters.json"
ITEMS_PATH = ROOT / "data" / "items.json"
DAILY_DIR = ROOT / "data" / "daily"
# 前端固定从 /data/daily.json 取，这里每次覆盖最新一份
PUBLIC_OUT = ROOT / "web" / "public" / "data" / "daily.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

STALE_DAYS = 30

SECTIONS = [
    ("product", "产品发布"),
    ("research", "研究进展"),
    ("business", "商业动作"),
    ("policy", "政策监管"),
    ("opinion", "值得留意的观点"),
    ("other", "其他"),
]
CATEGORIES = {key for key, _name in SECTIONS}

# 启发式关键词：没配 LLM key 时用。命中第一个就归入该类。
KEYWORDS: dict[str, list[str]] = {
    "product": [
        "发布",
        "上线",
        "推出",
        "版本",
        "更新",
        "功能",
        "定价",
        "开源",
        "公测",
        "灰度",
        "release",
        "launch",
        "unveil",
        "beta",
        "预览",
        "上新",
        "model",
        "frontier",
        "模型",
    ],
    "research": [
        "论文",
        "基准",
        "benchmark",
        "arxiv",
        "研究",
        "训练",
        "评测",
        "方法",
        "数据集",
        "science",
        "证明",
        "猜想",
        "paper",
        "dataset",
        "training",
    ],
    "business": [
        "融资",
        "收购",
        "估值",
        "上市",
        "ipo",
        "财报",
        "营收",
        "投资",
        "人事",
        "任命",
        "招股",
        "s-1",
        "美元",
        "募资",
        "裁员",
        "funding",
        "valuation",
    ],
    "policy": [
        "监管",
        "法案",
        "合规",
        "诉讼",
        "出口管制",
        "政策",
        "禁令",
        "法院",
        "判",
        "regulat",
        "安全施压",
        "信托",
    ],
    "opinion": [
        "评论",
        "分析",
        "预测",
        "访谈",
        "观点",
        "解读",
        "思考",
        "怎么看",
        "长文",
        "报告",
        "教程",
        "总结",
        "拆解",
    ],
}

CLASSIFY_SYSTEM = (
    "你是 AI 新闻分类器。把每条新闻标题分到以下六类之一：\n"
    "product=产品发布（发布/上线/新版本/新模型/开源/定价）\n"
    "research=研究进展（论文/基准/评测/方法/数据集）\n"
    "business=商业动作（融资/收购/上市/财报/人事）\n"
    "policy=政策监管（监管/法案/诉讼/出口管制）\n"
    "opinion=值得留意的观点（评论/分析/预测/访谈/教程）\n"
    "other=其他（以上都不匹配）\n"
    "只输出一个 JSON 对象：键是事件 ID，值是小写类别名。不要输出任何解释。"
)

SUMMARY_SYSTEM = (
    "你是 AI 情报编辑。给定一类新闻的标题列表，用 2-3 句话概括这一类今天的共同点"
    "或最值得注意的一件事。平实陈述，不用「重磅」「颠覆」「史上最强」这类词，"
    "不逐条复述，不写没有依据的判断。直接输出正文，不要标题。"
)


def classify(title: str) -> str:
    t = title.lower()
    for key, _name in SECTIONS[:-1]:  # 不含 other
        if any(k in t for k in KEYWORDS[key]):
            return key
    return "other"


def latest_day(clusters: list[dict]) -> str:
    days = [m["published"][:10] for c in clusters for m in c["members"] if m["published"]]
    return max(days) if days else ""


def select_today(clusters: list[dict], day: str) -> list[dict]:
    picked = [
        c
        for c in clusters
        if any(m["published"] and m["published"][:10] == day for m in c["members"])
    ]
    picked.sort(key=lambda c: (-c["size"], c["primary"]))
    return picked


def gaps(sources: list[dict], items: list[dict], now: datetime) -> list[str]:
    newest_by: dict[str, str] = {}
    for it in items:
        if not it.get("published"):
            continue
        cur = newest_by.get(it["source_id"])
        if not cur or it["published"] > cur:
            newest_by[it["source_id"]] = it["published"]
    out: list[str] = []
    for s in sources:
        if not s.get("ok"):
            out.append(f"{s['name']} 本轮抓取失败")
            continue
        newest = newest_by.get(s["id"])
        if not newest:
            out.append(f"{s['name']} 60 天内零新增")
            continue
        age = (now - datetime.fromisoformat(newest)).days
        if age > STALE_DAYS:
            out.append(f"{s['name']} 已 {age} 天未更新")
    return out


def apply_mapping(events: list[dict], raw: dict) -> dict[str, str]:
    """把模型的分类结果套到事件上，非法/缺失的落到启发式。"""
    out: dict[str, str] = {}
    for c in events:
        got = raw.get(c["event_id"])
        out[c["event_id"]] = got if got in CATEGORIES else classify(c["members"][0]["title"])
    return out


def classify_llm(events: list[dict], settings: config.Settings) -> dict[str, str]:
    """一次调用分类全部事件，返回 event_id → 类别。非法结果落到启发式。"""
    lines = "\n".join(f"{c['event_id']}: {c['members'][0]['title']}" for c in events)
    raw = llm.chat_json(
        [{"role": "system", "content": CLASSIFY_SYSTEM}, {"role": "user", "content": lines}],
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )
    return apply_mapping(events, raw)


def summarize_llm(section_name: str, titles: list[str], settings: config.Settings) -> str:
    lines = "\n".join(f"- {t}" for t in titles)
    return llm.chat(
        [
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": f"类别：{section_name}\n标题：\n{lines}"},
        ],
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    ).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="生成当天日报")
    ap.add_argument("--date", help="指定日期 YYYY-MM-DD，默认取数据里最新一天")
    ap.add_argument("--dry-run", action="store_true", help="只打印要发给模型的请求，不调用")
    args = ap.parse_args()

    if not CLUSTERS_PATH.exists():
        print(f"找不到 {CLUSTERS_PATH} —— 先跑 bin/cluster.py merge", file=sys.stderr)
        return 1

    settings = config.load(require_base_url=False)
    clusters = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))["clusters"]
    raw = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    sources = raw.get("sources", [])
    items = raw.get("items", [])
    now = datetime.now(UTC)

    day = args.date or latest_day(clusters)
    if not day:
        print("数据里没有任何带日期的条目，无法生成日报", file=sys.stderr)
        return 2

    today = select_today(clusters, day)
    use_llm = bool(settings.llm_api_key)

    if use_llm:
        print(f"模型 {settings.llm_model} @ {settings.llm_base_url}")
        if args.dry_run:
            print("分类请求会发给模型：")
            print("  " + "\n  ".join(f"{c['event_id']}: {c['members'][0]['title']}" for c in today))
            print("概述请求：每个非空分类一次。")
            return 0
        try:
            mapping = classify_llm(today, settings)
        except Exception as exc:
            print(f"LLM 分类失败：{type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
    else:
        print("未配置 LLM_API_KEY，用启发式分类，概述留空。")
        mapping = {c["event_id"]: classify(c["members"][0]["title"]) for c in today}

    by_section: dict[str, list[dict]] = {key: [] for key, _name in SECTIONS}
    for c in today:
        by_section[mapping[c["event_id"]]].append(c)

    sections = []
    for key, name in SECTIONS:
        events = by_section[key]
        if not events:
            continue
        summary = None
        if use_llm:
            try:
                summary = summarize_llm(name, [c["members"][0]["title"] for c in events], settings)
            except Exception as exc:
                # 概述是增强不是核心，失败只留空，不阻断整份日报
                print(f"  概述「{name}」失败：{type(exc).__name__}", file=sys.stderr)
        sections.append(
            {
                "key": key,
                "name": name,
                "summary": summary,
                "events": [
                    {
                        "event_id": c["event_id"],
                        "title": c["members"][0]["title"],
                        "size": c["size"],
                        "tier": c["members"][0]["tier"],
                        "url": c["members"][0]["url"],
                        "published": c["members"][0]["published"],
                    }
                    for c in events
                ],
            }
        )

    payload = {
        "date": day,
        "generated_at": now.isoformat(),
        "coverage": {
            "events": len(today),
            "items": sum(c["size"] for c in today),
            "sources_ok": sum(1 for s in sources if s.get("ok")),
            "sources_total": len(sources),
        },
        "sections": sections,
        "gaps": gaps(sources, items, now),
    }

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    out = DAILY_DIR / f"{day}.json"
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    out.write_text(text, encoding="utf-8")
    PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.write_text(text, encoding="utf-8")

    print(f"{day} · 事件 {len(today)} · 分 {len(sections)} 类 · 缺口 {len(payload['gaps'])} 个")
    for s in sections:
        print(f"  {s['name']:<8} {len(s['events'])} 件{' · 概述 ✓' if s['summary'] else ''}")
    print(f"写入 {out.relative_to(ROOT)}、{PUBLIC_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
