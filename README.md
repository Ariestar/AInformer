# AInformer

AI 行业情报系统：多源抓取 → 事实标注 → 单页站点 + RSS。

设计原则一句话：**机器不替人筛**。抓回来的条目原样呈现，取舍由使用者决定。

## 它做什么

| 步骤 | 脚本 | 产物 |
|---|---|---|
| 抓取 + 归一 + 去重 | `bin/fetch.py` | `data/items.json` |
| 事实标注（可选） | `bin/triage.py` | `data/triage.json` |
| 源健康检查 | `bin/health.py` | `data/health.json`、`health_log.jsonl` |
| 导出前端契约 | `bin/export.py` | `web/public/data/items.json` |
| 渲染条目池 | `web/`（Astro + React 岛屿） | `out/index.html` |
| 生成 RSS 2.0 | `bin/build_feed.py` | `out/feed.xml` |
| 一条命令全跑 | `bin/publish.py` | 以上全部 + 部署 |

`data/` 和 `out/` 都是可重建产物，不入库。

## 快速开始

需要 Python ≥ 3.11、[uv](https://docs.astral.sh/uv/) 和 [bun](https://bun.sh)。

```bash
uv sync
cd web && bun install && cd ..

export AINFORMER_BASE_URL=https://your-site.pages.dev

uv run python bin/fetch.py
uv run python bin/export.py
cd web && bun run build && cd ..
uv run python bin/build_feed.py
```

改界面时用带热更新的开发服务器：

```bash
cd web && bun run dev
```

`out/` 是一个完整的静态站点，**要通过 HTTP 访问**（`cd web && bun run preview`，
或部署后访问）：条目数据放在 `/data/items.json`，由浏览器单独请求，直接双击
`out/index.html` 会因浏览器对 `file://` 的限制读不到数据。页面提供搜索、按源筛选、
只看官方源、只看有日期、勾选导出 Markdown，以及深浅色切换。

## 信息源

源清单写在 `sources.toml`，17 个源分三级：

| tier | 含义 | 数量 |
|---|---|---|
| `official` | 一手事实，官网/官方博客 | 6 |
| `media` | 只做交叉验证，不能作为唯一事实来源 | 9 |
| `aggregator` | 只当线索，必须回到一手源确认 | 2 |

只收有 RSS/Atom 的源，不做 HTML 抓取兼容。改源只改这一个文件。

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `AINFORMER_BASE_URL` | 是 | 站点根地址。feed 的 `atom:link self` 依赖它，**没有默认值**，缺了直接退出码 2 |
| `TYPESAFE_API_KEY` | 否 | 只有跑 `bin/triage.py` 时需要 |

## 部署

```bash
uv run python bin/publish.py              # 抓取 → 建站 → feed → 部署
uv run python bin/publish.py --no-deploy  # 只重建 out/
```

`out/` 整个目录就是一个可部署站点。默认走 `bunx wrangler@4 pages deploy`，
项目名由 `wrangler.toml` 的 `name` 决定，`--project` 可覆盖。
Cloudflare 的 CORS 与缓存头在 `web/public/_headers`，随前端构建进入 `out/`。

线上：

- 站点 https://ainformer.pages.dev
- RSS https://ainformer.pages.dev/feed.xml

## 目录

```
bin/           六个脚本，每个只干一件事
web/           站点源码：Astro 页面 + React 岛屿 + 一份样式表
schema/        前端数据契约，items.json 的唯一真相
sources.toml   源清单（唯一需要日常改的文件）
regression/    历史取舍记录与基线（人工参考，不参与构建）
docs/          源清单与提示词手册
```

## 已知边界

- **判断层未接线**：`bin/triage.py` 会产出 `data/triage.json`，但站点和 feed
  目前都不读它。它现在只作为一个可单独运行的标注工具存在。
- **未覆盖的源**：Anthropic 官网无 feed、微软 Copilot 博客 403、阿里/字节/百度
  只有公众号。每期简报的「待人工核实」里应如实写明。
- **没有自动化测试**：`regression/` 是人工基线，不是测试套件。

## 相关

仓库的 `legacy` 分支保留了早期的 AInformer 抓取服务（FastAPI + CLI +
`api`/`rss`/`scrape` 适配器 + RSSHub）。它和本项目是上下层关系：那边是采集层，
这边是成品。
