# Runbook

一页纸。出问题先看这里。

## 目录结构

```
ai-intel/
├── sources.toml        改源：加/删源、调时间窗、开关自动屏蔽
├── rules.md            筛选参考：给人看的，不是给机器执行的
├── wrangler.toml       Cloudflare Pages 项目配置（同时锚定「项目根」，别删）
├── package.json        同上，锚定项目根用（别删，见「两个踩过的坑」）
├── bin/
│   ├── fetch.py        拉取 + 标准化 + 去重 → data/items.json
│   ├── health.py       源健康检查 → data/health.json
│   ├── triage.py       旁路判断层（Jev）→ data/triage.json
│   ├── build_site.py   渲染条目池 → out/index.html
│   ├── build_feed.py   情报池 → out/feed.xml（RSS 2.0）
│   └── publish.py      一条命令：抓取 → 建站 → feed → 部署
├── data/               机器产物，不要手改
├── out/                页面产物，整个目录就是一个可部署站点
└── regression/
    ├── cases.tsv       历史取舍记录
    └── baseline/       历史基线
```

## 每天怎么跑

```bash
python bin/fetch.py --days 5
python bin/build_site.py
```

→ `out/index.html`：单文件，双击打开。里面是**全部条目**，带筛选、搜索、勾选、导出。

机器不替你筛。`fetch.py` 只做三件事：拉取、标准化、去重。`blacklist` 默认是空的。
你要屏蔽某类消息，要么在页面上筛，要么往 `sources.toml` 的 `blacklist` 里加词。

## 每周怎么查

```bash
python bin/health.py
```

看三类异常：
- **拉取失败**：域名改了、反爬加了、源关了
- **连续 3 次零新增**：源还活着但内容断了，最隐蔽
- **最新条目超过 30 天**：可能已停更

## 发布成 RSS

**线上已经跑起来了：**

| | |
|---|---|
| 站点 | https://ai-intel-63f.pages.dev |
| RSS | https://ai-intel-63f.pages.dev/feed.xml |
| 托管 | Cloudflare Pages，项目名 `ai-intel` |

一条命令跑完：

```bash
python bin/publish.py
```

内部顺序：`fetch.py` → `triage.py` → `build_site.py` → `build_feed.py` → 部署。
任何一步失败立刻停，不用旧产物顶替 —— 半成品宁可不上线。

只想重建、不部署：

```bash
python bin/publish.py --no-deploy
```

`out/` 目录同时有 `index.html` 和 `feed.xml` —— **整个目录就是一个可部署站点**。
闭环了：你订阅别人，也被别人订阅。

### feed 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--limit` | 100 | 最多输出多少条 |
| `--per-source` | 10 | 单源配额，`0` = 不限 |
| `--days` | 0 | 只发最近 N 天 |
| `--tier` | 全部 | `official,media,aggregator` 任选 |
| `--base-url` | 见下 | 部署后的站点根地址，写进 `atom:link self` |

`--base-url` 默认读环境变量 `AI_INTEL_BASE_URL`，再回落到 `build_feed.py` 里的
`DEFAULT_BASE_URL`（当前是 `https://ai-intel-63f.pages.dev`）。
**换域名或绑自定义域名时改那一处**，之后所有调用都跟着变。

**为什么要按源配额**：纯按时间排序会奖励更新频率高的源。
AIHOT 两天发 50 条，不加配额会把官方源全挤到 100 名之外。
配额不是判断重要性，是**结构平衡** —— 每个源拿一样的份额，比按频率排序更中立。

### 部署：为什么是 bunx，不是 npm，也不是 scoop

三条路都试过，结论：

| 方式 | 结果 |
|---|---|
| `scoop install wrangler` | ❌ 装的是 **legacy 1.21.0**（Rust 版，已被主 bucket 移进 `deprecated/`），从没支持过 `pages deploy` |
| `npm i wrangler` | ⚠️ 能用，但污染全局/项目 `node_modules`，且本机 `C:\Users\package.json` 会让 npm 把 prefix 解析到 `C:\Users` |
| `bunx wrangler@4` | ✅ 走 bun 缓存，不落项目目录，当前 4.152.0 |

所以部署命令固定为：

```bash
bunx wrangler@4 pages deploy --branch main --commit-dirty=true
```

`wrangler.toml` 里已经写了 `pages_build_output_dir = "out"` 和 `name = "ai-intel"`，
不用再传目录和项目名。

### 凭据

已用 OAuth 登录（`wolllf@sair-club.com`），token 存在
`C:\Users\19411_4bs7lzt\.config\.wrangler\config\default.toml`，带 `pages (write)` 权限。

换机器或 token 失效时：

```bash
bunx wrangler@4 login      # 交互式 OAuth，浏览器点一下
bunx wrangler@4 whoami     # 验证，会列出 Account ID 和权限
```

