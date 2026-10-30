interface Props {
  page: number;
  pageCount: number;
  total: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, pageCount, total, onChange }: Props) {
  return (
    <div className="pager">
      <button className="btn" type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← 上一页
      </button>
      <button
        className="btn"
        type="button"
        disabled={page >= pageCount}
        onClick={() => onChange(page + 1)}
      >
        下一页 →
      </button>
      <span className="pos">
        第 {page} / {pageCount} 页 · 共 {total} 条
      </span>
    </div>
  );
}
