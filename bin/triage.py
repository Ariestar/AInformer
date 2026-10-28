#!/usr/bin/env python3
"""
triage.py —— Jev 判断层

只有一条路径：TypeSafe Jev。没有规则引擎，没有降级，没有兜底。

没有 TYPESAFE_API_KEY 就跑不起来 —— 这是故意的。
一个声称能判断的层，在判断不了的时候假装判断了，比直接报错更坏。

它只回答**事实判断**：
    1. 这条属不属于 AI 领域        is_ai_related
    2. 这条是什么类型              topic
    3. 这条是既成事实还是观点      is_announcement

它不做：排序、打重要性分、筛选、隐藏条目。判断权在人。

用法：
    export TYPESAFE_API_KEY=...
    python bin/triage.py
    python bin/triage.py --dry-run     # 只打印请求体，不调用、不写文件

端点：
    默认 https://api.typesafe.ai/v1/systemone
    官方未向中国大陆开放，可设 TYPESAFE_BASE_URL 指向兼容中转
    （OpenRouter / TaoToken 等），模型 ID 用 JEV_MODEL 覆盖。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "data" / "items.json"
OUT_PATH = ROOT / "data" / "triage.json"

_SETTINGS = config.load(require_base_url=False)
JEV_BASE = _SETTINGS.typesafe_base
JEV_ENDPOINT = JEV_BASE + "/v1/systemone"
JEV_MODEL = _SETTINGS.jev_model
TIMEOUT = 30

# 限流与服务过载要退避重试 —— 这是官方 SDK 的既定行为，不是降级。
RETRY_CODES = {429, 529}
MAX_ATTEMPTS = 3

# ---------------------------------------------------------------- 问题设计
# 三条原则：判断要窄、state 要结构化、只问客观可验证的事。
# 注意：questions 的键名不参与推理，语义必须写在 instructions / criteria 里。
QUESTIONS = {
    "is_ai_related": {
        "type": "noul",
        "instructions": (
            "判断这条资讯的核心主题是否属于人工智能领域，包括大模型、机器学习、"
            "AI 产品与工具、AI 公司动态、AI 监管政策、AI 芯片与算力。"
            "如果 AI 只是文章顺带提及、主体是其他行业，判为否。"
        ),
    },
    "topic": {
        "type": "choice",
        "instructions": "这条资讯的主要内容属于哪一类？",
        "criteria": {
            "产品": "发布、上线、版本更新、新功能、定价调整",
            "研究": "论文、技术方法、模型能力评测、实验结果",
            "商业": "融资、收购、估值、营收、人事变动",
            "政策": "监管、法案、合规、诉讼、出口管制",
            "观点": "评论、分析、预测、访谈，没有新的事实发生",
            "其他": "以上都不是",
        },
    },
    "is_announcement": {
        "type": "noul",
        "instructions": (
            "这条资讯是否在陈述一个已经发生、可验证的事实（发布、上线、融资、判决等）？"
            "如果主要是观点、预测或评论，判为否。"
        ),
    },
}


def _key(item: dict) -> str:
    raw = item.get("url") or item.get("title") or ""
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _state(item: dict) -> dict:
    return {
        "title": item.get("title") or "",
        "summary": (item.get("summary") or "")[:600],
        "source": item.get("source_name") or "",
        "published": item.get("published") or "",
    }


def _post(body: dict, api_key: str) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    delay = 1.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(
            JEV_ENDPOINT,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ainformer-triage/2.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in RETRY_CODES and attempt < MAX_ATTEMPTS:
                print(
                    f"    HTTP {e.code}，{delay:.0f}s 后重试（{attempt}/{MAX_ATTEMPTS}）",
                    file=sys.stderr,
                )
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("重试耗尽")


def _parse(payload: dict) -> tuple[dict, str]:
    """响应字段是 answers，不是 choices。版本号回显在顶层。"""
    ans = payload.get("answers")
    if not isinstance(ans, dict):
        raise ValueError(f"响应里没有 answers 字段，实际顶层键：{list(payload)[:8]}")

    ai = ans.get("is_ai_related") or {}
    tp = ans.get("topic") or {}
    an = ans.get("is_announcement") or {}
    version = payload.get("model") or payload.get("version") or JEV_MODEL

    return {
        "is_ai_related": round(float(ai.get("noul", 0.0)), 3),
        "topic": tp.get("choice") or "其他",
        "topic_conf": round(float(tp.get("confidence", 0.0)), 3),
        "topic_probs": {k: round(float(v), 3) for k, v in (tp.get("probabilities") or {}).items()},
        "is_announcement": round(float(an.get("noul", 0.0)), 3),
    }, version


def main() -> int:
    ap = argparse.ArgumentParser(description="AI 情报的 Jev 判断层")
    ap.add_argument("--dry-run", action="store_true", help="只打印请求体，不调用、不写文件")
    args = ap.parse_args()

    if not ITEMS_PATH.exists():
        print(f"找不到 {ITEMS_PATH}，先跑 bin/fetch.py", file=sys.stderr)
        return 1

    items = json.loads(ITEMS_PATH.read_text(encoding="utf-8")).get("items", [])
    if not items:
        print("items.json 里没有条目", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"端点 {JEV_ENDPOINT} · 模型 {JEV_MODEL} · 条目 {len(items)}")
        print("将要发送的请求体（第一条）：")
        print(
            json.dumps(
                {"model": JEV_MODEL, "state": _state(items[0]), "questions": QUESTIONS},
                ensure_ascii=False,
                indent=2,
            )
        )
        print("\n--dry-run：未调用接口，未写入任何文件。")
        return 0

    api_key = _SETTINGS.typesafe_key
    if not api_key:
        print("未设置 TYPESAFE_API_KEY。", file=sys.stderr)
        print("", file=sys.stderr)
        print("这个脚本没有降级路径 —— 没有 key 就没有判断。", file=sys.stderr)
        print("官方端点未向中国大陆开放，可以：", file=sys.stderr)
        print("  1) 设 TYPESAFE_BASE_URL 指向兼容中转（OpenRouter / TaoToken）", file=sys.stderr)
        print("  2) 用开源复现版自建（如 APUS fast-browser-use，MIT）", file=sys.stderr)
        print("  3) 不跑这一层。data/triage.json 缺失时下游应当正常工作。", file=sys.stderr)
        return 2

    print(f"端点 {JEV_ENDPOINT} · 模型 {JEV_MODEL} · 条目 {len(items)}")

    results: dict[str, dict] = {}
    version = JEV_MODEL

    for i, item in enumerate(items, 1):
        title = (item.get("title") or "")[:50]
        try:
            payload = _post(
                {"model": JEV_MODEL, "state": _state(item), "questions": QUESTIONS}, api_key
            )
            parsed, version = _parse(payload)
            results[_key(item)] = parsed
        except Exception as e:
            # 不替换、不跳过、不猜。一条判不了就整体失败，让人看见。
            print(f"\n第 {i} 条失败：{title}", file=sys.stderr)
            print(f"  {type(e).__name__}: {e}", file=sys.stderr)
            print(
                "  未写入 data/triage.json —— 宁可没有结果，也不要半真半假的结果。", file=sys.stderr
            )
            return 1

        if i % 10 == 0 or i == len(items):
            print(f"  {i}/{len(items)}")

    out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "engine": version,
        "endpoint": JEV_ENDPOINT,
        "note": "本文件只做事实标注，不排序、不筛选；判断权仍在人。",
        "questions": {k: v["type"] for k, v in QUESTIONS.items()},
        "items": results,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    ai_n = sum(1 for v in results.values() if v["is_ai_related"] >= 0.5)
    ann_n = sum(1 for v in results.values() if v["is_announcement"] >= 0.5)
    topic_dist: dict[str, int] = {}
    for v in results.values():
        topic_dist[v["topic"]] = topic_dist.get(v["topic"], 0) + 1
    low = sorted(
        (
            (v["is_ai_related"], (items[k].get("title") or "")[:56])
            for k, v in results.items()
            if v["is_ai_related"] < 0.5
        ),
        key=lambda x: x[0],
    )

    print(f"\n已写入 {OUT_PATH.relative_to(ROOT)}（引擎 {version}）")
    print(f"  AI 相关 {ai_n} / {len(results)}（阈值 0.5，只标注不隐藏）")
    print(f"  既成事实 {ann_n} / {len(results)}，其余为观点/预测")
    print(
        "  类型分布 "
        + "、".join(f"{k} {v}" for k, v in sorted(topic_dist.items(), key=lambda x: -x[1]))
    )
    if low:
        print("\n  低 AI 相关度（仅供参考，未从池中移除）：")
        for s, t in low[:8]:
            print(f"    {s:.2f}  {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
