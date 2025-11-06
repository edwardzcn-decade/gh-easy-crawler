#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import textwrap

import pytest

from core.api import GitHubRESTCrawler
from core.config import (
    GITHUB_REPO_NAME_TEST,
    GITHUB_REPO_OWNER_TEST,
    OUTPUT_DIR_TEST,
    get_github_token_default,
)

MARKDOWN_SAMPLE = textwrap.dedent(
    """
    # Welcome to Markdown API Testing

    This paragraph includes *italic*, **bold**, and `inline code`.

    ## Section

    1. First numbered
    2. Second numbered

    - alpha
    - beta
    - $x^2+y^2=z^2$

    > Take time to craft delightful APIs.

    ```python
    def fo(name: str) -> str:
        return f"Hello, {name}!"
    ```

    Visit [Example](https://example.com) for more context.
    """
).strip()

EXPECTED_HTML_SNIPPETS = [
    'Welcome to Markdown API Testing</h1>',
    'Section</h2>',
    "<em>italic</em>",
    "<strong>bold</strong>",
    "<code>inline code</code>",
    "<ol>",
    "First numbered",
    "<ul>",
    "alpha",
    "beta",
    "x^2+y^2=z^2",
    "<blockquote>",
    "Take time to craft delightful APIs.",
    "highlight-source-python",
    'href="https://example.com"',
]


@pytest.fixture(scope="module")
def crawler() -> GitHubRESTCrawler:
    token = get_github_token_default()
    if not token:
        pytest.skip(
            "GITHUB_TOKEN environment variable is required to run GitHub API tests."
        )
    return GitHubRESTCrawler(
        GITHUB_REPO_OWNER_TEST,
        GITHUB_REPO_NAME_TEST,
        token,
        OUTPUT_DIR_TEST,
    )


def _assert_html_contains_expected(html: str):
    for snippet in EXPECTED_HTML_SNIPPETS:
        assert snippet in html


def test_render_markdown_creates_expected_html_file(crawler: GitHubRESTCrawler):
    filename = "test_markdown_rendered_markdown.html"
    o = crawler.output_dir / filename
    if o.exists():
        o.unlink()

    rendered_html = crawler.render_markdown(MARKDOWN_SAMPLE, output_filename=filename)

    assert isinstance(rendered_html, str)
    assert rendered_html.strip()
    _assert_html_contains_expected(rendered_html)

    assert o.exists()
    disk_html = o.read_text(encoding="utf-8")
    assert disk_html == rendered_html


def test_render_markdown_raw_honors_custom_filename(crawler: GitHubRESTCrawler):
    filename = "test_markdown_rendered_raw.html"
    o = crawler.output_dir / filename
    if o.exists():
        o.unlink()

    rendered_html = crawler.render_markdown_raw(
        MARKDOWN_SAMPLE, output_filename=filename
    )

    assert isinstance(rendered_html, str)
    assert rendered_html.strip()
    _assert_html_contains_expected(rendered_html)

    assert o.exists()
    disk_html = o.read_text(encoding="utf-8")
    assert disk_html == rendered_html
