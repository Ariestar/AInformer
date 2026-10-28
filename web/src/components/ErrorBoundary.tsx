import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

// 岛屿内部任何渲染错误都会让 React 卸载整棵树，没有边界就是整页空白。
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("页面渲染失败", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="wrap main">
          <div className="empty">
            页面出错了：{this.state.error.message}
            <br />
            <br />
            <button className="btn" type="button" onClick={() => location.reload()}>
              重新加载
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
