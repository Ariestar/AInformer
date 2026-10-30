import { useState } from "react";
import { fmtDate } from "../lib/format";
import type { HealthSummary } from "../lib/health";

interface Props {
  health: HealthSummary | null;
}

const STATE_LABEL: Record<string, string> = {
  ok: "正常",
  error: "抓取失败",
  stale: "已停更",
  empty: "零新增",
};

// 源健康面板：只在有异常时出现一条警示，点开看全部源。
// health 为 null 表示完整数据还没加载回来，此时什么都不渲染。
export default function HealthPanel({ health }: Props) {
  const [open, setOpen] = useState(false);

  if (!health || health.problemCount === 0) return null;

  return (
    <div className="health">
      <button
        type="button"
        className="health-banner"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="health-warn">⚠ {health.alerts.join("；")}</span>
        <span className="health-toggle">{open ? "收起 ▴" : "查看全部源 ▾"}</span>
      </button>
      {open ? (
        <div className="health-drawer">
          {health.rows.map((r) => (
            <div className="health-row" key={r.id}>
              <span className={`health-state ${r.state}`}>{STATE_LABEL[r.state]}</span>
              <span className="health-name">{r.name}</span>
              <span className="health-kept">本轮 {r.kept} 条</span>
              <span className="health-newest">{r.newest ? fmtDate(r.newest) : "无条目"}</span>
              {r.staleDays > 0 ? <span className="health-stale">{r.staleDays} 天前</span> : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
