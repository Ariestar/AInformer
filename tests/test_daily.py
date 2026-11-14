from daily import apply_mapping, latest_day, select_today


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
        assert apply_mapping([c], {"e1": "bogus"}) == {"e1": "other"}

    def test_falls_back_on_missing_key(self):
        c = cluster("2026-10-29", title="某公司融资")
        assert apply_mapping([c], {}) == {"e1": "other"}
