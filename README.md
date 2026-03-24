# AInformer

AInformer 是一个用 Python 编写的 AI 信息采集服务，提供统一的 SDK、REST API、CLI 和内置 Dashboard。

当前版本的定位是“无状态抓取层”：

- 通过 `config/sources.toml` 注册和管理信息源。
- 使用统一的通用适配器抓取 `api`、`rss`、`scrape` 三类来源。
- 支持本地 `fixture` 源做联调和测试。
- 按请求执行标准化、正文提取和去重。
- 不包含数据库、任务队列、缓存和持久化存储。

## 功能概览

- Dashboard 页面：`/` 或 `/dashboard`
- 健康检查：`/v1/health`
- 列出全部来源：`/v1/sources`
- 查询单个来源：`/v1/sources/{source_id}`
- 触发抓取：`POST /v1/fetch`
- CLI 入口：`ainformer`

## 运行要求

- Python `3.12+`
- `uv`
- Docker
- Docker Compose
- 可访问外部 RSS/API/网页的网络环境
- 如果使用 `rsshub://...` 形式的源，需要可用的自建 RSSHub 实例

## 项目结构

```text
AInformer/
├─ config/sources.toml        # 默认来源配置
├─ src/ainformer/api.py       # FastAPI 应用入口
├─ src/ainformer/cli.py       # CLI 入口
├─ src/ainformer/service.py   # 核心抓取服务
├─ src/ainformer/adapters.py  # 各类抓取适配器
└─ tests/                     # 测试
```

## Docker Compose 一键启动

这是当前推荐的部署方式。仓库已经内置：

- `Dockerfile`
- `docker-compose.yml`
- AInformer 服务
- 自建 RSSHub
- Redis

启动命令：

```bash
docker compose up -d --build
```

启动完成后可访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/v1/health`

查看日志：

```bash
docker compose logs -f
```

停止服务：

```bash
docker compose down
```

如果连 Redis 数据卷也一并删除：

```bash
docker compose down -v
```

默认行为：

- `ainformer` 容器监听 `8000`
- `rsshub` 在 Compose 内网通过 `http://rsshub:1200` 提供服务
- AInformer 默认直接使用自建 RSSHub，不再回退公共 `rsshub.app`

如果你需要调整来源配置，修改仓库内的 [config/sources.toml](/v:/Coding/AInformer/config/sources.toml) 后重新执行：

```bash
docker compose up -d --build
```

## 本地开发启动

### 1. 安装依赖

```powershell
uv sync
```

如果只想安装生产依赖，可以使用：

```powershell
uv sync --frozen --no-dev
```

### 2. 跑测试

```powershell
uv run pytest
```

### 3. 检查来源配置

```powershell
uv run ainformer sources list
```

查看单个来源：

```powershell
uv run ainformer sources show arxiv.ai
```

### 4. 手动抓一次数据

```powershell
uv run ainformer fetch --source-id arxiv.ai --no-include-full-text
```

抓取全部来源：

```powershell
uv run ainformer fetch-all --no-include-full-text
```

### 5. 启动 API 和 Dashboard

```powershell
uv run uvicorn ainformer.api:create_app --factory --host 127.0.0.1 --port 8000
```

启动后访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/v1/health`

## 配置说明

### 1. 来源配置文件

默认配置文件路径是：

```text
config/sources.toml
```

支持的顶层分组：

- `[api."source.id"]`
- `[rss."source.id"]`
- `[scrape."source.id"]`
- `[fixture."source.id"]`

一个最小的 RSS 配置示例：

```toml
[rss."hackernews.best"]
name = "Hacker News Best"
tags = ["community", "news"]
feed_url = "https://hnrss.org/best"
article_fetch_enabled = false
```

一个最小的抓取页配置示例：

```toml
[scrape."demo.scrape"]
name = "Demo Scrape"
tags = ["demo"]
entry_url = "https://example.com/ai"
item_selector = "article.card"
title_selector = "h2 a"
link_selector = "h2 a"
link_attr = "href"
published_at_selector = "time"
published_at_attr = "datetime"
author_selector = ".author"
excerpt_selector = ".summary"
tag_selector = ".tag"
article_fetch_enabled = true
```

### 2. 自定义配置路径

CLI 下推荐直接传 `--config`：

```powershell
uv run ainformer sources list --config .\config\sources.toml
uv run ainformer fetch --config .\config\sources.toml --source-id arxiv.ai
```

API 模式下如果不想使用默认 `config/sources.toml`，需要在进程环境中显式设置：

```powershell
$env:AINFORMER_SOURCES_CONFIG = "C:\deploy\ainformer\sources.toml"
uv run uvicorn ainformer.api:create_app --factory --host 127.0.0.1 --port 8000
```

注意：

- `AINFORMER_SOURCES_CONFIG` 是进程启动前读取的。
- 对 API 服务来说，推荐在 systemd、Docker、容器编排或启动脚本里设置它。
- 不要只把它写进 `.env` 后就指望 API 自动识别。

### 3. `.env` 的用途

服务会在“当前工作目录”或“配置文件所在目录”向上查找 `.env`，可用于放运行时变量，例如：

```dotenv
AINFORMER_RSSHUB_BASE_URL=http://127.0.0.1:1200
```

当前最常用的是：

- `AINFORMER_RSSHUB_BASE_URL`

它会影响 `rsshub://...` 形式的来源解析，例如：

