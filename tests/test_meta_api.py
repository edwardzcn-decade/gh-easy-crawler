#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest

from core.api import GitHubRESTCrawler
from core.config import (
    GITHUB_REPO_NAME_TEST,
    GITHUB_REPO_OWNER_TEST,
    OUTPUT_DIR_TEST,
    get_github_token_default,
)


@pytest.fixture(scope="module")
def crawler() -> GitHubRESTCrawler:
    token = get_github_token_default()
    if not token:
        pytest.skip(
            "GITHUB_TOKEN environment variable is required to run GitHub API tests."
        )
    return GitHubRESTCrawler(
        GITHUB_REPO_OWNER_TEST, GITHUB_REPO_NAME_TEST, token, OUTPUT_DIR_TEST
    )


def test_get_zen_returns_text(crawler: GitHubRESTCrawler):
    zen_text = crawler.get_zen()
    assert isinstance(zen_text, str)
    assert zen_text != ""


def test_get_octocat_accepts_speech(crawler: GitHubRESTCrawler):
    speech = "Unit test greeting"
    octocat_text = crawler.get_octocat(speech)
    assert isinstance(octocat_text, str)
    assert speech in octocat_text


def test_get_api_root_contains_url(crawler: GitHubRESTCrawler):
    api_root = crawler.get_api_root()
    assert isinstance(api_root, dict)
    assert "current_user_url" in api_root


def test_get_github_meta_contains_key(crawler: GitHubRESTCrawler):
    meta_info = crawler.get_github_meta()
    assert isinstance(meta_info, dict)
    assert "api" in meta_info


def test_get_api_versions_not_empty(crawler: GitHubRESTCrawler):
    versions = crawler.get_api_versions()
    assert isinstance(versions, list)
    assert versions != []
