#!/usr/bin/env python3
"""把抓取产物导出成前端契约。

职责边界：只做校验和裁剪，不抓取、不判断、不渲染。

数据流：
    data/items.json（抓取层原始产物）
        -> 按 schema/pool.schema.json 校验
        -> web/public/data/items.json（前端消费的精简数据）

schema 是唯一契约。字段少了、类型错了，这里当场报错退出，
而不是让浏览器在运行时拿到 undefined 再静默崩掉。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "data" / "items.json"
SCHEMA_PATH = ROOT / "schema" / "pool.schema.json"
OUT_PATH = ROOT / "web" / "public" / "data" / "items.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# ---------------------------------------------------------------- 校验
# 只实现本项目 schema 用到的关键字。多一个不支持的关键字就报错，
# 避免 schema 里写了校验器看不懂的约束、却以为已经生效。
SUPPORTED = {
    "type", "required", "properties", "items", "enum", "minLength",
    "minimum", "maximum", "format", "additionalProperties", "$ref", "$defs",
    "$schema", "$id", "title", "description",
}

TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    expected = TYPE_MAP.get(name)
    return expected is not None and isinstance(value, expected)


def _resolve(node: dict, root: dict) -> dict:
    ref = node.get("$ref")
    if not ref:
        return node
    if not ref.startswith("#/"):
        raise ValueError(f"不支持外部引用：{ref}")
    target = root
    for part in ref[2:].split("/"):
        target = target[part]
    return target


def validate(value, schema: dict, root: dict, path: str = "$") -> list[str]:
    """返回错误列表。空列表代表通过。"""
    schema = _resolve(schema, root)
    errors: list[str] = []

    unknown = set(schema) - SUPPORTED
    if unknown:
        errors.append(f"{path}: schema 使用了未实现的校验关键字 {sorted(unknown)}")
        return errors

    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(value, n) for n in names):
            return [f"{path}: 期望 {'/'.join(names)}，实际 {type(value).__name__}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: 值 {value!r} 不在枚举 {schema['enum']} 中")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: 长度 {len(value)} 小于 {schema['minLength']}")
        if schema.get("format") == "date-time" and not DATE_TIME.match(value):
            errors.append(f"{path}: {value!r} 不是 ISO 8601 时间")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} 小于 {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} 大于 {schema['maximum']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: 缺少必填字段 {key}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}: 出现契约外字段 {key}")
        for key, sub in props.items():
            if key in value:
                errors.extend(validate(value[key], sub, root, f"{path}.{key}"))

    if isinstance(value, list) and "items" in schema:
        for i, entry in enumerate(value):
            errors.extend(validate(entry, schema["items"], root, f"{path}[{i}]"))

    return errors


# ---------------------------------------------------------------- 转换
def item_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def cluster_id(title: str) -> str:
    """同一事件的不同报道通常标题措辞不同，这里只合并标题指纹完全一致的情况。

    宁可少合并，也不把两件事塞进一个簇 —— 合并错了比不合并更糟。
    """
    fingerprint = re.sub(r"[\s\W_]+", "", title.lower())[:40]
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:8]


def to_export(raw: dict) -> dict:
    items = []
    for it in raw["items"]:
        items.append({
            "id": item_id(it["url"]),
            "source_id": it["source_id"],
            "source_name": it["source_name"],
            "tier": it.get("tier", "media"),
            "title": it["title"],
            "url": it["url"],
            "published": it.get("published"),
            "summary": it.get("summary", ""),
            "cluster_id": cluster_id(it["title"]),
            "weight": float(it.get("weight", 0.5)),
        })

    return {
        "generated_at": raw["generated_at"],
        "window_days": raw["window_days"],
        "stats": raw["stats"],
        "items": items,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="校验并导出前端数据契约")
    ap.add_argument("--in", dest="src", default=str(ITEMS_PATH))
    ap.add_argument("--out", dest="dst", default=str(OUT_PATH))
    ap.add_argument("--schema", default=str(SCHEMA_PATH))
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"找不到 {src}，先跑 bin/fetch.py", file=sys.stderr)
        return 1

    raw = json.loads(src.read_text(encoding="utf-8"))
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))

    payload = to_export(raw)
    errors = validate(payload, schema, schema)
    if errors:
        print(f"契约校验失败，共 {len(errors)} 处：", file=sys.stderr)
        for e in errors[:20]:
            print(f"  - {e}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... 另有 {len(errors) - 20} 处", file=sys.stderr)
        print("未写入任何文件。", file=sys.stderr)
        return 2

    dst = Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    clusters = len({i["cluster_id"] for i in payload["items"]})
    tiers: dict[str, int] = {}
    for it in payload["items"]:
        tiers[it["tier"]] = tiers.get(it["tier"], 0) + 1

    print(f"契约校验通过：{len(payload['items'])} 条 / {clusters} 个事件簇")
    print("  层级 " + "、".join(f"{k} {v}" for k, v in sorted(tiers.items())))
    print(f"写入 {dst.relative_to(ROOT)}（{dst.stat().st_size / 1024:.0f} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
