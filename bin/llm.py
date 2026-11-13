#!/usr/bin/env python3
"""llm.py —— 基于 OpenAI SDK 的对话客户端，默认 DeepSeek。

LLM_BASE_URL / LLM_MODEL 换成任意 OpenAI 兼容服务即可，代码不动。
没有 key 时由调用方决定是否降级；SDK 自带 429/5xx 重试。
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

TIMEOUT = 60
MAX_RETRIES = 2


def chat(
    messages: list[dict],
    *,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.2,
    timeout: int = TIMEOUT,
) -> str:
    """发一轮对话，返回模型正文文本。失败抛异常，由调用方决定怎么办。"""
    client = OpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        max_retries=MAX_RETRIES,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def _parse_json(text: str) -> Any:
    """从模型回复里取第一段合法 JSON，兼容 ```json 围栏和前后说明文字。"""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[i:])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError(f"模型没有返回 JSON：{text[:120]!r}")


def chat_json(messages: list[dict], **kwargs) -> Any:
    """要求模型只输出 JSON，返回解析后的对象。解析失败抛 ValueError。"""
    return _parse_json(chat(messages, **kwargs).strip())
