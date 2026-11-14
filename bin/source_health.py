"""源健康状态的唯一实现：供 export 和 daily 共用，前端只负责渲染。"""

from __future__ import annotations

from datetime import datetime

STALE_DAYS = 30
_RANK = {"error": 0, "stale": 1, "empty": 2, "ok": 3}


def summarize(sources: list[dict], items: list[dict], now: datetime, window_days: int) -> dict:
    newest_by: dict[str, str] = {}
    for it in items:
        published = it.get("published")
        if not published:
            continue
        cur = newest_by.get(it["source_id"])
        if not cur or published > cur:
            newest_by[it["source_id"]] = published

    rows = []
    for s in sources:
        newest = newest_by.get(s["id"])
        stale_days = -1
        if newest:
            try:
                dt = datetime.fromisoformat(newest)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=now.tzinfo)
                stale_days = (now - dt).days
            except (TypeError, ValueError):
                newest = None

        if not s.get("ok"):
            state = "error"
        elif newest is None:
            state = "empty"
        elif stale_days > STALE_DAYS:
            state = "stale"
        else:
            state = "ok"

        rows.append(
            {
                "id": s["id"],
                "name": s.get("name") or s["id"],
                "state": state,
                "kept": s.get("kept", 0),
                "newest": newest,
                "staleDays": stale_days,
                "error": s.get("error"),
            }
        )

    rows.sort(key=lambda r: (_RANK[r["state"]], r["name"]))
    span = f"{window_days} 天内" if window_days else "当前窗口内"
    alerts = []
    for r in rows:
        if r["state"] == "error":
            alerts.append(f"{r['name']} 本轮抓取失败")
        elif r["state"] == "stale":
            alerts.append(f"{r['name']} 已 {r['staleDays']} 天未更新")
        elif r["state"] == "empty":
            alerts.append(f"{r['name']} {span}零新增")

    return {"total": len(rows), "problemCount": len(alerts), "alerts": alerts, "rows": rows}
