import { useCallback, useEffect, useMemo, useState } from "react";
import { groupItems } from "../lib/events";
import { fmtDate, tierName } from "../lib/format";
import { computeHealth } from "../lib/health";
import { type FilterState, filterItems, initialFilter, sourceOptions } from "../lib/select";
import type {
  DailyPayload,
  Item,
  PoolPayload,
  PoolView,
  SourceHealth,
  Stats,
  ViewMode,
} from "../lib/types";
import BriefView from "./BriefView";
import DailyView from "./DailyView";
import EventList from "./EventList";
import HealthPanel from "./HealthPanel";
import ItemList from "./ItemList";
import StatsStrip from "./StatsStrip";
import Toolbar from "./Toolbar";
import TopBar from "./TopBar";

// 勾选以条目的稳定 id 为键。
const SEL_KEY = "ainformer.selection.v1";
// 「这不是同一件事」的反馈，按 event_id 记，只在前端本地生效。
const SPLIT_KEY = "ainformer.split.v1";
const DATA_URL = "/data/items.json";
const DAILY_URL = "/data/daily.json";

interface Props {
  stats: Stats;
  windowDays: number;
  initialItems: Item[];
}

function loadSelection(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(SEL_KEY) || "[]") as string[]);
  } catch {
    return new Set();
  }
}

function loadSplit(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(SPLIT_KEY) || "[]") as string[]);
  } catch {
    return new Set();
  }
}

