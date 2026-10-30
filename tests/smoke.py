#!/usr/bin/env python3
"""端到端冒烟测试：召回 → 判定 → 合并 → 导出，最后断言契约字段。

用一条命令跑通整条链路，不在 shell 里写 heredoc（zsh 对多行 heredoc
和括号更敏感，容易 parse error）：
    python3 tests/smoke.py              # 用 tests/fixtures/items.json
    python3 tests/smoke.py --real       # 用 data/items.json（需先跑 bin/fetch.py）

默认走 fixture，因为它自包含、可离线跑；--real 才依赖抓取产物。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
WORK = ROOT / ".work"
FIXTURE = ROOT / "tests" / "fixtures" / "items.json"
REAL = ROOT / "data" / "items.json"


def run(cmd: list[str], label: str) -> None:
    print(f"\n=== {label} ===")
    print("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print(f"[失败] {label} 退出码 {proc.returncode}", file=sys.stderr)
        raise SystemExit(proc.returncode)


def fake_judge() -> None:
    """用标题三元组相似度冒充模型，只验证链路，不验证判断质量。"""
    punct = re.compile(r"[\s\W_]+", re.UNICODE)

    def grams(s: str) -> set[str]:
        t = punct.sub("", s.lower())
        return {t[i : i + 3] for i in range(len(t) - 2)} if len(t) > 3 else {t}

    def jac(a: set[str], b: set[str]) -> float:
        return len(a & b) / len(a | b) if a and b else 0.0

    outbox = WORK / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    n = 0
    for path in sorted((WORK / "inbox").glob("batch-*.jsonl")):
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            same = jac(grams(rec["a"]["title"]), grams(rec["b"]["title"])) >= 0.55
            lines.append(
                json.dumps(
                    {
                        "pair_id": rec["pair_id"],
                        "same_event": same,
                        "confidence": 0.92 if same else 0.25,
                        "reason": "标题重合" if same else "不同事",
                    },
                    ensure_ascii=False,
                )
            )
            n += 1
        (outbox / path.name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"假 agent 写了 {n} 条判定")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true", help="用 data/items.json 而非 fixture")
    args = ap.parse_args()

    src = REAL if args.real else FIXTURE
    if not src.exists():
        print(f"找不到 {src}。--real 需要先跑 bin/fetch.py。", file=sys.stderr)
        return 2

    py = sys.executable
    run([py, str(BIN / "cluster.py"), "prepare", "--items", str(src)], "1/4 召回候选对")
    fake_judge()
    run([py, str(BIN / "cluster.py"), "merge"], "2/4 合并")
    run([py, str(BIN / "export.py"), "--in", str(src)], "3/4 导出契约")

    out = json.loads((ROOT / "web" / "public" / "data" / "items.json").read_text(encoding="utf-8"))
    assert "sources" in out, "导出缺少 sources 数组"
    first = out["items"][0]
    missing = {"event_id", "event_size", "is_primary"} - set(first)
    assert not missing, f"首条缺字段：{missing}"
    events = len({i["event_id"] for i in out["items"]})
    multi = sum(1 for i in out["items"] if i["event_size"] > 1)

    print(
        f"\nOK：{len(out['items'])} 条 / {events} 个事件 / "
        f"{len(out['sources'])} 个源 / 多源条目 {multi} 条 / "
        f"首条 event_id={first['event_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
