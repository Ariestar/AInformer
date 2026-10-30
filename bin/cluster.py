#!/usr/bin/env python3
"""cluster.py —— 事件归并：召回 →（agent 判定）→ 校验 → 合并

职责边界：只做「这条资讯属于哪个事件」的机械部分。
不判断同一性（那是 agent 的外部产物），不排序、不打分、不筛选、不删条目。

三个模式：
    cluster.py prepare   召回候选对，切批写进 .work/inbox/，复制任务契约
    cluster.py merge     校验 outbox 契约 + 合并成 data/clusters.json
    cluster.py eval      对人工标注算 precision / recall / 错合并数

设计说明：
    - 条目只增不减：n 条进，n 条出，分进若干事件，覆盖率必须 100%。
    - 主源由本脚本按 (层级, 最早发布时间) 选出，不由模型选。模型判错也改不了一手源。
    - 错合并比漏合并更糟：非传递的矛盾边一律拒绝，宁可留两个簇。
    - 退出码 3 专指「agent 产物违约」，publish.py 据此中止，不让半成品上线。

为什么召回分两条通道：
    标题三元组只在同一语言内有效。「Google DeepMind 发布 Gemini 4 Carbon」和英文
    官网原文的字符几乎不重合，但共享 Gemini / Carbon 两个专名。只靠标题通道，
    跨源合并基本进不了候选 —— 实测跨源对从 21 涨到 154 全靠第二条通道。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

import config
import llm

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "data" / "items.json"
WORK = ROOT / ".work"
CLUSTERS_PATH = ROOT / "data" / "clusters.json"
CONTRACT_SRC = ROOT / "docs" / "事件归并契约.md"

TIER_RANK = {"official": 0, "media": 1, "aggregator": 2}
MERGE_THRESHOLD = 0.85
MAX_REASON = 20
FIELDS = {"pair_id", "same_event", "confidence", "reason"}

WORD = re.compile(r"[a-z][a-z0-9][a-z0-9.\-]{1,}")
PUNCT = re.compile(r"[\s\W_]+", re.UNICODE)

# 只去掉纯语法词。别把 ai / new 这类领域词去掉。
STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "you",
    "your",
    "are",
    "was",
    "were",
    "has",
    "have",
    "will",
    "can",
    "but",
    "its",
    "his",
    "her",
    "they",
    "them",
    "their",
    "our",
    "out",
    "into",
    "than",
    "then",
    "now",
    "more",
    "most",
    "all",
    "any",
    "one",
    "two",
    "how",
    "why",
    "what",
    "when",
    "who",
    "com",
    "www",
    "http",
    "https",
    "amp",
    "via",
    "per",
    "about",
    "after",
    "before",
    "over",
    "under",
    "just",
    "also",
    "very",
    "much",
    "some",
    "such",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def rel(p: Path) -> str:
    """相对项目根的显示路径；根外路径（如 --out /tmp/x）原样返回，不要在这里炸。"""
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


# ---------------------------------------------------------------- 文本工具
def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"https?://\S+", " ", s)
    return PUNCT.sub("", s)


def grams(s: str, n: int = 3) -> set[str]:
    t = norm(s)
    if not t:
        return set()
    if len(t) <= n:
        return {t}
    return {t[i : i + n] for i in range(len(t) - n + 1)}


def words(s: str) -> set[str]:
    return {w for w in WORD.findall(s.lower()) if w not in STOP and len(w) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def title_core(s: str) -> str:
    """去掉数字后的标题骨架。「橘鸦AI早报 10-24」和「… 10-26」应视为同栏目。"""
    return PUNCT.sub("", re.sub(r"\d+", "", s.lower()))


def parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def same_day(a: datetime | None, b: datetime | None) -> bool:
    return a is not None and b is not None and a.date() == b.date()


def item_id(it: dict) -> str:
    return it.get("id") or hashlib.sha1(it["url"].encode()).hexdigest()[:12]


def pair_id(url_a: str, url_b: str) -> str:
    a, b = sorted([url_a, url_b])
    return hashlib.sha1(f"{a}\n{b}".encode()).hexdigest()[:12]


# ---------------------------------------------------------------- prepare
def recall(
    items: list[dict], hours: int, min_jac: float, min_words: int, max_df: int, keep_serial: bool
) -> tuple[dict[str, tuple[float, dict, dict]], int, list[dict]]:
    """返回 (pair_id → (分数, a, b), 被丢弃的栏目对数量, 无法配对的条目)。"""
    pre, unpairable = [], []
    for it in items:
        core = title_core(it.get("title") or "")
        if not core:
            # 标题只有日期（如「2026-10-29」的日报），没有可用于匹配的语义。
            # 不参与归并，在 merge 里作为单例保留 —— 不猜，也不丢。
            unpairable.append(
                {
                    "id": item_id(it),
                    "url": it["url"],
                    "source": it.get("source_name") or "",
                    "title": it.get("title") or "",
                }
            )
            continue
        pre.append(
            {
                "it": it,
                "g": grams(it["title"]),
                "w": words(it["title"] + " " + (it.get("summary") or "")),
                "t": parse_ts(it.get("published")),
                "core": core,
            }
        )

    cands: dict[str, tuple[float, dict, dict]] = {}
    dropped_serial = 0

    # 通道一：标题三元组 + 共享实词
    for x, y in combinations(pre, 2):
        both = x["t"] is not None and y["t"] is not None
        if both and abs((x["t"] - y["t"]).total_seconds()) / 3600 > hours:
            continue
        if not keep_serial and x["core"] == y["core"] and not same_day(x["t"], y["t"]):
            dropped_serial += 1
            continue
        jac = jaccard(x["g"], y["g"])
        shared = len(x["w"] & y["w"])
        hit = (jac >= min_jac or shared >= min_words) if both else jac >= 0.55
        if not hit:
            continue
        pid = pair_id(x["it"]["url"], y["it"]["url"])
        cands[pid] = (jac + 0.08 * min(shared, 8), x["it"], y["it"])

    # 通道二：稀有专名共现（跨语言、跨源）
    df: dict[str, int] = {}
    for p in pre:
        for t in p["w"]:
            df[t] = df.get(t, 0) + 1
    inverted: dict[str, list[dict]] = {}
    for p in pre:
        for t in p["w"]:
            if df[t] <= max_df:
                inverted.setdefault(t, []).append(p)

    co: dict[str, int] = {}
    for ps in inverted.values():
        if len(ps) < 2:
            continue
        for x, y in combinations(ps, 2):
            if not x["t"] or not y["t"]:
                continue
            if abs((x["t"] - y["t"]).total_seconds()) / 3600 > hours:
                continue
            pid = pair_id(x["it"]["url"], y["it"]["url"])
            co[pid] = co.get(pid, 0) + 1
            score, a, b = cands.get(pid, (0.0, x["it"], y["it"]))
            cands[pid] = (max(score, 0.45 + 0.06 * min(co[pid], 8)), a, b)

    return cands, dropped_serial, unpairable


def cap_pairs(
    cands: dict[str, tuple[float, dict, dict]], max_degree: int, max_pairs: int
) -> list[tuple[float, str, dict, dict]]:
    ordered = sorted(cands.items(), key=lambda kv: (-kv[1][0], kv[0]))
    degree: dict[str, int] = {}
    kept: list[tuple[float, str, dict, dict]] = []
    for pid, (score, a, b) in ordered:
        ia, ib = item_id(a), item_id(b)
        if degree.get(ia, 0) >= max_degree or degree.get(ib, 0) >= max_degree:
            continue
        degree[ia] = degree.get(ia, 0) + 1
        degree[ib] = degree.get(ib, 0) + 1
        kept.append((score, pid, a, b))
        if len(kept) >= max_pairs:
            break
    return kept


def side(it: dict) -> dict:
    """给 agent 看的一侧。摘要截断，控制上下文成本。"""
    return {
        "source": it.get("source_name") or "",
        "tier": it.get("tier") or "",
        "published": it.get("published") or "",
        "title": it.get("title") or "",
        "summary": (it.get("summary") or "")[:300],
    }


def cmd_prepare(args) -> int:
    src = Path(args.items)
    if not src.exists():
        die(f"找不到 {src}，先跑 bin/fetch.py", 2)
    raw = json.loads(src.read_text(encoding="utf-8"))
    items = raw.get("items") if isinstance(raw, dict) else raw
    if not items:
        die(f"{src} 里没有条目", 2)
    if not CONTRACT_SRC.exists():
        die(f"缺少任务契约 {CONTRACT_SRC}", 2)

    work = Path(args.work)
    cands, dropped_serial, unpairable = recall(
        items, args.hours, args.min_jaccard, args.min_words, args.max_df, args.keep_serial
    )
    pairs = cap_pairs(cands, args.max_degree, args.max_pairs)

    for d in (work / "inbox", work / "outbox"):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    shutil.copyfile(CONTRACT_SRC, work / "CONTRACT.md")

    index: dict[str, list[str]] = {}
    for n, (_score, pid, a, b) in enumerate(pairs):
        x, y = (a, b) if a["url"] < b["url"] else (b, a)
        rec = {"pair_id": pid, "a": side(x), "b": side(y)}
        path = work / "inbox" / f"batch-{n // args.batch_size + 1:03d}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        index[pid] = [x["url"], y["url"]]

    batches = (len(pairs) + args.batch_size - 1) // args.batch_size
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "window_hours": args.hours,
        "params": {
            "batch_size": args.batch_size,
            "min_jaccard": args.min_jaccard,
            "min_words": args.min_words,
            "max_degree": args.max_degree,
            "max_df": args.max_df,
        },
        "counts": {"items": len(items), "pairs": len(pairs), "batches": batches},
        "items": [
            {
                "id": item_id(it),
                "url": it["url"],
                "source_id": it.get("source_id") or "",
                "tier": it.get("tier") or "",
                "published": it.get("published") or "",
                "title": it.get("title") or "",
            }
            for it in items
        ],
        "pairs_index": index,
        "unpairable": unpairable,
    }
    (work / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"条目 {len(items)} → 候选对 {len(pairs)} → {batches} 批")
    print(f"  时间窗 {args.hours}h · 标题相似度 ≥{args.min_jaccard} · 共享实词 ≥{args.min_words}")
    print(f"  单条目最多 {args.max_degree} 对；参与配对 {len(items) - len(unpairable)} 条")
    if dropped_serial:
        print(f"  丢弃 {dropped_serial} 对「同一栏目不同期」")
    if unpairable:
        print(f"  标题无实义、归并为单例：{len(unpairable)} 条（{unpairable[0]['source']} 等）")
    print(f"写入 {rel(work)}/inbox、manifest.json、CONTRACT.md")
    cwd = rel(work)
    task = (
        "读 CONTRACT.md，只处理 inbox/batch-001.jsonl，把结果写进 outbox/batch-001.jsonl。"
        "不要联网，不要修改其它文件，处理完就退出。"
    )
    print("\n下一步（让 agent 判定。先跑一个批次看质量，再放全量）：")
    print(f'  cd {cwd} && dsh headless "{task}"')
    print("  全部批次：把 batch-001 换成 batch-*")
    print("\n然后： uv run python bin/cluster.py merge")
    return 0


# ---------------------------------------------------------------- 校验
def load_manifest(work: Path) -> dict:
    path = work / "manifest.json"
    if not path.exists():
        die(f"找不到 {path} —— 先跑 bin/cluster.py prepare", 2)
    return json.loads(path.read_text(encoding="utf-8"))


def load_decisions(work: Path) -> tuple[dict[str, dict], list[str]]:
    outbox = work / "outbox"
    if not outbox.exists():
        die(f"找不到 {outbox} —— agent 还没跑", 2)
    problems: list[str] = []
    decisions: dict[str, dict] = {}
    for path in sorted(outbox.glob("batch-*.jsonl")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            where = f"{path.name}:{lineno}"
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"{where} 不是合法 JSON：{exc.msg}")
                continue
            if not isinstance(rec, dict) or set(rec) != FIELDS:
                got = set(rec) if isinstance(rec, dict) else set()
                problems.append(
                    f"{where} 字段不符：缺 {sorted(FIELDS - got)} 多 {sorted(got - FIELDS)}"
                )
                continue
            pid = rec["pair_id"]
            if not isinstance(pid, str) or not pid:
                problems.append(f"{where} pair_id 非法")
                continue
            if pid in decisions:
                problems.append(f"{where} pair_id 重复：{pid}")
                continue
            if not isinstance(rec["same_event"], bool):
                problems.append(f"{where} same_event 不是布尔值：{rec['same_event']!r}")
                continue
            conf = rec["confidence"]
            if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
                problems.append(f"{where} confidence 不在 0–1：{conf!r}")
                continue
            reason = rec["reason"]
            if not isinstance(reason, str):
                problems.append(f"{where} reason 不是字符串")
                continue
            if len(reason) > MAX_REASON:
                problems.append(f"{where} reason 超过 {MAX_REASON} 字：{reason[:30]}…")
            if "http" in reason.lower():
                problems.append(f"{where} reason 里出现了 URL")
            if rec["same_event"] and conf < MERGE_THRESHOLD:
                problems.append(
                    f"{where} 结论自相矛盾：same_event=true 但 confidence={conf} < {MERGE_THRESHOLD}"
                )
            decisions[pid] = rec
    return decisions, problems


def cmd_merge(args) -> int:
    work = Path(args.work)
    manifest = load_manifest(work)
    index = manifest["pairs_index"]

    expected: dict[str, str] = {}
    for path in sorted((work / "inbox").glob("batch-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                expected[json.loads(line)["pair_id"]] = path.name
    if not expected:
        die(f"{work / 'inbox'} 里没有候选对 —— 先跑 prepare", 2)

    decisions, problems = load_decisions(work)
    missing_files = [
        name for name in sorted(set(expected.values())) if not (work / "outbox" / name).exists()
    ]
    unknown = set(decisions) - set(expected)
    missing = set(expected) - set(decisions)
    if unknown:
        problems.append(
            f"出现 {len(unknown)} 个不属于任何批次的 pair_id，例：{sorted(unknown)[:3]}"
        )
    if missing:
        problems.append(f"缺 {len(missing)} 条决策，例：{sorted(missing)[:3]}")
    if missing_files:
        problems.append(f"缺 {len(missing_files)} 个输出文件：{missing_files[:5]}")

    print(f"候选对 {len(expected)} · 已判定 {len(decisions)} · 批次 {len(set(expected.values()))}")
    if problems:
        print(f"\n契约违约，共 {len(problems)} 处：", file=sys.stderr)
        for p in problems[:25]:
            print(f"  - {p}", file=sys.stderr)
        if len(problems) > 25:
            print(f"  … 另有 {len(problems) - 25} 处", file=sys.stderr)
        print("\n未通过校验。让 agent 重跑对应批次，不要手工改 outbox。", file=sys.stderr)
        return 3

    yes = sum(1 for d in decisions.values() if d["same_event"])
    confs = sorted(d["confidence"] for d in decisions.values())
    print(f"契约通过 · 判同一事件 {yes} · 判不同 {len(decisions) - yes}")
    print(
        f"  置信度 中位 {confs[len(confs) // 2]:.2f} · 最低 {confs[0]:.2f} · 最高 {confs[-1]:.2f}"
    )

    url_to_id = {it["url"]: it["id"] for it in manifest["items"]}
    by_id = {it["id"]: it for it in manifest["items"]}

    parent = {i: i for i in by_id}
    members = {i: {i} for i in by_id}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    pos, neg = [], set()
    for pid, d in decisions.items():
        pair = index.get(pid)
        if not pair:
            continue
        a, b = url_to_id.get(pair[0]), url_to_id.get(pair[1])
        if not a or not b:
            continue
        if d["same_event"]:
            pos.append((d["confidence"], a, b))
        elif d["confidence"] >= MERGE_THRESHOLD:
            neg.add(frozenset((a, b)))
    pos.sort(key=lambda x: (-x[0], x[1], x[2]))

    rejected = 0
    accepted: list[tuple[float, str, str]] = []
    for conf, a, b in pos:
        ra, rb = find(a), find(b)
        if ra == rb:
            accepted.append((conf, a, b))
            continue
        # 非传递矛盾：A≈B、B≈C 但 A≉C 时，不把 C 拉进来
        if any(frozenset((m1, m2)) in neg for m1 in members[ra] for m2 in members[rb]):
            rejected += 1
            continue
        parent[rb] = ra
        members[ra] |= members.pop(rb)
        accepted.append((conf, a, b))

    groups: dict[str, list[str]] = {}
    for i in by_id:
        groups.setdefault(find(i), []).append(i)

    clusters = []
    for member_ids in groups.values():
        infos = [by_id[m] for m in member_ids]
        primary = min(
            infos,
            key=lambda it: (
                TIER_RANK.get(it.get("tier") or "media", 1),
                it.get("published") or "9999",
                it["id"],
            ),
        )
        member_ids.sort(key=lambda m: (m != primary["id"], by_id[m].get("published") or "", m))
        inside = [c for c, x, y in accepted if x in member_ids and y in member_ids]
        clusters.append(
            {
                "event_id": "e" + min(member_ids)[:7],
                "primary": primary["id"],
                "size": len(member_ids),
                "min_confidence": round(min(inside), 3) if inside else None,
                "members": [
                    {
                        "id": by_id[m]["id"],
                        "url": by_id[m]["url"],
                        "source": by_id[m].get("source_id") or "",
                        "tier": by_id[m].get("tier") or "",
                        "published": by_id[m].get("published") or "",
                        "title": by_id[m].get("title") or "",
                    }
                    for m in member_ids
                ],
            }
        )
    clusters.sort(key=lambda c: (-c["size"], c["primary"]))

    covered = [m["id"] for c in clusters for m in c["members"]]
    if len(covered) != len(by_id) or len(set(covered)) != len(by_id):
        die(
            f"归并结果未全覆盖：{len(by_id)} 条进，{len(covered)} 条出，"
            f"去重后 {len(set(covered))} 条",
            3,
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "threshold": MERGE_THRESHOLD,
                "stats": {
                    "items": len(by_id),
                    "clusters": len(clusters),
                    "multi": sum(1 for c in clusters if c["size"] > 1),
                    "singletons": sum(1 for c in clusters if c["size"] == 1),
                    "edges_accepted": len(accepted),
                    "edges_rejected_conflict": rejected,
                },
                "clusters": clusters,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    multi = [c for c in clusters if c["size"] > 1]
    print(
        f"条目 {len(by_id)} → 事件 {len(clusters)}（多成员 {len(multi)}，单例 {len(clusters) - len(multi)}）"
    )
    print(f"  接受边 {len(accepted)} · 因矛盾拒绝 {rejected}")
    print(f"写入 {rel(out)}（{out.stat().st_size / 1024:.0f} KB）")
    if multi:
        print("\n  规模最大的几个事件：")
        for c in multi[:8]:
            p = c["members"][0]
            print(f"   {c['size']} 条  [{p['tier']}] {p['title'][:44]}")
    return 0


# ---------------------------------------------------------------- 评测
def cmd_eval(args) -> int:
    work = Path(args.work)
    manifest = load_manifest(work)
    decisions, _ = load_decisions(work)
    labels = Path(args.labels)
    if not labels.exists():
        die(f"找不到标注文件 {labels}", 2)

    url_pair_to_pid = {tuple(sorted(v)): k for k, v in manifest["pairs_index"].items()}

    tp = fp = fn = tn = 0
    not_candidate: list[tuple[str, str, int]] = []
    wrong_merge: list[tuple[str, str]] = []
    missed: list[tuple[str, str]] = []

    for lineno, line in enumerate(labels.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            print(f"  跳过第 {lineno} 行：需要 url_a\\turl_b\\tsame", file=sys.stderr)
            continue
        ua, ub, gold = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if gold not in {"0", "1"}:
            print(f"  跳过第 {lineno} 行：same 只能是 0 或 1", file=sys.stderr)
            continue
        want = gold == "1"
        pid = url_pair_to_pid.get(tuple(sorted([ua, ub])))
        if not pid or pid not in decisions:
            not_candidate.append((ua, ub, int(want)))
            if want:
                fn += 1
            continue
        got = decisions[pid]["same_event"]
        if got and want:
            tp += 1
        elif got and not want:
            fp += 1
            wrong_merge.append((ua, ub))
        elif not got and want:
            fn += 1
            missed.append((ua, ub))
        else:
            tn += 1

    total = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    print(
        f"标注 {total + len(not_candidate)} 对，其中判定 {total} 对 · TP {tp} FP {fp} FN {fn} TN {tn}"
    )
    print(f"  precision {prec:.3f} · recall {rec:.3f} · 错合并 {fp}")
    if not_candidate:
        same = sum(1 for x in not_candidate if x[2])
        print(
            f"  未进入候选对 {len(not_candidate)}（其中本该合并的 {same}）—— 召回的锅，不是 agent 的"
        )
    if wrong_merge:
        print("\n  错合并（最严重，优先修）：")
        for ua, ub in wrong_merge[:5]:
            print(f"   - {ua[:60]}  ×  {ub[:60]}")
    if missed:
        print("\n  漏合并（可接受）：")
        for ua, ub in missed[:5]:
            print(f"   - {ua[:60]}  ×  {ub[:60]}")
    if fp == 0 and total:
        print("\n  错合并为 0 —— 达到上线门槛。")
    return 0


# ---------------------------------------------------------------- LLM 判定
JUDGE_SYSTEM = (
    "你是新闻事件归并判断器。给定若干对资讯，判断每一对是否在报道同一个事件。\n"
    "判「是」：同一事件的中英文报道、转述/编译/转载、官方原文+媒体解读、多源同报。\n"
    "判「否」：同一公司不同产品/版本、日报/合集 vs 单条、综述 vs 其中一条、"
    "传闻 vs 正式发布、同一事件后续进展、同一活动不同年份、仅话题相同。\n"
    "来源层级 official=官方 / media=媒体 / aggregator=聚合 只帮你理解谁是一手，不影响判断。\n"
    "不确定就判否。same_event=true 时 confidence 必须 ≥0.85。\n"
    "只输出 JSON 数组，每项四个字段：pair_id、same_event(布尔)、confidence(0-1 小数)、"
    "reason(≤20 字，不含 URL)。不要输出任何解释。"
)


def judge_batch(pairs: list[dict], settings: config.Settings) -> dict[str, dict]:
    """一次调用判定一批候选对，返回 pair_id → 决策。缺失/非法结果保守判否。"""
    lines = []
    for p in pairs:
        a, b = p["a"], p["b"]
        pa = a["published"][:10] if a["published"] else "无日期"
        pb = b["published"][:10] if b["published"] else "无日期"
        lines.append(
            f"- id: {p['pair_id']}\n"
            f"  a: [{a['tier']}] {a['title']} ({pa})\n"
            f"  b: [{b['tier']}] {b['title']} ({pb})"
        )
    raw = llm.chat_json(
        [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": "\n".join(lines)},
        ],
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )
    if not isinstance(raw, list):
        raise ValueError(f"模型应返回数组，实际 {type(raw).__name__}")

    by_id = {d.get("pair_id"): d for d in raw if isinstance(d, dict)}
    out: dict[str, dict] = {}
    for p in pairs:
        pid = p["pair_id"]
        d = by_id.get(pid)
        if (
            isinstance(d, dict)
            and isinstance(d.get("same_event"), bool)
            and isinstance(d.get("confidence"), (int, float))
            and 0 <= d["confidence"] <= 1
        ):
            same = d["same_event"] and not (d["same_event"] and d["confidence"] < 0.85)
            conf = round(float(d["confidence"]), 3)
        else:
            same, conf = False, 0.5  # 保守默认：不合并
        reason = d.get("reason", "") if isinstance(d, dict) else ""
        reason = (
            reason if isinstance(reason, str) and len(reason) <= 20 and "http" not in reason else ""
        )
        out[pid] = {"pair_id": pid, "same_event": same, "confidence": conf, "reason": reason}
    return out


def cmd_judge(args) -> int:
    work = Path(args.work)
    inbox = work / "inbox"
    outbox = work / "outbox"
    cache_path = work / "judge_cache.json"

    settings = config.load(require_base_url=False)
    if not settings.llm_api_key:
        print("未配置 LLM_API_KEY，judge 需要模型判定。", file=sys.stderr)
        return 2

    if not inbox.exists():
        print(f"找不到 {inbox} —— 先跑 bin/cluster.py prepare", file=sys.stderr)
        return 1

    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    outbox.mkdir(parents=True, exist_ok=True)
    judged = 0
    for path in sorted(inbox.glob("batch-*.jsonl")):
        pairs = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        todo = [p for p in pairs if p["pair_id"] not in cache]
        if todo:
            decisions = judge_batch(todo, settings)
            cache.update(decisions)
            judged += len(todo)
        lines = []
        for p in pairs:
            d = cache.get(p["pair_id"])
            if not d:
                print(f"  缺判定 {p['pair_id']}", file=sys.stderr)
                return 3
            lines.append(json.dumps(d, ensure_ascii=False))
        (outbox / path.name).write_text("\n".join(lines) + "\n", encoding="utf-8")

    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"本次判定 {judged} 对，缓存累计 {len(cache)} 对")
    return 0


# ---------------------------------------------------------------- 入口
def main() -> int:
    ap = argparse.ArgumentParser(description="事件归并：召回 / 合并 / 评测")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="召回候选对，切批写进 .work/")
    p.add_argument("--items", default=str(ITEMS_PATH))
    p.add_argument("--work", default=str(WORK))
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--hours", type=int, default=48)
    p.add_argument("--min-jaccard", type=float, default=0.30)
    p.add_argument("--min-words", type=int, default=3)
    p.add_argument("--max-df", type=int, default=12, help="专名共现通道的稀有词上限")
    p.add_argument("--max-degree", type=int, default=6)
    p.add_argument("--max-pairs", type=int, default=1500)
    p.add_argument("--keep-serial", action="store_true", help="保留同一栏目不同期")
    p.set_defaults(func=cmd_prepare)

    m = sub.add_parser("merge", help="校验 outbox 并合并成 data/clusters.json")
    m.add_argument("--work", default=str(WORK))
    m.add_argument("--out", default=str(CLUSTERS_PATH))
    m.set_defaults(func=cmd_merge)

    j = sub.add_parser("judge", help="用 LLM 判定 .work/inbox 里的候选对")
    j.add_argument("--work", default=str(WORK))
    j.set_defaults(func=cmd_judge)

    e = sub.add_parser("eval", help="对人工标注算准确率")
    e.add_argument("--work", default=str(WORK))
    e.add_argument("--labels", default=str(ROOT / "regression" / "pairs.tsv"))
    e.set_defaults(func=cmd_eval)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
