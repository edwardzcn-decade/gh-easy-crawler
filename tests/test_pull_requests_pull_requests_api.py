#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for pull request REST APIs.
These follow the structure used in issue comment tests so the suite stays consistent.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

import pytest

from core.exceptions import NotFoundError, GitHubHTTPError, UnprocessableEntity
from core.api import GitHubRESTCrawler
from core.config import (
    GITHUB_REPO_NAME_TEST,
    GITHUB_REPO_OWNER_TEST,
    OUTPUT_DIR_TEST,
    get_github_token_test,
)

# For create pr only
# The name of the branch where your changes are implemented.
TEST_PULL_REQUEST_HEAD = "v0.4.1"
# The name of the branch where your changes are pulled into. e.g. main/master
TEST_PULL_REQUEST_BASE = "main"


def _cleanup_output_artifacts():
    """Remove stale JSON files related to pull request tests."""
    output_path = Path(OUTPUT_DIR_TEST)
    output_path.mkdir(parents=True, exist_ok=True)
    patterns = [
        "pull_*_created.json",
        "pull_*_updated.json",
        "pull_*_files_page_*.json",
        "pull_*_commits_page_*.json",
        "pull_*.json",
        "repo_pulls.json",
    ]
    for pattern in patterns:
        for path in output_path.glob(pattern):
            try:
                path.unlink()
            except FileNotFoundError:
                continue


@pytest.fixture(scope="module")
def crawler() -> GitHubRESTCrawler:
    token = get_github_token_test()
    if not token:
        pytest.skip("GITHUB_TOKEN is required to run GitHub API tests.")
    return GitHubRESTCrawler(
        "edwardzcn-decade",
        "gh-easy-crawler",
        token,
        OUTPUT_DIR_TEST,
    )


@pytest.fixture(scope="module", autouse=True)
def prepare_environment():
    """Prepare local environment before running module tests."""
    print("🧩 Preparing local test environment...")
    _cleanup_output_artifacts()
    yield
    print("✅ Finished module tests, environment teardown complete.")


@pytest.fixture(scope="module")
def sample_pulls(crawler: GitHubRESTCrawler) -> list[dict]:
    pulls = crawler.list_repo_pulls(state="all", per_page=50, page=1)
    if pulls == []:
        pytest.skip("Test repository has no pull requests to inspect.")
    return pulls


@pytest.fixture(scope="module")
def first_sample_pull(sample_pulls: list[dict]) -> dict:
    return sample_pulls[0]


@pytest.fixture(scope="module")
def merged_special_pull(sample_pulls: list[dict]) -> dict:
    return sample_pulls[-13]


@pytest.fixture(scope="module")
def closed_special_pull(sample_pulls: list[dict]) -> dict:
    return sample_pulls[-12]


def test_list_repo_pulls_creates_output(crawler: GitHubRESTCrawler):
    test_filename = "repo_pulls.json"
    output_path = Path(OUTPUT_DIR_TEST) / test_filename
    if output_path.exists():
        output_path.unlink()

    pulls = crawler.list_repo_pulls(
        state="all", per_page=30, page=1, output_filename=test_filename
    )

    assert isinstance(pulls, list)
    assert output_path.exists()


def test_get_pull_matches_listing(crawler: GitHubRESTCrawler, first_sample_pull: dict):
    pull_number = first_sample_pull["number"]
    output_path = Path(OUTPUT_DIR_TEST) / f"pull_{pull_number}.json"
    if output_path.exists():
        output_path.unlink()

    fetched = crawler.get_pull(pull_number)

    assert fetched["number"] == pull_number
    assert fetched["title"] == first_sample_pull["title"]
    assert output_path.exists()


def test_list_pull_commits_and_files(
    crawler: GitHubRESTCrawler, merged_special_pull: dict
):
    pull_number = merged_special_pull["number"]
    commits_path = Path(OUTPUT_DIR_TEST) / f"pull_{pull_number}_commits_page_1.json"
    files_path = Path(OUTPUT_DIR_TEST) / f"pull_{pull_number}_files_page_1.json"
    for candidate in (commits_path, files_path):
        if candidate.exists():
            candidate.unlink()

    commits = crawler.list_pull_commits(pull_number, per_page=30, page=1)
    files = crawler.list_pull_files(pull_number, per_page=30, page=1)

    assert isinstance(commits, list)
    assert isinstance(files, list)
    assert commits_path.exists()
    assert files_path.exists()


def test_is_pull_merged(crawler: GitHubRESTCrawler, merged_special_pull: dict):
    pull_number = merged_special_pull["number"]
    merged_flag = bool(merged_special_pull.get("merged_at"))
    if merged_flag:
        # Double check use another API
        assert crawler.is_pull_merged(pull_number) is True
    else:
        print("⚠️ TEST WARNING: merged_special_pull's merged_flag is False!")
        # Double check use another API
        try:
            assert crawler.is_pull_merged(pull_number) is True
        except NotFoundError as err:
            # Unmerged pr should get status code 404
            assert err.code == 404
            assert False


def test_is_pull_not_merged(crawler: GitHubRESTCrawler, closed_special_pull: dict):
    pull_number = closed_special_pull["number"]
    merged_flag = bool(closed_special_pull.get("merged_at"))
    if merged_flag:
        print("⚠️ TEST WARNING: closed_special_pull's merged_flag is True.")
        # Double check use another API
        try:
            assert crawler.is_pull_merged(pull_number) is False
        except NotFoundError as err:
            assert err.code == 404
            assert True
    else:
        # Double check use another API
        # /merge endpoint API will return 404 if pull request has not been merged
        # and trigger HTTPError
        with pytest.raises(NotFoundError):
            crawler.is_pull_merged(pull_number)


@pytest.fixture
def pull_creation_inputs():
    if not TEST_PULL_REQUEST_HEAD or not TEST_PULL_REQUEST_BASE:
        pytest.skip(
            "Set TEST_PULL_REQUEST_HEAD and TEST_PULL_REQUEST_BASE to run creation tests."
        )
    return TEST_PULL_REQUEST_HEAD, TEST_PULL_REQUEST_BASE


def test_create_update_close_pull_request(
    crawler: GitHubRESTCrawler, pull_creation_inputs
):
    head, base = pull_creation_inputs

    title_time = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title_prefix = "[UT][REST]"
    title_postfix = f"{title_time}"
    title = f"{title_prefix} Automated create and close pull request {title_postfix}"
    body = "Automated test pull request generated by test suite."
    try:
        created = crawler.create_pull(
            title=title,
            head=head,
            head_repo="",
            base=base,
            body=body,
            draft=False,
            # Github ignores the `maintainer_can_modify` in the same repository
            # maintainer_can_modify=True,
        )
    except GitHubHTTPError as err:
        if isinstance(err, UnprocessableEntity):
            assert "A pull request already exists for" in err.text
            pytest.skip("An open pull request exists with the same head branch")
        else:
            raise
    pull_number = created["number"]
    created_output = Path(OUTPUT_DIR_TEST) / f"pull_{created['number']}_created.json"
    assert created["title"] == title
    assert created_output.exists()

    updated_title = f"{title} :: updated"
    updated_body = f"{body}\n\nUpdated by automated test."
    crawler.update_pull(
        pull_number,
        state="closed",
        title=updated_title,
        body=updated_body,
        # maintainer_can_modify=False
    )
    updated_output = Path(OUTPUT_DIR_TEST) / f"pull_{pull_number}_updated.json"
    assert updated_output.exists()

    readed = crawler.get_pull(pull_number=pull_number)
    assert readed["title"] == updated_title
    assert readed["state"] == "closed"
