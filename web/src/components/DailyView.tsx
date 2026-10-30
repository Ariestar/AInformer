import { fmtDate, tierName } from "../lib/format";
import type { DailyPayload } from "../lib/types";

interface Props {
  daily: DailyPayload;
}

// 「今日」日报：一屏读完。分类和缺口由后端 daily.py 生成。
export default function DailyView({ daily }: Props) {
  const c = daily.coverage;
  const empty =
    c.sources_ok === 0
      ? "今天抓取失败，日报无法生成。"
      : daily.sections.length === 0
        ? "今天没有新事件。"
        : null;

  return (
    <div className="daily">
      <header className="daily-head">
        <h1 className="daily-title">{daily.date} · 日报</h1>
        <div className="daily-meta">
          今日 {c.events} 件事 · {c.items} 条报道 · 覆盖 {c.sources_ok}/{c.sources_total} 源
        </div>
      </header>

      {empty ? (
        <div className="empty">{empty}</div>
      ) : (
        daily.sections.map((s) => (
          <section className="daily-section" key={s.key}>
            <h2 className="daily-sec-title">
              {s.name} <span className="cnt">{s.events.length}</span>
            </h2>
            {s.summary ? <p className="daily-sec-summary">{s.summary}</p> : null}
            <ul className="daily-list">
              {s.events.map((e) => (
                <li className="daily-item" key={e.event_id}>
                  <span className={`src ${e.tier}`}>{tierName(e.tier, true)}</span>
                  <a href={e.url} target="_blank" rel="noopener">
                    {e.title}
                  </a>
                  {e.size > 1 ? <span className="daily-multi">{e.size} 源</span> : null}
                  {e.published ? <span className="daily-time">{fmtDate(e.published)}</span> : null}
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      {daily.gaps.length > 0 ? (
        <footer className="daily-gaps">⚠ 本期缺口：{daily.gaps.join("；")}</footer>
      ) : null}
    </div>
  );
}
