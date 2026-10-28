# AI 情报 RSS 源

## 官方

- OpenAI News — https://openai.com/news/rss.xml
- Google AI Blog — https://blog.google/technology/ai/rss/
- Google DeepMind — https://deepmind.google/blog/rss.xml
- GitHub Changelog — https://github.blog/changelog/feed/
- Hugging Face Blog — https://huggingface.co/blog/feed.xml
- Microsoft Research — https://www.microsoft.com/en-us/research/feed/

## 媒体

- 量子位 — https://www.qbitai.com/feed
- 机器之心 — https://wechat2rss.bestblogs.dev/feed/2f520471856d56c7b3a95cd09eb777149b32828a.xml
- 新智元 — https://wechat2rss.bestblogs.dev/feed/e531a18b21c34cf787b83ab444eef659d7a980de.xml
- PaperWeekly — https://wechat2rss.bestblogs.dev/feed/0120e999fc95e098c74bd5482a2a4c8407c42c38.xml
- Datawhale — https://wechat2rss.bestblogs.dev/feed/ea0dd8bddfe4fbfb32eaa81a1e1b628d45e97a80.xml
- 数字生命卡兹克 — https://wechat2rss.bestblogs.dev/feed/ff621c3e98d6ae6fceb3397e57441ffc6ea3c17f.xml
- 赛博禅心 — https://wechat2rss.bestblogs.dev/feed/752c31ca0446b837339463fc5440539e20267d2f.xml
- 字节跳动技术团队 — https://wechat2rss.bestblogs.dev/feed/6efd40bb335d2037f365d284cb5e00f0843e737e.xml
- 腾讯技术工程 — https://wechat2rss.bestblogs.dev/feed/1e0ac39f8952b2e7f0807313cf2633d25078a171.xml

## 聚合

- AIHOT — https://aihot.news/rss.xml
- 橘鸦AI早报 — https://daily.juya.uk/rss.xml

---

# 判断提示词

`bin/triage.py` 的 `QUESTIONS`，原样可粘。三个问题，只问客观可验证的事。

```json
{
  "is_ai_related": {
    "type": "noul",
    "instructions": "判断这条资讯的核心主题是否属于人工智能领域，包括大模型、机器学习、AI 产品与工具、AI 公司动态、AI 监管政策、AI 芯片与算力。如果 AI 只是文章顺带提及、主体是其他行业，判为否。"
  },
  "topic": {
    "type": "choice",
    "instructions": "这条资讯的主要内容属于哪一类？",
    "criteria": {
      "产品": "发布、上线、版本更新、新功能、定价调整",
      "研究": "论文、技术方法、模型能力评测、实验结果",
      "商业": "融资、收购、估值、营收、人事变动",
      "政策": "监管、法案、合规、诉讼、出口管制",
      "观点": "评论、分析、预测、访谈，没有新的事实发生",
      "其他": "以上都不是"
    }
  },
  "is_announcement": {
    "type": "noul",
    "instructions": "这条资讯是否在陈述一个已经发生、可验证的事实（发布、上线、融资、判决等）？如果主要是观点、预测或评论，判为否。"
  }
}
```

**输入 state**：`title` / `summary`（截 600 字）/ `source` / `published`
**输出**：`data/triage.json`，不排序、不打分、不删条目

**三种问题类型**
- `noul` — 0–1 概率
- `choice` — 枚举选项（≤255 个）
- `score` — 2–10 档

**注意**：`QUESTIONS` 的键名不参与推理，语义必须写在 `instructions` / `criteria` 里。

---

# 简报出稿提示词

给模型直接用的完整版。

```
你是 AI 行业情报编辑。下面是今天抓到的条目（JSON，含 title / summary /
source / tier / published / url）。按以下规则整理成一份简报。

【取舍】
- 入选必须同时满足三条：有官方原文、有明确时间、能落到具体动作。缺一条进「待人工核实」
- 不设条数上限，也不为凑数收录
- 同一事件被多源报道：合并为一条，保留最早最权威的来源作主来源，其余列「旁证」
- 媒体源（tier=media）不能作为唯一事实来源；聚合源（tier=aggregator）只当线索，
  必须回到一手源确认后才能进正文
- 没有 pubDate 的条目：保留，但必须写「来源未标注具体日期」，并在待核实里列明
- 不得用抓取时间冒充发布时间

【事实分级】每条必须标一个：
- 【已证实】官方页面/文档明确写出，带官方链接
- 【来源观点】媒体评论、分析师判断、厂商宣传性表述，注明出处
- 【我的推断】基于事实的推演，写明依据
厂商自测的性能数据，一律注明「厂商自测数据」。

【上线状态】不许混写，原文没写清就写「官方未说明」：
发布/宣布 ≠ 灰度测试 ≠ waitlist ≠ 正式可用 ≠ 仅企业版 ≠ 仅特定地区

【结构】
## 今日结论
2–3 句，说清今天最值得注意的一件事，不要罗列

## 逐条
标题 / 分类 / 发生了什么 / 为什么重要 / 适合谁关注 / 来源 / 旁证

## 建议关注
## 待人工核实
含未覆盖的源：Anthropic（官网无 feed）、微软 Copilot 博客（403）、
阿里/字节/百度等国内厂商（只有公众号）

【语气】平实陈述，不用「颠覆」「重磅」「史上最强」这类词。
不确定就写不确定，不要补全。
```

---

# 怎么跑

依赖交给 uv，Python 需 ≥ 3.11（`tomllib` 从 3.11 才有）。

```bash
uv sync                                   # 首次：按 pyproject.toml 建 .venv

export AI_INTEL_BASE_URL=https://ai-intel-63f.pages.dev

uv run python bin/fetch.py            # 抓取 → data/items.json
uv run python bin/triage.py           # 判断 → data/triage.json（需 TYPESAFE_API_KEY）
uv run python bin/build_site.py       # → out/index.html
uv run python bin/build_feed.py       # → out/feed.xml
uv run python bin/publish.py          # 一条命令跑完上面全部 + 部署
```

**站点地址不写死在代码里。** `AI_INTEL_BASE_URL` 没有默认值：feed 的
`atom:link self` 必须指向真实地址，缺了这个变量 `build_feed.py` 直接退出码 2。
`publish.py` 也认 `--base-url`，优先级高于环境变量。

**没有 TYPESAFE_API_KEY 时**：`triage.py` 会退出码 2（这是故意的，不降级）。
走 `uv run python bin/publish.py --no-triage` 跳过判断层，其余照常。

**线上地址**
- 站点 https://ai-intel-63f.pages.dev
- RSS https://ai-intel-63f.pages.dev/feed.xml

**静态配置**：Cloudflare 的 `_headers`（CORS、缓存）在 `static/_headers`，
`build_site.py` 每次构建都会把它同步进 `out/`。`out/` 不入库，别往里面手写东西。

**演示时的两个坑**
- 用脚本探活会拿到 403，Cloudflare 拦 `Python-urllib` 的 UA，换浏览器 UA 即 200。订阅器不受影响
- 部署要用 `bunx wrangler@4`，不用 npm，也不用 scoop（scoop 里那个是 legacy 1.21.0，不支持 pages deploy）

**没覆盖 ≠ 没发生**。上面三个缺口要在每期简报的「待人工核实」里如实写。
