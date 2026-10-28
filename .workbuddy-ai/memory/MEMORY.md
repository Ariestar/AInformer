# 项目长期记忆

## 协作约定

- **报告一律直接输出到对话，不要写成 md 文件放进仓库。**
  用户明确要求过（2026-10-28）。分析、对比、评审类内容都在回复里给全，
  不生成 `docs/*.md` 交付物。只有用户点名要文件时才落盘。
- 提交信息用英文（遵循 AGENTS.md 的 Communication 条款），
  项目内的注释、文档、页面文案保持中文。

## 仓库与命名（2026-10-28 起）

- 唯一工作目录：`D:\Coding\AInformer`（远端 `github.com/Ariestar/AInformer`）。
  原来的 `D:\Coding\ai_news` 已清空废弃，不要再引用它。
- 分支：`main` = AInformer 本体（原 ai-intel 代码）；
  `legacy` = 早期 AInformer 抓取服务（FastAPI + api/rss/scrape 适配器 + RSSHub）。
- 全量改名已完成（commit `f946dce`，`refactor!:`）：
  - 包名 `ai-intel` → `ainformer`（pyproject / package.json / uv.lock）
  - 环境变量 `AI_INTEL_BASE_URL` → **`AINFORMER_BASE_URL`**
  - Cloudflare Pages 项目名 `ai-intel` → `ainformer`，**线上地址会变**，
    旧的 `ai-intel-63f.pages.dev` 停用，RSS 订阅者需换源
- `gh` CLI 认证失效（GITHUB_TOKEN 与 keyring token 均无效），但 git push
  走 Git Credential Manager 可用。需要 gh 操作（改名、PR）前先 `gh auth login`。

## 项目事实

- 站点地址只能通过 `AINFORMER_BASE_URL` 或 `--base-url` 传入，代码里没有默认值。
- 打包/运行统一走 `uv`（`uv run python bin/xxx.py`）。
- `bin/triage.py` 是断头路：产出 `data/triage.json`，但站点和 feed 都不读它。
  用户决定「先不介入」，保持现状，不要擅自接线或删除。
- 抓取层能力缺口（scrape / api / RSSHub / 正文提取 / pytest）还在 `legacy` 分支上，
  尚未迁移到 main。
- `sources.toml` 的 `user_agent` 是 `ainformer/1.0`（非浏览器 UA），
  微软 Copilot 那个 403 源其实没修好——文档里写着"换浏览器 UA 即 200"，
  但没落到配置上。
