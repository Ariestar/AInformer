import type { FilterState } from "../lib/select";
import type { SortKey } from "../lib/types";

interface Props {
  filter: FilterState;
  query: string;
  sources: Array<{ id: string; name: string }>;
  selectedCount: number;
  onChange: (next: FilterState) => void;
  onQueryChange: (query: string) => void;
  onSelectVisible: () => void;
  onClear: () => void;
  onExport: () => void;
}

export default function Toolbar({
  filter,
  query,
  sources,
  selectedCount,
  onChange,
  onQueryChange,
  onSelectVisible,
  onClear,
  onExport,
}: Props) {
  return (
    <div className="bar">
      <div className="search">
        <svg
          className="search-i"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <circle cx="7" cy="7" r="4.5" />
          <path d="M10.6 10.6 14 14" />
        </svg>
        <input
          className="inp q"
          type="search"
          placeholder="搜标题、摘要、来源…"
          aria-label="搜索条目"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
        />
      </div>
      <select
        className="pick"
        aria-label="按来源筛选"
        value={filter.src}
        onChange={(e) => onChange({ ...filter, src: e.target.value })}
      >
        <option value="all">全部来源</option>
        {sources.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
      <select
        className="pick"
        aria-label="排序方式"
        value={filter.sort}
        onChange={(e) => onChange({ ...filter, sort: e.target.value as SortKey })}
      >
        <option value="time">按时间</option>
        <option value="source">按来源</option>
      </select>
      <button
        className={filter.official ? "tog on" : "tog"}
        type="button"
        aria-pressed={filter.official}
        onClick={() => onChange({ ...filter, official: !filter.official })}
      >
        只看官方源
      </button>
      <button
        className={filter.dated ? "tog on" : "tog"}
        type="button"
        aria-pressed={filter.dated}
        onClick={() => onChange({ ...filter, dated: !filter.dated })}
      >
        只看有日期
      </button>
      <span className="sp" />
      <button className="btn" type="button" onClick={onSelectVisible}>
        全选本页
      </button>
      <button className="btn" type="button" onClick={onClear}>
        清空
      </button>
      <button
        className="btn primary"
        type="button"
        onClick={onExport}
        disabled={selectedCount === 0}
        title={selectedCount === 0 ? "先勾选条目" : undefined}
      >
        导出 Markdown
      </button>
    </div>
  );
}
