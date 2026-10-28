import type { Item, Stats } from "../lib/types";
import ErrorBoundary from "./ErrorBoundary";
import PoolApp from "./PoolApp";

interface Props {
  stats: Stats;
  windowDays: number;
  initialItems: Item[];
}

// 岛屿只能有一个入口：ErrorBoundary 必须和它保护的内容在同一个 React 树里，
// 用 Astro 的 slot 包一层是无效的（子节点会被序列化成静态 HTML，不再 hydrate）。
export default function App(props: Props) {
  return (
    <ErrorBoundary>
      <PoolApp {...props} />
    </ErrorBoundary>
  );
}
