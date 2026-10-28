import type { ViewMode } from "../lib/types";
import ThemeToggle from "./ThemeToggle";

interface Props {
  mode: ViewMode;
  total: number;
  selectedCount: number;
  onModeChange: (mode: ViewMode) => void;
}

export default function TopBar({ mode, total, selectedCount, onModeChange }: Props) {
  return (
    <div className="topbar">
      <div className="inner">
        <div className="logo" />
        <span className="brand">
          AInformer <span>/ 条目池</span>
        </span>
        <div className="seg">
          <button
            className={mode === "pool" ? "on" : undefined}
            aria-pressed={mode === "pool"}
            onClick={() => onModeChange("pool")}
          >
            条目池 <span className="cnt">{total}</span>
          </button>
          <button
            className={mode === "brief" ? "on" : undefined}
            aria-pressed={mode === "brief"}
            onClick={() => onModeChange("brief")}
          >
            我的简报 <span className="cnt">{selectedCount}</span>
          </button>
        </div>
        <ThemeToggle />
      </div>
    </div>
  );
}
