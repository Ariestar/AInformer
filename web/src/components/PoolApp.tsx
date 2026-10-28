import { useCallback, useEffect, useMemo, useState } from "react";
import type { Item, Stats, ViewMode } from "../lib/types";
import { filterItems, initialFilter, sourceOptions, type FilterState } from "../lib/select";
import { fmtDate, tierName } from "../lib/format";
import TopBar from "./TopBar";
import StatsStrip from "./StatsStrip";
import Toolbar from "./Toolbar";
import ItemList from "./ItemList";
import BriefView from "./BriefView";

// 勾选以条目的稳定 id 为键。
const SEL_KEY = "ainformer.selection.v1";
const DATA_URL = "/data/items.json";

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

export default function PoolApp({ stats, windowDays, initialItems }: Props) {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterState>(initialFilter);
  const [mode, setMode] = useState<ViewMode>("pool");
  const [cur, setCur] = useState(0);
  // 服务端渲染时读不到 localStorage，首屏必须是空集合，否则客户端首次渲染
  // 与 SSR 输出不一致，React 会判定 hydration mismatch 并整树重渲染。
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    setSelected(loadSelection());
    setRestored(true);
  }, []);

  // 构建期只内联首屏可见的前若干条，完整列表由浏览器单独请求，可独立缓存。
  useEffect(() => {
    let cancelled = false;
    fetch(DATA_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ items: Item[] }>;
      })
      .then((payload) => {
        if (cancelled) return;
        setItems(payload.items);
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

  // 恢复完成前不写回，否则会把刚读到的勾选覆盖成空数组
  useEffect(() => {
    if (!restored) return;
    try {
      localStorage.setItem(SEL_KEY, JSON.stringify([...selected]));
    } catch {
      // 存储不可用时静默降级为仅本次会话有效
    }
  }, [selected, restored]);

  const visible = useMemo(() => filterItems(items, filter), [items, filter]);
  const selectedItems = useMemo(() => items.filter((it) => selected.has(it.id)), [items, selected]);
  const sources = useMemo(() => sourceOptions(items), [items]);

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
    if (selectedItems.length === 0) {
      alert("还没有选任何条目");
      return;
    }
    const lines = [`# AI 情报简报（自选 ${selectedItems.length} 条）`, "", "> 由 AInformer 生成，筛选由人完成。", ""];
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

      <div className="wrap main">
        {mode === "pool" ? (
          <>
            <Toolbar
              filter={filter}
              sources={sources}
              onChange={setFilter}
              onSelectVisible={() =>
                setSelected((prev) => {
                  const next = new Set(prev);
                  visible.forEach((it) => next.add(it.id));
                  return next;
                })
              }
              onClear={() => setSelected(new Set())}
              onExport={exportMarkdown}
            />
            <ItemList items={visible} selected={selected} onToggle={toggle} />
            {loadError ? (
              <div className="empty">完整列表加载失败（{loadError}），当前仅显示构建期保留的 {initialItems.length} 条。刷新重试。</div>
            ) : null}
          </>
        ) : (
          <BriefView items={selectedItems} cur={cur} onSelect={selectAt} onRemove={toggle} />
        )}
      </div>
    </>
  );
}
