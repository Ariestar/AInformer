#!/usr/bin/env python3
"""publish.py —— 一条命令跑完「抓取 → 判断 → 导出 → 构建站点 → 生成 feed → 部署」

用法：
    export AINFORMER_BASE_URL=https://your-site.pages.dev
    uv run python bin/publish.py              # 全跑，最后部署到 Cloudflare Pages
    uv run python bin/publish.py --no-deploy  # 只重建 out/，不部署
    uv run python bin/publish.py --no-triage  # 跳过 Jev 判断层
    uv run python bin/publish.py --limit 60   # feed 最多 60 条

设计说明：
    - 每步失败立刻停，绝不用旧产物顶替。半成品宁可不上线。
    - 站点由 web/ 下的 Astro 构建，产物直接写进 out/；Astro 构建会清空 out/，
      所以 feed.xml 必须排在构建之后。
    - 部署走 bunx（不依赖 npm / 全局安装）。
    - 站点地址只从环境变量或 --base-url 来，不写死 —— 写死的默认值会让
      feed 的 atom:link self 指向不存在的地址。
    - 任何一步的原始输出都直接透传，不在中间吞掉错误。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
WEB = ROOT / "web"
OUT = ROOT / "out"
BASE_URL_ENV = "AINFORMER_BASE_URL"


def run(label: str, cmd: list[str], cwd: Path = ROOT) -> None:
    print(f"\n=== {label} ===", flush=True)
    print("$ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        print(f"\n[失败] {label} 退出码 {proc.returncode}，已中止。", file=sys.stderr)
        sys.exit(proc.returncode)


def main() -> int:
    cfg = config.load(require_base_url=False)

    ap = argparse.ArgumentParser(description="抓取 → 判断 → 导出 → 构建 → feed → 部署")
    ap.add_argument("--no-deploy", action="store_true", help="只重建 out/，不部署")
    ap.add_argument("--no-triage", action="store_true", help="跳过 Jev 判断层")
    ap.add_argument("--limit", type=int, default=cfg.feed_limit, help="feed 最多多少条")
    ap.add_argument("--per-source", type=int, default=cfg.feed_per_source, help="单源配额")
    ap.add_argument(
        "--base-url", default=cfg.base_url, help="站点根地址，默认取 AINFORMER_BASE_URL"
    )
    ap.add_argument(
        "--project", default=None, help="Cloudflare Pages 项目名，默认由 wrangler.toml 的 name 决定"
    )
    args = ap.parse_args()

    # 地址先解析：feed 的 atom:link self 依赖它，缺了就别开始跑
    base = (args.base_url or "").strip().rstrip("/")
    if not base:
        print("缺少站点根地址。设 AINFORMER_BASE_URL，或传 --base-url。", file=sys.stderr)
        return 2
    os.environ[BASE_URL_ENV] = base  # 子进程共用同一个地址

    # 前端构建与部署都依赖 bun，缺了在第一步就报，别等到第 4 步才炸
    bun = shutil.which("bun")
    if not bun:
        print("找不到 bun。前端构建需要 bun，装好后再跑：https://bun.sh", file=sys.stderr)
        return 2

    py = sys.executable

    run("1/6 抓取源", [py, str(BIN / "fetch.py")])

    if not args.no_triage:
        run("2/6 Jev 判断", [py, str(BIN / "triage.py")])
    else:
        print("\n=== 2/6 Jev 判断（已跳过）===")

    run("3/6 导出前端契约", [py, str(BIN / "export.py")])

    run("4/6 构建站点", [bun, "run", "build"], cwd=WEB)

    run(
        "5/6 生成 feed",
        [
            py,
            str(BIN / "build_feed.py"),
            "--limit",
            str(args.limit),
            "--per-source",
            str(args.per_source),
            "--base-url",
            base,
        ],
    )

    if args.no_deploy:
        print("\n=== 6/6 部署（已跳过）===")
        print(f"产物在 {OUT}")
        return 0

    deploy = [bun, "x", "wrangler@4", "pages", "deploy", "--branch", "main", "--commit-dirty=true"]
    if args.project:
        deploy += ["--project-name", args.project]
    run("6/6 部署到 Cloudflare Pages", deploy, cwd=ROOT)

    print(f"\n完成。站点 {base}")
    print(f"      RSS  {base}/feed.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
