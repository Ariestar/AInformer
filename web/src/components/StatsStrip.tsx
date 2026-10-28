interface Props {
  sourcesOk: number;
  sourcesTotal: number;
  fetched: number;
  shown: number;
  selected: number;
  windowDays: number;
}

export default function StatsStrip({ sourcesOk, sourcesTotal, fetched, shown, selected, windowDays }: Props) {
  return (
    <div className="strip">
      <div className="inner">
        <div className="stat">
          <span className="k">源</span>
          <span className="v">
            {sourcesOk}/{sourcesTotal}
          </span>
        </div>
        <div className="stat">
          <span className="k">抓取</span>
          <span className="v">{fetched}</span>
        </div>
        <div className="stat">
          <span className="k">当前显示</span>
          <span className="v">{shown}</span>
        </div>
        <div className="stat">
          <span className="k">已选</span>
          <span className="v">{selected}</span>
        </div>
        <div className="stat" style={{ marginLeft: "auto" }}>
          <span className="k">窗口</span>
          <span className="v dim">{windowDays} 天</span>
        </div>
      </div>
    </div>
  );
}
