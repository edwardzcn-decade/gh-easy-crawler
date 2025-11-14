#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for GitHub issue comment CURD APIs (REST API implementation).
Tests are split into phases (Clean up, Create, Read/Update, Delete)
and share state through pytest fixtures.
"""

import os
import time
import pytest
from pathlib import Path
from uuid import uuid4

from core.api import GitHubRESTCrawler
from core.config import (
    GITHUB_REPO_NAME_TEST,
    GITHUB_REPO_OWNER_TEST,
    OUTPUT_DIR_TEST,
    get_github_token_test,
)

# Use a deterministic prefix so old test artifacts can be identified reliably.
TEST_COMMENT_PREFIX = "[UT][issue-comments]"
TEST_ISSUE_NUMBER = int(os.getenv("GITHUB_TEST_ISSUE_NUMBER", "1"))


# -------------------------------------------------------------
# Environment setup and Clean up
# -------------------------------------------------------------
def _cleanup_output_artifacts():
    """Remove stale JSON files related to issue comment tests."""
    output_path = Path(OUTPUT_DIR_TEST)
    output_path.mkdir(parents=True, exist_ok=True)
    patterns = [
        "issue_comment_*",
        "issue_*_comments_page_*",
        "repo_issues.json",
        "repo_issue_comments_*",
    ]
    for pattern in patterns:
        for path in output_path.glob(pattern):
            try:
                path.unlink()
            except FileNotFoundError:
                continue


# -------------------------------------------------------------
# Shared fixtures
# -------------------------------------------------------------
@pytest.fixture(scope="module")
def crawler() -> GitHubRESTCrawler:
    token = get_github_token_test()
    if not token:
        pytest.skip("GITHUB_TOKEN is required to run GitHub API tests.")
    return GitHubRESTCrawler(
        GITHUB_REPO_OWNER_TEST,
        GITHUB_REPO_NAME_TEST,
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


# -------------------------------------------------------------
# Cleanup test
# -------------------------------------------------------------
def test_cleanup_old_test_comments(crawler: GitHubRESTCrawler):
    """
    Clean up old test comments from the test issue
    """
    scanned_count = 0
    deleted_count = 0
    existing_comments = crawler.list_issue_comments(
        TEST_ISSUE_NUMBER, per_page=100, page=1
    )
    for comment in existing_comments:
        scanned_count += 1
        comment_body = comment.get("body", "UNKNOW BODY")
        if comment_body.startswith(TEST_COMMENT_PREFIX):
            if_delete = crawler.delete_single_issue_comment(comment["id"])
            if if_delete:
                deleted_count += 1
            else:
                print(f"⚠️ Fail to clean comment: {comment_body}")
            time.sleep(0.1)
    print(f"🧹 Deleted {deleted_count} stale test comments for cleanup.")
    # Assertion ensure all old test comments are fetched within one page (per_page=100)
    # and at least one test comment is deleted. For the first run, relax to >= 0.
    assert scanned_count < 100 and deleted_count >= 1


# -------------------------------------------------------------
# GET comment list tests
# -------------------------------------------------------------
def test_list_comments(crawler: GitHubRESTCrawler):
    """
    Verify list_repo_issue_comments and list_issue_comments are valid.
    """
    # Initial list calls validate list endpoints succeed.
    repo_comments_initial = crawler.list_repo_issue_comments(per_page=30, page=1)
    assert isinstance(repo_comments_initial, list)

    issue_comments_initial = crawler.list_issue_comments(
        TEST_ISSUE_NUMBER, per_page=100, page=1
    )
    assert isinstance(issue_comments_initial, list)


# -------------------------------------------------------------
# Individual CURD tests
# -------------------------------------------------------------
def test_issue_comment_crud_flow(crawler: GitHubRESTCrawler):
    # Create two comments but only plan to delete one to satisfy manual inspection requirement.
    keep_body = f"{TEST_COMMENT_PREFIX} keep {uuid4().hex}"
    keep_comment = crawler.create_single_issue_comment(TEST_ISSUE_NUMBER, keep_body)
    keep_id = keep_comment["id"]
    assert keep_comment["body"] == keep_body

    delete_body = f"{TEST_COMMENT_PREFIX} delete {uuid4().hex}"
    delete_comment = crawler.create_single_issue_comment(TEST_ISSUE_NUMBER, delete_body)
    delete_id = delete_comment["id"]
    assert delete_comment["body"] == delete_body

    # Fetch and update the comment that will be kept.
    fetched_keep = crawler.get_single_issue_comment(keep_id)
    assert fetched_keep["body"] == keep_body

    updated_body = f"{keep_body} :: updated"
    updated_keep = crawler.update_single_issue_comment(keep_id, updated_body)
    assert updated_keep["body"] == updated_body

    # Confirm the update persisted.
    refetched_keep = crawler.get_single_issue_comment(keep_id)
    assert refetched_keep["body"] == updated_body

    # Delete the second comment and ensure it no longer appears in listings.
    if_delete = crawler.delete_single_issue_comment(delete_id)
    assert if_delete

    time.sleep(0.2)

    issue_comments_after = crawler.list_issue_comments(
        TEST_ISSUE_NUMBER, per_page=100, page=1
    )
    issue_comment_ids = {comment["id"] for comment in issue_comments_after}
    assert keep_id in issue_comment_ids
    assert delete_id not in issue_comment_ids

    repo_comments_after = crawler.list_repo_issue_comments(per_page=100, page=1)
    repo_comment_ids = {comment["id"] for comment in repo_comments_after}
    assert keep_id in repo_comment_ids
    assert delete_id not in repo_comment_ids
