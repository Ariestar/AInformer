"""运行时配置的唯一入口。

读 .env 交给 python-dotenv；这里只负责默认值和必填校验，
让脚本里不再出现散落的字面量。

优先级：命令行参数 > 进程环境 > .env > 这里的默认值。
CI 里没有 .env，同名变量由仓库的 secrets / variables 注入。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def _text(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


def _number(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"{name} 必须是整数，当前是 {raw!r}") from None


@dataclass(frozen=True)
class Settings:
    base_url: str
    site_name: str
    site_desc: str
    brand: str
    feed_limit: int
    feed_per_source: int
    user_agent: str
    typesafe_key: str
    typesafe_base: str
    jev_model: str


def load(*, require_base_url: bool = True) -> Settings:
    # override=False：进程环境优先，方便 CI 或临时 export 覆盖 .env
    load_dotenv(ENV_FILE, override=False)

    base_url = _text("AINFORMER_BASE_URL").rstrip("/")
    if require_base_url and not base_url:
        raise SystemExit(
            "缺少 AINFORMER_BASE_URL。复制 .env.example 为 .env 并填好，或在命令行传 --base-url。"
        )

    return Settings(
        base_url=base_url,
        site_name=_text("AINFORMER_SITE_NAME", "AI 情报池"),
        site_desc=_text(
            "AINFORMER_SITE_DESC",
            "由 AInformer 从多个一手源与中文源聚合而成。不做重要性筛选，只按时间排序。",
        ),
        brand=_text("AINFORMER_BRAND", "AInformer"),
        feed_limit=_number("AINFORMER_FEED_LIMIT", 100),
        feed_per_source=_number("AINFORMER_FEED_PER_SOURCE", 10),
        user_agent=_text("AINFORMER_USER_AGENT", "ainformer/1.0"),
        typesafe_key=_text("TYPESAFE_API_KEY"),
        typesafe_base=_text("TYPESAFE_BASE_URL", "https://api.typesafe.ai").rstrip("/"),
        jev_model=_text("JEV_MODEL", "jev-latest"),
    )
