import json
from collections import Counter
from types import SimpleNamespace

import cluster
from cluster import cap_pairs, pair_id, recall


def make_item(url, title, published="2026-10-28T00:00:00+00:00", summary="", tier="media"):
    return {
        "url": url,
        "title": title,
        "published": published,
        "summary": summary,
        "source_id": "s",
        "source_name": "Source",
        "tier": tier,
    }


class TestRecall:
    def test_pairs_cross_language_by_shared_entity(self):
        # 中文标题和英文原文按字面几乎不重合，但共享专名 Gemini / Carbon
        items = [
            make_item("https://a.com/1", "Google DeepMind 发布 Gemini 4 Carbon 前沿模型"),
            make_item("https://a.com/2", "Gemini 4 Carbon: Our next frontier model"),
        ]
        cands, _, _ = recall(items, 48, 0.3, 3, 12, False)
        assert pair_id("https://a.com/1", "https://a.com/2") in cands

    def test_does_not_pair_unrelated_products(self):
        items = [
            make_item("https://a.com/1", "OpenAI 发布 GPT-6"),
            make_item("https://a.com/2", "字节跳动发布豆包大模型"),
        ]
        cands, _, _ = recall(items, 48, 0.3, 3, 12, False)
        assert pair_id("https://a.com/1", "https://a.com/2") not in cands

    def test_date_only_title_is_unpairable(self):
        items = [
            make_item("https://a.com/1", "2026-10-29"),
            make_item("https://a.com/2", "2026-10-28"),
        ]
        cands, _, unpairable = recall(items, 48, 0.3, 3, 12, False)
        assert len(cands) == 0
        assert len(unpairable) == 2

    def test_serial_digest_pairs_are_dropped(self):
        items = [
            make_item("https://a.com/1", "橘鸦AI早报 10-24", published="2026-10-24T00:00:00+00:00"),
            make_item("https://a.com/2", "橘鸦AI早报 10-26", published="2026-10-26T00:00:00+00:00"),
        ]
        cands, dropped, _ = recall(items, 48, 0.3, 3, 12, False)
        assert len(cands) == 0
        assert dropped == 1

    def test_keep_serial_retains_digest_pair(self):
        # 数字不同导致三元组相似度低，只有通道二靠共享专名命中
        items = [
            make_item(
                "https://a.com/1", f"Gemini 早报 {'1' * 24}", published="2026-10-24T00:00:00+00:00"
            ),
            make_item(
                "https://a.com/2", f"Gemini 早报 {'2' * 24}", published="2026-10-26T00:00:00+00:00"
            ),
        ]
        cands, dropped, _ = recall(items, 48, 0.3, 3, 12, False)
        assert len(cands) == 0
        assert dropped == 1

        kept, kept_dropped, _ = recall(items, 48, 0.3, 3, 12, True)
        assert pair_id("https://a.com/1", "https://a.com/2") in kept
        assert kept_dropped == 0


class TestJudgeFallback:
    def test_invalid_output_writes_negative_without_cache(self, tmp_path, monkeypatch):
        work = tmp_path / "work"
        (work / "inbox").mkdir(parents=True)
        rec = {"pair_id": "p1", "a": {"url": "https://a.com/1"}, "b": {"url": "https://a.com/2"}}
        (work / "inbox" / "batch-001.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
        monkeypatch.setattr(
            cluster,
            "judge_batch",
            lambda pairs, settings: (_ for _ in ()).throw(ValueError("bad json")),
        )
        monkeypatch.setattr(
            cluster.config,
            "load",
            lambda **_: SimpleNamespace(
                llm_api_key="test", llm_model="stub", llm_base_url="http://127.0.0.1"
            ),
        )

        assert cluster.cmd_judge(SimpleNamespace(work=str(work))) == 0
        decision = json.loads((work / "outbox" / "batch-001.jsonl").read_text(encoding="utf-8"))
        assert decision["same_event"] is False
        cache_files = list(work.glob("judge_cache_*.json"))
        if cache_files:
            assert "p1" not in json.loads(cache_files[0].read_text(encoding="utf-8"))


class TestCapPairs:
    def test_respects_max_degree(self):
        a = make_item("https://a.com/1", "X")
        b = make_item("https://a.com/2", "Y")
        c = make_item("https://a.com/3", "Z")
        cands = {
            pair_id("https://a.com/1", "https://a.com/2"): (0.9, a, b),
            pair_id("https://a.com/2", "https://a.com/3"): (0.8, b, c),
            pair_id("https://a.com/1", "https://a.com/3"): (0.7, a, c),
        }
        kept = cap_pairs(cands, max_degree=1, max_pairs=100)
        degree: Counter[str] = Counter()
        for _score, _pid, x, y in kept:
            degree[x["url"]] += 1
            degree[y["url"]] += 1
        assert all(v <= 1 for v in degree.values())
        assert len(kept) == 1  # 三条边，度数上限 1，只能留一条
