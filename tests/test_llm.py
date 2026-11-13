import pytest

from llm import _parse_json


class TestParseJson:
    def test_plain_object(self):
        assert _parse_json('{"e1": "product"}') == {"e1": "product"}

    def test_fenced_array(self):
        text = '```json\n[{"pair_id": "p1", "same_event": true}]\n```'
        assert _parse_json(text) == [{"pair_id": "p1", "same_event": True}]

    def test_preamble_and_trailing_text(self):
        text = '结果如下：{"e1": "research"}。以上。'
        assert _parse_json(text) == {"e1": "research"}

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="没有返回 JSON"):
            _parse_json("not json at all")