export default function PoolApp({ stats, windowDays, initialItems }: Props) {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterState>(initialFilter);
  const [mode, setMode] = useState<ViewMode>("daily");
  const [view, setView] = useState<PoolView>("events");
  const [daily, setDaily] = useState<DailyPayload | null>(null);
  const [cur, setCur] = useState(0);
  // 服务端渲染时读不到 localStorage，首屏必须是空集合，否则客户端首次渲染
  // 与 SSR 输出不一致，React 会判定 hydration mismatch 并整树重渲染。
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [split, setSplit] = useState<Set<string>>(() => new Set());
  const [restored, setRestored] = useState(false);
  const [healthSources, setHealthSources] = useState<SourceHealth[]>([]);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);

  useEffect(() => {
    setSelected(loadSelection());
    setSplit(loadSplit());
    setRestored(true);
  }, []);

  // 构建期只内联首屏可见的前若干条，完整列表由浏览器单独请求，可独立缓存。
  useEffect(() => {
    let cancelled = false;
    fetch(DATA_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<PoolPayload>;
      })
      .then((payload) => {
        if (cancelled) return;
        setItems(payload.items);
        setHealthSources(payload.sources);
        setGeneratedAt(payload.generated_at);
        setLoaded(true);
      })
      .catch((err: unknown) => {
        // 不静默降级：失败要说出来，否则用户会以为只有前几十条
        if (!cancelled) setLoadError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 日报单独请求，加载失败时「今日」视图给出明确提示而不是空白。
  useEffect(() => {
    let cancelled = false;
    fetch(DAILY_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<DailyPayload>;
      })
      .then((payload) => {
        if (!cancelled) setDaily(payload);
      })
      .catch(() => {
        if (!cancelled) setDaily(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 恢复完成前不写回，否则会把刚读到的勾选覆盖成空数组
  useEffect(() => {
    if (!restored) return;
    try {
      localStorage.setItem(SEL_KEY, JSON.stringify([...selected]));
      localStorage.setItem(SPLIT_KEY, JSON.stringify([...split]));
    } catch {
      // 存储不可用时静默降级为仅本次会话有效
    }
  }, [selected, split, restored]);

  const visible = useMemo(() => filterItems(items, filter), [items, filter]);
  const selectedItems = useMemo(() => items.filter((it) => selected.has(it.id)), [items, selected]);
  const sources = useMemo(() => sourceOptions(items), [items]);
  const groups = useMemo(() => groupItems(visible, split), [visible, split]);
  const health = useMemo(
    () => (generatedAt ? computeHealth(healthSources, items, generatedAt) : null),
    [healthSources, items, generatedAt],
  );

  // 移除条目后游标可能越界，回到第一条
  useEffect(() => {
    if (cur >= selectedItems.length) setCur(0);
  }, [cur, selectedItems.length]);

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // 事件视图里勾选是整个事件（其全部成员）一起勾。
  const toggleEvent = useCallback((ids: string[]) => {
    setSelected((prev) => {
      const next = new Set(prev);
      const allOn = ids.every((id) => next.has(id));
      for (const id of ids) {
        if (allOn) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  }, []);

  // 用户判定「这不是同一件事」：把该事件拆成单条，只影响本地视图。
  const feedback = useCallback((eventId: string) => {
    setSplit((prev) => new Set(prev).add(eventId));
  }, []);

  const selectAt = useCallback(
    (index: number) => {
      setCur(Math.max(0, Math.min(index, selectedItems.length - 1)));
    },
    [selectedItems.length],
  );

  useEffect(() => {
    if (mode !== "brief") return;
    function onKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "SELECT") return;
      if (selectedItems.length === 0) return;
      if (e.key === "ArrowRight" || e.key === "j") {
        e.preventDefault();
        setCur((c) => Math.min(c + 1, selectedItems.length - 1));
      }
      if (e.key === "ArrowLeft" || e.key === "k") {
        e.preventDefault();
        setCur((c) => Math.max(c - 1, 0));
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mode, selectedItems.length]);

  function exportMarkdown() {
    // 没勾选时按钮本身就是 disabled，这里只是防御性返回
    if (selectedItems.length === 0) return;
    const lines = [
      `# AI 情报简报（自选 ${selectedItems.length} 条）`,
      "",
      "> 由 AInformer 生成，筛选由人完成。",
      "",
    ];
    selectedItems.forEach((it, k) => {
      lines.push(`## ${k + 1}. ${it.title}`, "");
      lines.push(`- 来源：${it.source_name}（${tierName(it.tier, true)}）`);
      lines.push(`- 时间：${fmtDate(it.published)}`);
      lines.push(`- 链接：${it.url}`);
      if (it.summary) lines.push("", it.summary);
      lines.push("");
    });
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `briefing-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // 总数在构建期已知，不随加载状态跳变；"当前显示"在完整数据到达后才改为筛选结果
  const total = stats.after_dedup;
  const shown = loaded ? visible.length : stats.after_dedup;

  return (
    <>
      <TopBar mode={mode} total={total} selectedCount={selected.size} onModeChange={setMode} />
      <StatsStrip
        sourcesOk={stats.sources_ok}
        sourcesTotal={stats.sources_total}
        fetched={stats.raw_items}
        shown={shown}
        selected={selected.size}
        windowDays={windowDays}
      />

      <HealthPanel health={health} />

      <div className="wrap main">
        {mode === "daily" ? (
          daily ? (
            <DailyView daily={daily} />
          ) : (
            <div className="empty">日报加载中，若长时间无反应请刷新。</div>
          )
        ) : mode === "pool" ? (
          <>
            <div className="view-toggle" role="tablist" aria-label="情报池视图">
              <button
                type="button"
                role="tab"
                aria-selected={view === "events"}
                className={view === "events" ? "on" : undefined}
                onClick={() => setView("events")}
              >
                按事件 <span className="cnt">{groups.length}</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={view === "items"}
                className={view === "items" ? "on" : undefined}
                onClick={() => setView("items")}
              >
                按条 <span className="cnt">{visible.length}</span>
              </button>
            </div>
            <Toolbar
              filter={filter}
              sources={sources}
              selectedCount={selected.size}
              onChange={setFilter}
              onSelectVisible={() =>
                setSelected((prev) => {
                  const next = new Set(prev);
                  visible.forEach((it) => {
                    next.add(it.id);
                  });
                  return next;
                })
              }
              onClear={() => setSelected(new Set())}
              onExport={exportMarkdown}
            />
            {view === "events" ? (
              <EventList
                groups={groups}
                selected={selected}
                onToggle={toggleEvent}
                onFeedback={feedback}
              />
            ) : (
              <ItemList items={visible} selected={selected} onToggle={toggle} />
            )}
            {loadError ? (
              <div className="empty">
                完整列表加载失败（{loadError}），当前仅显示构建期保留的 {initialItems.length}{" "}
                条。刷新重试。
              </div>
            ) : null}
          </>
        ) : (
          <BriefView items={selectedItems} cur={cur} onSelect={selectAt} onRemove={toggle} />
        )}
      </div>
    </>
  );
}
