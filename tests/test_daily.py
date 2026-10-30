from daily import apply_mapping, classify, latest_day, select_today


def cluster(day, title="无标题", size=1, primary="p1"):
    return {
        "event_id": "e1",
        "primary": primary,
        "size": size,
        "members": [
            {
                "id": "m1",
                "url": "https://a.com/1",
                "source": "s",
                "tier": "media",
                "published": f"{day}T00:00:00+00:00",
                "title": title,
            }
        ],
    }


class TestClassify:
    def test_product_by_launch_word(self):
        assert classify("OpenAI 发布 GPT-6") == "product"

    def test_english_model_release_is_product(self):
        assert classify("Gemini 4 Carbon: Our next frontier model") == "product"

    def test_research_by_paper(self):
        assert classify("一篇论文提出新的训练方法") == "research"

    def test_business_by_funding(self):
        assert classify("某公司完成 1 亿美元融资") == "business"

    def test_policy_by_regulation(self):
        assert classify("欧盟通过新的监管法案") == "policy"

    def test_fallback_to_other(self):
        assert classify("一家公司换了个 logo") == "other"


class TestSelectToday:
    def test_picks_only_the_given_day(self):
        clusters = [cluster("2026-10-28"), cluster("2026-10-29"), cluster("2026-10-29")]
        assert len(select_today(clusters, "2026-10-29")) == 2

    def test_latest_day_ignores_undated(self):
        clusters = [
            cluster("2026-10-27"),
            cluster("2026-10-29"),
        ]
        # 加一条无日期的成员事件，不应影响 latest_day
        undated = cluster("2026-10-29")
        undated["members"][0]["published"] = None
        clusters.append(undated)
        assert latest_day(clusters) == "2026-10-29"


class TestApplyMapping:
    def test_uses_valid_model_result(self):
        c = cluster("2026-10-29", title="某公司融资")
        assert apply_mapping([c], {"e1": "business"}) == {"e1": "business"}

    def test_falls_back_on_invalid_category(self):
        c = cluster("2026-10-29", title="某公司融资")
        # 模型给了非法类别，应落到启发式（标题含「融资」→ business）
        assert apply_mapping([c], {"e1": "bogus"}) == {"e1": "business"}

    def test_falls_back_on_missing_key(self):
        c = cluster("2026-10-29", title="某公司融资")
        assert apply_mapping([c], {}) == {"e1": "business"}
