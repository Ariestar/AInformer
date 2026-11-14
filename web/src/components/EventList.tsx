import { useState } from "react";
import { type EventGroup, tierBreakdown } from "../lib/events";
import { fmtDate } from "../lib/format";

interface Props {
  groups: EventGroup[];
  selected: Set<string>;
  onToggle: (ids: string[]) => void;
  onFeedback: (eventId: string) => void;
}

// 事件视图：一件事一行，展开看同一事件下的多个来源。
// 可信度两档：有官方源 / 无官方源。
export default function EventList({ groups, selected, onToggle, onFeedback }: Props) {
  if (groups.length === 0) {
    return (
      <div className="list">
        <div className="empty">没有匹配的事件。换个关键词，或关掉筛选条件。</div>
      </div>
    );
  }
  return (
    <div className="list">
      <ul className="rows">
        {groups.map((g) => (
          <EventRow
            key={`${g.event_id}:${g.primary.id}`}
            group={g}
            selected={selected}
            onToggle={onToggle}
            onFeedback={onFeedback}
          />
        ))}
      </ul>
    </div>
  );
}

function EventRow({
  group,
  selected,
  onToggle,
  onFeedback,
}: {
  group: EventGroup;
  selected: Set<string>;
  onToggle: (ids: string[]) => void;
  onFeedback: (eventId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const g = group;
  const ids = g.items.map((it) => it.id);
  const allSelected = ids.every((id) => selected.has(id));

  return (
    <li className={allSelected ? "row event sel" : "row event"}>
      <input
        className="ck"
        type="checkbox"
        checked={allSelected}
        aria-label={`选中：${g.primary.title}`}
        onChange={() => onToggle(ids)}
      />
      <div className={`src ${g.primary.tier}`}>{g.primary.source_name}</div>
      <div className="t">
        <a className="ti" href={g.primary.url} target="_blank" rel="noopener">
          {g.primary.title}
        </a>
        {g.primary.summary ? <div className="sm">{g.primary.summary}</div> : null}
        <div className="ev-meta">
          <span className={g.hasOfficial ? "ev-trust on" : "ev-trust"}>
            {g.hasOfficial ? "官方" : "无官方源"}
          </span>
          {g.size > 1 ? (
            <>
              <span>{g.size} 源</span>
              <span>{tierBreakdown(g)}</span>
              <button
                type="button"
                className="ev-link"
                aria-expanded={open}
                onClick={() => setOpen((v) => !v)}
              >
                {open ? "收起" : "展开"}
              </button>
              <button type="button" className="ev-link warn" onClick={() => onFeedback(g.event_id)}>
                这不是同一件事
              </button>
            </>
          ) : null}
        </div>
        {open ? (
          <ul className="ev-members">
            {g.items.map((it) => (
              <li className="ev-member" key={it.id}>
                <span className={`src ${it.tier}`}>{it.source_name}</span>
                <a href={it.url} target="_blank" rel="noopener">
                  {it.title}
                </a>
                <span className="d">{fmtDate(it.published)}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <div className="d">{fmtDate(g.newest)}</div>
    </li>
  );
}
