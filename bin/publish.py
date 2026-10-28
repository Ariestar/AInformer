#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish.py —— 一条命令跑完「抓取 → 建站 → 生成 feed → 部署」

用法：
    export AINFORMER_BASE_URL=https://your-site.pages.dev
    uv run python bin/publish.py          # 全跑，最后部署到 Cloudflare Pages
    uv run python bin/publish.py --no-deploy   # 只重建 out/，不部署
    uv run python bin/publish.py --no-triage   # 跳过 Jev 判断层
    uv run python bin/publish.py --limit 60    # 这次只发 60 条

设计说明：
    - 每步失败立刻停，绝不用旧产物顶替。半成品宁可不上线。
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
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
    ap = argparse.ArgumentParser(description="抓取 → 建站 → feed → 部署")
    ap.add_argument("--no-deploy", action="store_true", help="只重建 out/，不部署")
    ap.add_argument("--no-triage", action="store_true", help="跳过 Jev 判断层")
    ap.add_argument("--limit", type=int, default=100, help="feed 最多多少条")
    ap.add_argument("--per-source", type=int, default=10, help="单源配额")
    ap.add_argument("--base-url", default=None,
                    help=f"站点根地址，默认取 {BASE_URL_ENV}")
    ap.add_argument("--project", default=None,
                    help="Cloudflare Pages 项目名，默认由 wrangler.toml 的 name 决定")
    args = ap.parse_args()

    # 地址先解析：feed 的 atom:link self 依赖它，缺了就别开始跑
    base = (args.base_url or os.environ.get(BASE_URL_ENV, "")).strip().rstrip("/")
    if not base:
        print(f"缺少站点根地址。设环境变量 {BASE_URL_ENV}，或传 --base-url。", file=sys.stderr)
        return 2
    os.environ[BASE_URL_ENV] = base  # 子进程共用同一个地址

    py = sys.executable

    run("1/5 抓取源", [py, str(BIN / "fetch.py")])

    if not args.no_triage:
        run("2/5 Jev 判断", [py, str(BIN / "triage.py")])
    else:
        print("\n=== 2/5 Jev 判断（已跳过）===")

    run("3/5 生成站点", [py, str(BIN / "build_site.py")])

    run("4/5 生成 feed", [
        py, str(BIN / "build_feed.py"),
        "--limit", str(args.limit),
        "--per-source", str(args.per_source),
        "--base-url", base,
    ])

    if args.no_deploy:
        print("\n=== 5/5 部署（已跳过）===")
        print(f"产物在 {OUT}")
        return 0

    bunx = shutil.which("bunx")
    if not bunx:
        print("\n[失败] 找不到 bunx。装 bun 或改用 wrangler 手动部署。", file=sys.stderr)
        return 2

    deploy = [bunx, "wrangler@4", "pages", "deploy",
              "--branch", "main", "--commit-dirty=true"]
    if args.project:
        deploy += ["--project-name", args.project]
    run("5/5 部署到 Cloudflare Pages", deploy, cwd=ROOT)

    print(f"\n完成。站点 {base}")
    print(f"      RSS  {base}/feed.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
