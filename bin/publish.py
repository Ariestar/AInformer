#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish.py —— 一条命令跑完「抓取 → 建站 → 生成 feed → 部署」

用法：
    python bin/publish.py                 # 全跑，最后部署到 Cloudflare Pages
    python bin/publish.py --no-deploy     # 只重建 out/，不部署
    python bin/publish.py --no-triage     # 跳过 Jev 判断层
    python bin/publish.py --limit 60      # 这次只发 60 条

设计说明：
    - 每步失败立刻停，绝不用旧产物顶替。半成品宁可不上线。
    - 部署走 bunx（不依赖 npm / 全局安装）。
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
    ap.add_argument("--project", default="ai-intel", help="Cloudflare Pages 项目名")
    args = ap.parse_args()

    py = sys.executable

    run("1/4 抓取源", [py, str(BIN / "fetch.py")])

    if not args.no_triage:
        run("2/4 Jev 判断", [py, str(BIN / "triage.py")])
    else:
        print("\n=== 2/4 Jev 判断（已跳过）===")

    run("3/4 生成站点与 feed", [
        py, str(BIN / "build_site.py"),
    ])
    run("3b/4 生成 feed", [
        py, str(BIN / "build_feed.py"),
        "--limit", str(args.limit),
        "--per-source", str(args.per_source),
    ])

    if args.no_deploy:
        print("\n=== 4/4 部署（已跳过）===")
        print(f"产物在 {OUT}")
        return 0

    bunx = shutil.which("bunx")
    if not bunx:
        print("\n[失败] 找不到 bunx。装 bun 或改用 wrangler 手动部署。", file=sys.stderr)
        return 2

    run("4/4 部署到 Cloudflare Pages", [
        bunx, "wrangler@4", "pages", "deploy",
        "--branch", "main",
        "--commit-dirty=true",
    ], cwd=ROOT)

    base = os.environ.get("AI_INTEL_BASE_URL", "https://ai-intel.pages.dev").rstrip("/")
    print(f"\n完成。站点 {base}")
    print(f"      RSS  {base}/feed.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
