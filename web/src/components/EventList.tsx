import { useState } from "react";
import { type EventGroup, tierBreakdown } from "../lib/events";
import { fmtDate, tierName } from "../lib/format";

interface Props {
  groups: EventGroup[];
  selected: Set<string>;
  onToggle: (ids: string[]) => void;
  onFeedback: (eventId: string) => void;
}

// 事件视图：一件事一块，下挂多个来源。可信度两档：有官方源 / 无官方源。
export default function EventList({ groups, selected, onToggle, onFeedback }: Props) {
  if (groups.length === 0) {
    return <div className="empty">没有匹配的事件。换个关键词，或关掉筛选条件。</div>;
  }
  return (
    <div className="list">
      {groups.map((g) => (
        <EventRow
          key={g.event_id}
          group={g}
          selected={selected}
          onToggle={onToggle}
          onFeedback={onFeedback}
        />
      ))}
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
    <div className={allSelected ? "event sel" : "event"}>
      <div className="event-head">
        <input
          className="ck"
          type="checkbox"
          checked={allSelected}
          aria-label={`选中：${g.primary.title}`}
          onChange={() => onToggle(ids)}
        />
        <div className="ev-main">
          <div className="ev-meta">
            <span className={g.hasOfficial ? "trust on" : "trust off"}>
              {g.hasOfficial ? "官方" : "无官方源"}
            </span>
            <span className="ev-count">{g.size} 源</span>
            <span className="ev-tiers">{tierBreakdown(g)}</span>
            <span className="ev-date">{fmtDate(g.newest)}</span>
          </div>
          <a className="ev-title" href={g.primary.url} target="_blank" rel="noopener">
            {g.primary.title}
          </a>
          {g.primary.summary ? <div className="ev-summary">{g.primary.summary}</div> : null}
        </div>
        <div className="ev-actions">
          <button
            type="button"
            className="ev-expand"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "收起" : "展开"}
          </button>
          {g.size > 1 ? (
            <button type="button" className="ev-split" onClick={() => onFeedback(g.event_id)}>
              这不是同一件事
            </button>
          ) : null}
        </div>
      </div>
      {open ? (
        <div className="event-body">
          {g.items.map((it) => (
            <div className="ev-member" key={it.id}>
              <span className={`src ${it.tier}`}>{tierName(it.tier, true)}</span>
              <a href={it.url} target="_blank" rel="noopener">
                {it.title}
              </a>
              <span className="d">{fmtDate(it.published)}</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
