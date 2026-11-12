import { useEffect, useId, useRef, useState } from "react";

interface Option {
  value: string;
  label: string;
}

interface Props {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  ariaLabel: string;
}

// 自写下拉：原生 <select> 的打开弹层是系统渲染、无法主题化，与本站手绘图标风格冲突。
// 这里用按钮 + 弹层重做，连选项列表也走 DESIGN.md 的 token；支持方向键 / Home / End / Enter / Esc / 点击外部关闭。
export default function Select({ value, options, onChange, ariaLabel }: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const baseId = useId();

  const currentIndex = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  );
  const currentLabel = options[currentIndex]?.label ?? "";

  // 打开时把高亮对齐到当前选中项，并把焦点移入弹层
  useEffect(() => {
    if (!open) return;
    setActive(currentIndex);
    const id = requestAnimationFrame(() => listRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open, currentIndex]);

  // 键盘移动高亮后把目标项滚入可视区
  useEffect(() => {
    if (!open) return;
    const el = listRef.current?.querySelector<HTMLElement>(`#${CSS.escape(`${baseId}-${active}`)}`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active, open, baseId]);

  // 点击控件外部关闭
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  function choose(i: number) {
    const opt = options[i];
    if (!opt) return;
    onChange(opt.value);
    setOpen(false);
    btnRef.current?.focus();
  }

  function onButtonKey(e: React.KeyboardEvent) {
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
      e.preventDefault();
      setOpen(true);
    }
  }

  function onListKey(e: React.KeyboardEvent) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActive((a) => Math.min(a + 1, options.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActive((a) => Math.max(a - 1, 0));
        break;
      case "Home":
        e.preventDefault();
        setActive(0);
        break;
      case "End":
        e.preventDefault();
        setActive(options.length - 1);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        choose(active);
        break;
      case "Escape":
        e.preventDefault();
        setOpen(false);
        btnRef.current?.focus();
        break;
      case "Tab":
        setOpen(false);
        break;
    }
  }

  return (
    <div className="sel" ref={wrapRef}>
      <button
        type="button"
        className="sel-btn"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={onButtonKey}
        ref={btnRef}
      >
        <span className="lbl">{currentLabel}</span>
        <svg
          className="chev"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M4 6l4 4 4-4" />
        </svg>
      </button>
      {open ? (
        <div
          className="sel-menu"
          role="listbox"
          aria-label={ariaLabel}
          aria-activedescendant={`${baseId}-${active}`}
          tabIndex={-1}
          ref={listRef}
          onKeyDown={onListKey}
        >
          {options.map((o, i) => {
            const selected = o.value === value;
            return (
              <div
                key={o.value}
                id={`${baseId}-${i}`}
                role="option"
                aria-selected={selected}
                tabIndex={-1}
                className={i === active ? "sel-opt active" : "sel-opt"}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    choose(i);
                  }
                }}
              >
                <span className="lbl">{o.label}</span>
                <svg
                  className="ck-svg"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3.5 8.5l3 3 6-6.5" />
                </svg>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
