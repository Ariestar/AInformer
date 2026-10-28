#!/usr/bin/env python3
"""源健康检查。

每周跑一次。三类异常：HTTP 失败、连续零新增、最新条目过旧。
源腐烂不会报错，只会让你慢慢漏消息，所以要主动查。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch_bytes, load_config, parse_feed  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOG = DATA / "health_log.jsonl"
STALE_DAYS = 30
ZERO_STREAK_ALERT = 3


def load_history() -> dict[str, list[int]]:
    hist: dict[str, list[int]] = {}
    if not LOG.exists():
        return hist
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        hist.setdefault(rec["id"], []).append(rec.get("items", 0))
    return hist


def main() -> int:
    cfg = load_config()
    fc = cfg.get("fetch", {})
    timeout = fc.get("timeout", 20)
    ua = fc.get("user_agent", "ai-intel/1.0")
    now = datetime.now(timezone.utc)
    history = load_history()

    rows, alerts = [], []
    for src in cfg.get("source", []):
        sid = src["id"]
        row = {"id": sid, "name": src["name"], "ts": now.isoformat(), "status": None, "items": 0, "newest": None, "error": None}
        try:
            blob = fetch_bytes(src["url"], timeout, ua)
            entries = parse_feed(blob)
            row["status"] = 200
            row["items"] = len(entries)
            dates = [e["published"] for e in entries if e["published"]]
            if dates:
                row["newest"] = max(dates).isoformat()
        except Exception as exc:  # noqa: BLE001 — 健康检查要吃掉所有异常，不能因为一个源挂掉整轮失败
            row["status"] = "ERR"
            row["error"] = f"{type(exc).__name__}: {exc}"
            alerts.append((sid, "拉取失败", row["error"]))
        rows.append(row)

        if row["status"] == 200:
            streak = history.get(sid, [])[-ZERO_STREAK_ALERT + 1:] + [row["items"]]
            if len(streak) >= ZERO_STREAK_ALERT and all(x == 0 for x in streak):
                alerts.append((sid, f"连续 {ZERO_STREAK_ALERT} 次零新增", "源还活着但内容断了"))
            if row["newest"]:
                newest = datetime.fromisoformat(row["newest"])
                age = (now - newest).days
                if age > STALE_DAYS:
                    alerts.append((sid, f"最新条目已 {age} 天未更新", "可能已停更或换了地址"))

    DATA.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    (DATA / "health.json").write_text(
        json.dumps({"checked_at": now.isoformat(), "rows": rows, "alerts": alerts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"{'源':<18}{'状态':<8}{'条目':>6}  {'最新条目':<12}")
    print("-" * 52)
    for r in rows:
        newest = (r["newest"] or "—")[:10]
        print(f"{r['id']:<18}{str(r['status']):<8}{r['items']:>6}  {newest:<12}")

    if alerts:
        print("\n需要处理：")
        for sid, what, why in alerts:
            print(f"  - {sid}: {what}（{why}）")
    else:
        print("\n全部正常。")
    return 0 if not alerts else 2


if __name__ == "__main__":
    raise SystemExit(main())
