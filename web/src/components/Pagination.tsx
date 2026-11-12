interface Props {
  page: number;
  pageCount: number;
  total: number;
  onChange: (page: number) => void;
}

function Chevron({ dir }: { dir: "left" | "right" }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={dir === "left" ? "M9.5 3.5 5 8l4.5 4.5" : "M6.5 3.5 11 8l-4.5 4.5"} />
    </svg>
  );
}

export default function Pagination({ page, pageCount, total, onChange }: Props) {
  return (
    <div className="pager">
      <button className="btn" type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        <Chevron dir="left" />
        上一页
      </button>
      <button
        className="btn"
        type="button"
        disabled={page >= pageCount}
        onClick={() => onChange(page + 1)}
      >
        下一页
        <Chevron dir="right" />
      </button>
      <span className="pos">
        第 {page} / {pageCount} 页 · 共 {total} 条
      </span>
    </div>
  );
}
