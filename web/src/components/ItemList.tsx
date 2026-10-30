import type { ReactNode } from "react";
import { fmtDate } from "../lib/format";
import type { Item } from "../lib/types";

interface Props {
  items: Item[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  footer?: ReactNode;
}

export default function ItemList({ items, selected, onToggle, footer }: Props) {
  return (
    <div className="list">
      {items.length === 0 ? (
        <div className="empty">没有匹配的条目。换个关键词，或关掉筛选条件。</div>
      ) : (
        <ul className="rows">
          {items.map((it) => {
            const on = selected.has(it.id);
            return (
              <li className={on ? "row sel" : "row"} key={it.id}>
                <input
                  className="ck"
                  type="checkbox"
                  checked={on}
                  aria-label={`选中：${it.title}`}
                  onChange={() => onToggle(it.id)}
                />
                <div className={`src ${it.tier}`} title={it.source_name}>
                  {it.source_name}
                </div>
                <div className="t">
                  <a className="ti" href={it.url} target="_blank" rel="noopener">
                    {it.title}
                  </a>
                  {it.summary ? <div className="sm">{it.summary}</div> : null}
                </div>
                <div className={it.published ? "d" : "d none"}>{fmtDate(it.published)}</div>
                {/* 标题本身就是同一个链接，箭头只是视觉提示，不再做成重复链接。 */}
                <span className="ext" aria-hidden="true">
                  ↗
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {footer}
    </div>
  );
}
