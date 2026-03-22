from importlib import resources

from ainformer.extractor import extract_article_from_html


def test_extract_article_from_fixture_html() -> None:
    html = resources.files("ainformer.fixtures").joinpath("sample_article.html").read_text(encoding="utf-8")
    article = extract_article_from_html(html)

    assert article.title == "Fixture Foundation Launch"
    assert article.published_at is not None
    assert article.authors == ["Jane Doe", "John Roe"]
    assert article.excerpt == "A local fixture article used to validate HTML extraction."
    assert "The fixture adapter launches a local article pipeline" in article.content_text
    assert "<article>" in article.content_html
    assert article.content_complete is True