```toml
[rss."anthropic.blog"]
name = "Anthropic Articles"
tags = ["company", "blog"]
feed_url = "rsshub://anthropic/news"
article_fetch_enabled = false
```

在 Docker Compose 部署里，AInformer 默认会直接访问内网中的自建 RSSHub：

```text
http://rsshub:1200
```

如果你是在宿主机直接运行 `uv run ...`，而不是运行在 Compose 网络里，通常需要自己指定：

```dotenv
AINFORMER_RSSHUB_BASE_URL=http://127.0.0.1:1200
```

### 4. 抓取策略相关字段

- `article_fetch_enabled = true` 表示在列表页/Feed 之外，继续请求文章详情页
- `full_text_policy = "excerpt_only"` 表示即使请求里要求全文，也只返回摘要，不抓取正文
- `enabled = false` 表示保留配置但禁用该来源

## 完整部署流程

当前推荐把 AInformer 和 RSSHub 一起通过 Docker Compose 部署。下面这套流程默认部署目标是一台 Linux 服务器。

### 1. 准备服务器

确保服务器已经安装：

- Docker
- Docker Compose
- Git

### 2. 拉取代码

```bash
git clone https://github.com/Ariestar/AInformer.git
cd ainformer
```

更新代码：

```bash
cd ainformer
git pull
```

### 3. 检查来源配置

上线前先检查 `config/sources.toml`：

- 删除不需要的来源
- 确认 `feed_url`、`url`、`entry_url` 可访问
- 对不需要正文的来源设置 `article_fetch_enabled = false`
- 对只要摘要的来源设置 `full_text_policy = "excerpt_only"`

### 4. 启动全套服务

```bash
cd ainformer
docker compose up -d --build
```

这条命令会同时启动：

- `ainformer`
- `rsshub`
- `redis`

### 5. 检查服务状态

```bash
docker compose ps
docker compose logs -f
```

健康检查：

```bash
curl http://127.0.0.1:8000/v1/health
curl http://127.0.0.1:8000/v1/sources
```

### 6. 对外发布

如果只是在内网用，到这里就够了。

如果要对公网发布，建议在宿主机前面再加一层 Nginx 或云负载均衡，把外部流量转发到：

```text
http://127.0.0.1:8000
```

一个最小 Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 7. 更新发布

```bash
cd /opt/ainformer
git pull
docker compose up -d --build
```

如果需要重新拉取基础镜像：

```bash
docker compose pull
docker compose up -d --build
```

### 8. 停止或清理

停止但保留数据卷：

```bash
docker compose down
```

连 Redis 数据一起清理：

```bash
docker compose down -v
```

## 常用命令

列出来源：

```bash
uv run ainformer sources list --config ./config/sources.toml
```

查看单个来源：

```bash
uv run ainformer sources show arxiv.ai --config ./config/sources.toml
```

单独抓某个来源：

```bash
uv run ainformer fetch --config ./config/sources.toml --source-id arxiv.ai --no-include-full-text
```

抓全部来源：

```bash
uv run ainformer fetch-all --config ./config/sources.toml --no-include-full-text
```

## 常见问题

### 1. API 启动了，但没有读取你指定的配置文件

优先检查：

- 是否真的设置了 `AINFORMER_SOURCES_CONFIG`
- 这个变量是不是在进程启动前就已经存在
- `systemd` 服务文件里有没有写 `Environment=AINFORMER_SOURCES_CONFIG=...`

### 2. `rsshub://...` 来源抓不到

优先检查：

- `docker compose ps` 里 `rsshub`、`redis` 是否都正常
- `AINFORMER_RSSHUB_BASE_URL` 是否指向正确地址
- 如果是宿主机直跑 `uv run`，是否把 `AINFORMER_RSSHUB_BASE_URL` 设成了 `http://127.0.0.1:1200`
- 如果某些 RSSHub 路由本身依赖浏览器渲染，当前这份 Compose 没有额外接 `browserless`，这类路由可能需要你后续单独补浏览器能力

### 3. Dashboard 很慢

这是当前架构的正常现象之一，因为：

- Dashboard 每次刷新都会实时请求全部来源
- 当前没有缓存
- 开启 `article_fetch_enabled = true` 时还会额外抓文章详情页

可以通过以下方式降低延迟：

- 减少来源数量
- 将不需要正文的来源设为 `article_fetch_enabled = false`
- 请求时关闭全文抓取
- 对只需要摘要的来源使用 `full_text_policy = "excerpt_only"`

## 说明

当前仓库更像“抓取服务基础层”，不是完整的信息平台。它适合先把来源配置、标准化接口、CLI/API 调通，再在上层接入数据库、任务队列、定时调度和前端系统。