### 两个踩过的坑

**1. `EPERM mkdir 'C:\Users\.wrangler\tmp'`**

wrangler 的 Pages 模块用 `file("package.json")` **向上查找**来定位「项目根」。
本机 `C:\Users\` 下有个 2026-03-09 留下的空 `package.json`（内容 `{}`），
于是项目根被解析成 `C:\Users`，tmp 目录也跟着跑偏，权限拒绝。

解法：在 `ai-intel/` 放一个自己的 `package.json`，让查找先命中。已加，别删。

**关于删掉 `C:\Users\package.json`**：试过，删不了。`C:\Users` 目录本身对当前用户
（`Andrews`）没有写权限 —— 连 `touch C:/Users/_test` 都是 Permission denied。
要清掉得用管理员权限：

```
# 管理员 PowerShell 或 CMD
del C:\Users\package.json
```

同目录还有个 `package-lock.json`（84 B，`name: "Users"`，零依赖），是同一批 `npm init`
留下的。**不删也没影响** —— 只要 `ai-intel/package.json` 在，wrangler 的根目录解析就
先命中项目内的那个。所以这事不急，不值得为它提权。

已备份到 `.workbuddy-ai/backup/C-Users-npm-20261023/`。

**2. 用脚本探活会拿到 403**

Cloudflare 会拦 `Python-urllib/3.x` 这类 UA。同一个 URL 换浏览器 UA 就是 200。
**订阅器不受影响**，只是自己写探活脚本时要带 UA。

### 响应头（`out/_headers` 已生效）

```
/feed.xml     Access-Control-Allow-Origin: *    Cache-Control: public, max-age=600
```

线上实测确认：`feed.xml` 带 CORS，任何网页应用都能直接 `fetch`；
10 分钟缓存，够用又不至于让人等太久。

### 每天定时

Windows 任务计划程序 / cron，每天跑一次 `python bin/publish.py` 即可。
失败会停在出错那一步，不会把半成品推上线。


## Jev 判断层（旁路，无降级）

```bash
export TYPESAFE_API_KEY=...
python bin/triage.py
python bin/triage.py --dry-run   # 只打印请求体，不调用、不写文件
```

它只回答三个**事实判断**：这条属不属于 AI 领域、属于哪一类、是既成事实还是观点。
输出 `data/triage.json`，**不排序、不打重要性分、不从池里删任何条目**。

**只有一条路径，没有 fallback。** 没有 key 就退出码 2 并说明原因，不假装跑过；
某一条调用失败就整体失败、不写文件，不留半真半假的结果。
`data/triage.json` 缺失时下游正常工作——这是"没跑"，不是"跑了但降级"。

设计上故意做成旁路：`fetch.py` 一行不改，删掉 `bin/triage.py` 和 `data/triage.json`，
系统回到原样，不留残渣。

**为什么不能让它做"哪条重要"**：那是价值判断，是这个系统唯一必须由人做的部分。
模型能做的是"这条是不是重复""这条是不是 AI"——有客观答案的事。

### 规则引擎删掉了，但它的实测数据留着

先做过一版关键词规则引擎，量出它的上限之后删掉了。数据留着，因为它就是"为什么必须上模型"的论据：

| 判断 | 规则引擎实测（2026-10-23） |
|---|---|
| AI 相关 | 102/128，靠"源先验 + 关键词"；`Kling`、`FLUX`、`granite` 这类新模型名永远补不完 |
| 类型 | 34 条落进"其他"，因为中文快讯的措辞和词表对不上 |
| 去重 | 真重复对 0.600、财报模板对 0.525，分离度只有 0.075 |

留着它当降级是错的：两套判断同时存在，跑出来的东西不一样，你永远不知道看到的是哪一套。
**要么用模型判，要么承认没判。**

### 一个可以直接拿去讲的实例

2026-10-23 的池子里，同一件事被三个源报了：

- `openai_news`：Build more responsive apps with the **Decisions API**（英文，官方一手）
- `aihot`：OpenAI 正式发布 **Decisions API**，面向低延迟低成本小决策（中文，聚合）
- `juya_daily`：2026-10-23 这一期日报里也提到（中文，聚合）

**规则去重一条都没抓到。** 不是阈值没调好——中英改写之间没有任何字面重叠，
这是字面匹配的原理性天花板。想看"同一件事被几个源报道"，只能靠模型。

反过来说，这也解释了为什么加聚合源之后条目数翻倍但信息增量没那么大：
重复是真实存在的，只是你看不见。

## 关于 Jev

**它是什么**：TypeSafe AI 2026-09-15 发布的 System One 决策模型。不生成文本，
只返回带校准概率的结构化判断（Choice / Score / Noul），端到端 70–500ms，
按输入 token 计费、输出免费。基于 RLCD 训练，概率是校准过的——说 0.9 把握就有九成对。

**它不是什么**：不能写简报、不能总结、不能解释理由。**如果你想让它"总结今天的资讯"，它做不到。**
它只做判断题，不做作文题。

**接入前的三个硬约束**：

1. **未向中国大陆开放**，早期访问制。要么走 OpenRouter，要么走兼容中转
   （`TYPESAFE_BASE_URL`），要么用开源复现（APUS `fast-browser-use`，MIT）。
2. **发布不足六周，v1.13**。已知弱项是数字、日期、对抗性内容——正好是资讯场景的常见元素，
   所以 `published`、融资额这类字段不要交给它，继续用规则解析。
3. **打破零依赖**。现在整个 `ai-intel/` 是纯 stdlib、离线可跑。加了它就是多一个云端依赖，
   演示现场网络出问题会影响这一层——所以必须做成旁路，不能进主链路。

**什么时候值得切到 Jev**：源超过 10 个、或中文源占比过半、或每天条目过百。
在此之前规则够用，多一个依赖只是多一个坏点。

## 出问题查哪里

| 症状 | 先查 | 处理 |
|---|---|---|
| 某源没内容 | `data/items.json` 的 `sources[]` 里该源的 `error` | 打开 url 看是否 404/403；换地址或停用 |
| 简报里出现旧闻 | 该条的 `published` | 源没给 pubDate，或给了抓取时间；按 rules.md 第七节处理 |
| 同一事件出现两次 | 两条的 `title` | 加进 `regression/cases.tsv` 标 MERGE，下次按规则合并 |
| 全是营销稿 | `sources.toml` 的 `[filter].blacklist` | 加关键词；但优先砍源，别堆词 |
| 改了规则不知道好坏 | `regression/cases.tsv` | 跑一遍，看漏杀和误收 |

## 想改东西，改哪个文件

| 想做什么 | 改这里 | 不要改 |
|---|---|---|
| 加/删源 | `sources.toml` | `fetch.py` |
| 调整时间窗 | `sources.toml` 的 `days` | `fetch.py` |
| 淘汰某类消息 | `sources.toml` 的 `blacklist` 或 `rules.md` | `fetch.py` |
| 改简报结构 | `templates/briefing.md` | 代码 |
| 改判断逻辑 | `rules.md` | 代码 |
| 调"是不是 AI / 属于哪类"的事实判定 | `bin/triage.py` 的 `QUESTIONS` | `rules.md` |

**如果某次改动需要动 `fetch.py`，先问一句：这是不是本该做成配置？**

## 设计系统

页面按 **Violet Issue**（DESIGNmd，MIT）实现：https://designmd.ai/chef/violet-issue

- 颜色、字号、间距、圆角全部取自该系统，不自创数值
- 改主题只改 `bin/build_site.py` 顶部的 `:root` 变量块
- **一处刻意偏离**：设计系统指定 Inter / JetBrains Mono 走 Google Fonts，这里改成系统字体栈。
  原因是国内网络访问 Google Fonts 不稳定，投屏演示时字体请求失败会拖慢首屏。字体名仍保留在 font-family 里，本地装了就会生效。

## 维护节奏

| 频率 | 事项 | 工时 |
|---|---|---|
| 每周 | 跑 health.py，处理告警；看一次待核实 | 15 分钟 |
| 每月 | 源审计：关掉死的、补新出现的 | 30 分钟 |
| 每季度 | 按 cases.tsv 调一次判断标准 | 1-2 小时 |

超过 4 小时/月，说明配置没分离干净。

## 已知缺口

- **Anthropic**：官网无 RSS（`/rss.xml` 返回 404），当前未覆盖。若必须覆盖，需单独写适配器，但会引入维护成本。
- **微软 Copilot 博客**：feed 返回 403，当前未覆盖。
- 中国大陆厂商（阿里、字节、百度等）多只有公众号，无原生 feed。

**36氪已移除**（2026-10-23）。原因是信噪比：30 条里 21 条是财报和宏观快讯，
AI 相关只有 9 条；而且它的 RSS 不带 pubDate，所有条目都落在"无日期"里。
综合媒体不是不能接，是**不值得占一个源位**——同样三十分钟的阅读时间，
拿去读公众号的 AI 专稿收益高得多。

### 源分三级，别混着用

| tier | 含义 | 能当什么 |
|---|---|---|
| `official` | 厂商官方发布 | **事实依据**，可直接引用 |
| `media` | 媒体采写（量子位、机器之心） | 交叉验证，需回原文核对 |
| `aggregator` | 聚合转述（AIHOT、橘鸦） | **只当线索**，必须回到一手源确认 |

聚合源的价值不是信息量，是**覆盖**：它们补上了 X/KOL、国内媒体、中文语境下的取舍，
这些你自己订阅不到。代价是二手失真 + 重复，所以不能升格成事实依据。

橘鸦还有个粒度问题：一天一期日报，一期 = 一条 feed item。所以它永远只有 10 条左右，
但每条背后是当天几十条资讯。别拿它的条目数当信息量看。

这些缺口要在每期简报的「待人工核实」里如实写明——**没覆盖 ≠ 没发生**。

## 源接入审计（2026-10-23 逐个实测）

### 已接入 17 个

| 源 | tier | feed |
|---|---|---|
| OpenAI News | official | `openai.com/news/rss.xml` |
| Google AI Blog | official | `blog.google/technology/ai/rss/` |
| Google DeepMind | official | `deepmind.google/blog/rss.xml` |
| GitHub Changelog | official | `github.blog/changelog/feed/` |
| Hugging Face Blog | official | `huggingface.co/blog/feed.xml` |
| Microsoft Research | official | `microsoft.com/en-us/research/feed/` |
| 量子位 | media | `qbitai.com/feed` |
| 机器之心 | media | wechat2rss |
| 新智元 | media | wechat2rss |
| PaperWeekly | media | wechat2rss |
| Datawhale | media | wechat2rss |
| 数字生命卡兹克 | media | wechat2rss |
| 赛博禅心 | media | wechat2rss |
| 字节跳动技术团队 | media | wechat2rss（已停更，见下） |
| 腾讯技术工程 | media | wechat2rss |
| AIHOT | aggregator | `aihot.news/rss.xml` |
| 橘鸦AI早报 | aggregator | `daily.juya.uk/rss.xml` |

具体 hash 地址见 `sources.toml`。2026-10-23 实测 17/17 全部 HTTP 200，156 条。
`bytedance_tech` 最后更新 2026-08-05，窗口内 0 条，fetch 标 `[zero]` —— 这是真实停更，不是故障。

### 有 feed 但故意没接

| 源 | feed | 为什么没接 |
|---|---|---|
| 雷峰网 | `leiphone.com/feed` | 科技媒体，AI 占比中等 |
| InfoQ 中国 | `infoq.cn/feed` | 技术社区，AI 只是板块之一 |
| 掘金 | `juejin.cn/rss` | 全站热榜，前端/移动端混杂 |
| IT之家 | `ithome.com/rss/` | 综合科技，AI 占比低 |
| 少数派 | `sspai.com/feed` | 效率工具，基本不涉 AI |

现在 17 个源全部是 AI 专源或 AI 聚合源，信噪比是干净的。加这五个综合源会把它稀释掉。
要接就先问一句：**你愿意为多出来的 10% 覆盖，付出多看 100 条噪声的代价吗？**

### 公众号：不是没有 RSS，是没有官方 RSS

第一次审计时我判断"这些源都没有 RSS"，**这个判断是错的**，已经纠正。

实测下来分三种情况：

| 情况 | 例子 | 结论 |
|---|---|---|
| 官网 `/rss` 存在但已变成招商页 | 机器之心 | 公开 feed 关了，转成付费数据服务 |
| 官网根本没有 feed | 新智元、智源、Datawhale | 只能走第三方转换 |
| 官网域名已死 | PaperWeekly | 只能走第三方转换 |

机器之心的 `/rss` 现在返回的是一个 3 KB 的落地页，原文写着
「还在费劲爬数据？机器之心数据服务已上线，直接获取数据，高效又稳定！」——
**不是反爬，是商业决策**。这个 URL 还挂在首页上，但已经不是 feed 了。

### 公众号的正确解法：wechat2rss

BestBlogs 维护了一个 wechat2rss 实例，把 375 个公众号转成了标准 RSS：

- OPML 清单：`github.com/ginobefun/BestBlogs/blob/main/opml/bestblogs_wechat2rss_opml_all.opml`
- 单源地址形如：`https://wechat2rss.bestblogs.dev/feed/<sha1>.xml`
- 实测 8 个号全部可用，pubDate 准确，每个 feed 给最近 10 篇

**代价要说清楚**：转换器挂了是静默的，表现为源长期零新增。
`health.py` 的"连续 3 次零新增"就是为这种情况准备的，**别把它当误报**。
另外每个 feed 内嵌全文 HTML（0.3–1.6 MB），抓取会明显变慢。

### 仍然接不了的

| 源 | 原因 |
|---|---|
| 智源研究院 | 官网 `baai.ac.cn` 无 feed，`hub.baai.ac.cn/rss` 404，也不在 375 个号的清单里 |
| 葬AI / AIPaperWrite | 不在 wechat2rss 清单里。要接得自己找号或自建实例 |
| 微软亚洲研究院 | 没有独立公众号 feed；用官方博客 `microsoft.com/en-us/research/feed/` 覆盖（已接） |

