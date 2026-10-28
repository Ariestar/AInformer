import type { Item } from "../lib/types";
import { fmtDate, tierName } from "../lib/format";

interface Props {
  items: Item[];
  cur: number;
  onSelect: (index: number) => void;
  onRemove: (id: string) => void;
}

export default function BriefView({ items, cur, onSelect, onRemove }: Props) {
  if (items.length === 0) {
    return (
      <div className="stage">
        <nav className="side" aria-label="已选条目">
          <div className="side-h">你的简报</div>
        </nav>
        <section className="panel" aria-live="polite">
          <div className="empty">
            还没有选任何条目。
            <br />
            回到「条目池」，勾选你想留下的内容。
          </div>
          <div className="pager">
            <span className="pos">0 / 0</span>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="stage">
      <nav className="side" aria-label="已选条目">
        <div className="side-h">你的简报</div>
        {items.map((it, k) => (
          <a
            key={it.id}
            className={k === cur ? "navitem active" : "navitem"}
            tabIndex={0}
            role="button"
            onClick={() => onSelect(k)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(k);
              }
            }}
          >
            <span className="n">{String(k + 1).padStart(2, "0")}</span>
            <span className="nt">{it.title}</span>
          </a>
        ))}
      </nav>

      <section className="panel" aria-live="polite">
        {items.map((it, k) => (
          <article key={it.id} className={k === cur ? "slide active" : "slide"}>
            <div className="smeta">
              <span className={`chip ${it.tier}`}>{tierName(it.tier)}</span>
              <span className="status">
                {it.source_name} · {fmtDate(it.published)}
              </span>
            </div>
            <h1>{it.title}</h1>
            <div className="blk">
              <div className="k">摘要</div>
              <div className="v">{it.summary || "该源未提供摘要，点下方链接看原文。"}</div>
            </div>
            <div className="srcs">
              <a href={it.url} target="_blank" rel="noopener">
                打开原文 ↗
              </a>
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  onRemove(it.id);
                }}
              >
                从简报移除
              </a>
            </div>
          </article>
        ))}
        <div className="pager">
          <button className="btn" type="button" disabled={cur === 0} onClick={() => onSelect(cur - 1)}>
            ← 上一条
          </button>
          <button className="btn" type="button" disabled={cur === items.length - 1} onClick={() => onSelect(cur + 1)}>
            下一条 →
          </button>
          <span className="pos">
            {String(cur).padStart(2, "0")} / {String(items.length - 1).padStart(2, "0")}
          </span>
        </div>
      </section>
    </div>
  );
}
