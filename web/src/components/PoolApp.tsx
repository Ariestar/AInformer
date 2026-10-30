import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fmtDate, tierName } from "../lib/format";
import { type FilterState, filterItems, initialFilter, sourceOptions } from "../lib/select";
import type { Item, Stats, ViewMode } from "../lib/types";
import { onlyQueryChanged, readUrlState, type UrlState, writeUrlState } from "../lib/url";
import { useDebouncedValue } from "../lib/useDebounced";
import BriefView from "./BriefView";
import ItemList from "./ItemList";
import Pagination from "./Pagination";
import StatsStrip from "./StatsStrip";
import Toolbar from "./Toolbar";
import TopBar from "./TopBar";

// 勾选以条目的稳定 id 为键。
const SEL_KEY = "ainformer.selection.v1";
const DATA_URL = "/data/items.json";
const PAGE_SIZE = 50;

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
  // 输入框立即回显；过滤等 200ms 再用新值，避免每次按键全量重算。
  const [query, setQuery] = useState(filter.q);
  const [mode, setMode] = useState<ViewMode>("pool");
  const [page, setPage] = useState(1);
  const [cur, setCur] = useState(0);
  // 服务端渲染时读不到 localStorage，首屏必须是空集合，否则客户端首次渲染
  // 与 SSR 输出不一致，React 会判定 hydration mismatch 并整树重渲染。
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    setSelected(loadSelection());
    setRestored(true);
  }, []);

  const ctrlRef = useRef<AbortController | null>(null);

  // 构建期只内联首屏可见的前若干条，完整列表由浏览器单独请求，可独立缓存。
  const loadData = useCallback(() => {
    ctrlRef.current?.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    const timer = setTimeout(() => ctrl.abort(), 15000);
    setLoadError(null);
    fetch(DATA_URL, { signal: ctrl.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ items: Item[] }>;
      })
      .then((payload) => {
        if (ctrl.signal.aborted) return;
        setItems(payload.items);
        setLoaded(true);
        // 旧数据里勾选过、新数据里已不存在的 id 清掉，避免存储无限增长。
        const ids = new Set(payload.items.map((it) => it.id));
        setSelected((prev) => {
          const next = new Set([...prev].filter((id) => ids.has(id)));
          return next.size === prev.size ? prev : next;
        });
      })
      .catch((err: unknown) => {
        // 卸载时 cleanup 会 abort，此时 ctrlRef 已置空，不该再报错。
        if (ctrlRef.current !== ctrl) return;
        // 不静默降级：失败要说出来，否则用户会以为只有前几十条
        setLoadError(
          err instanceof DOMException && err.name === "AbortError"
            ? "请求超时"
            : err instanceof Error
              ? err.message
              : String(err),
        );
      })
      .finally(() => clearTimeout(timer));
  }, []);

  useEffect(() => {
    loadData();
    return () => {
      ctrlRef.current?.abort();
      ctrlRef.current = null;
    };
  }, [loadData]);

  // 恢复完成前不写回，否则会把刚读到的勾选覆盖成空数组
  useEffect(() => {
    if (!restored) return;
    try {
      localStorage.setItem(SEL_KEY, JSON.stringify([...selected]));
    } catch {
      // 存储不可用时静默降级为仅本次会话有效
    }
  }, [selected, restored]);

  // URL 承载筛选/视图/页码：进页面读一次，之后变更写回，支持分享与刷新保留。
  const [hydrated, setHydrated] = useState(false);
  const prevUrlRef = useRef<UrlState | null>(null);

  useEffect(() => {
    const s = readUrlState(location.search);
    setFilter(s.filter);
    setQuery(s.filter.q);
    setMode(s.mode);
    setPage(s.page);
    prevUrlRef.current = s;
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const next: UrlState = { filter, mode, page };
    const prev = prevUrlRef.current;
    // 打字只 replace（不刷历史），其余操作 push（后退键可回退）。
    const timer = setTimeout(() => {
      writeUrlState(next, prev && onlyQueryChanged(prev, next) ? "replace" : "push");
      prevUrlRef.current = next;
    }, 200);
    return () => clearTimeout(timer);
  }, [hydrated, filter, mode, page]);

  useEffect(() => {
    function onPop() {
      const s = readUrlState(location.search);
      setFilter(s.filter);
      setQuery(s.filter.q);
      setMode(s.mode);
      setPage(s.page);
      prevUrlRef.current = s;
    }
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // 输入防抖：只有防抖值追上当前输入、且与已生效的筛选词不同时才更新。
  const debouncedQuery = useDebouncedValue(query, 200);
  useEffect(() => {
    if (!hydrated) return;
    if (query !== debouncedQuery) return;
    if (filter.q === debouncedQuery) return;
    setFilter((prev) => ({ ...prev, q: debouncedQuery }));
    setPage(1);
  }, [hydrated, query, debouncedQuery, filter.q]);

  const visible = useMemo(() => filterItems(items, filter), [items, filter]);
  const selectedItems = useMemo(() => items.filter((it) => selected.has(it.id)), [items, selected]);
  const sources = useMemo(() => sourceOptions(items), [items]);

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const paged = useMemo(
    () => visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [visible, page],
  );

  // 筛选条件变化后回到第一页；页码越界时夹回最后一页。
  const changeFilter = useCallback((next: FilterState) => {
    setFilter(next);
    setPage(1);
  }, []);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

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

  // 总数在构建期已知，不随加载状态跳变；加载完成前"当前显示"只算真正渲染出来的条数。
  const total = stats.after_dedup;
  const shown = loaded ? visible.length : initialItems.length;

  return (
    <>
      <a className="skip" href="#main">
        跳到主内容
      </a>
      <TopBar mode={mode} total={total} selectedCount={selected.size} onModeChange={setMode} />
      <StatsStrip
        sourcesOk={stats.sources_ok}
        sourcesTotal={stats.sources_total}
        fetched={stats.raw_items}
        shown={shown}
        selected={selected.size}
        windowDays={windowDays}
      />

      <main className="wrap main" id="main">
        {mode === "pool" ? (
          <>
            <div className="sr-only" aria-live="polite">
              共 {visible.length} 条，第 {page} / {pageCount} 页
            </div>
            <Toolbar
              filter={filter}
              query={query}
              sources={sources}
              selectedCount={selected.size}
              onChange={changeFilter}
              onQueryChange={setQuery}
              onSelectVisible={() =>
                setSelected((prev) => {
                  const next = new Set(prev);
                  paged.forEach((it) => {
                    next.add(it.id);
                  });
                  return next;
                })
              }
              onClear={() => setSelected(new Set())}
              onExport={exportMarkdown}
            />
            {!loaded && !loadError ? (
              <div className="hint" role="status">
                正在加载完整列表…
              </div>
            ) : null}
            <ItemList
              items={paged}
              selected={selected}
              onToggle={toggle}
              footer={
                <Pagination
                  page={page}
                  pageCount={pageCount}
                  total={visible.length}
                  onChange={setPage}
                />
              }
            />
            {loadError ? (
              <div className="empty">
                完整列表加载失败（{loadError}），当前仅显示构建期保留的 {initialItems.length} 条。
                <br />
                <br />
                <button className="btn" type="button" onClick={loadData}>
                  重试
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <BriefView items={selectedItems} cur={cur} onSelect={selectAt} onRemove={toggle} />
        )}
      </main>
    </>
  );
}
