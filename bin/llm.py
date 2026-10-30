#!/usr/bin/env python3
"""llm.py —— OpenAI 兼容的对话客户端，零运行时依赖，用 urllib 直连。

默认端点 DeepSeek（https://api.deepseek.com），换 OpenAI / OpenRouter 只改
LLM_BASE_URL 和 LLM_MODEL 两个环境变量，代码不动。

和 triage.py 一样：没有 key 就拒绝运行（由调用方决定是否降级），
不在这一层吞掉错误或偷偷换实现。429 / 529 才退避重试。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

RETRY_CODES = {429, 529}
MAX_ATTEMPTS = 3
TIMEOUT = 60


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
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    delay = 1.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ainformer/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            if exc.code in RETRY_CODES and attempt < MAX_ATTEMPTS:
                print(
                    f"    HTTP {exc.code}，{delay:.0f}s 后重试（{attempt}/{MAX_ATTEMPTS}）",
                    flush=True,
                )
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("重试耗尽")


def chat_json(messages: list[dict], **kwargs) -> dict:
    """要求模型只输出 JSON，返回解析后的对象。解析失败抛 ValueError。"""
    text = chat(messages, **kwargs).strip()
    # 模型偶尔会包一层 ```json ... ```，剥掉再解析
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)
