#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import pytest

from core.api import GitHubRESTCrawler
from core.config import (
    GITHUB_REPO_NAME_TEST,
    GITHUB_REPO_OWNER_TEST,
    OUTPUT_DIR_TEST,
    get_github_token_test,
)
from core.exceptions import (
    AuthenticationFailed,
    ForbiddenError,
    GitHubHTTPError,
    TransportError,
)

# Opt-in flag for profile mutation tests to avoid accidental profile changes.
ENABLE_USER_MUTATION = os.getenv("ENABLE_USER_MUTATION_TESTS", "") == "1"


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


def _call_or_skip(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AuthenticationFailed:
        pytest.skip("Authentication required or token invalid.")
    except ForbiddenError:
        pytest.skip("Insufficient permissions for user endpoints.")
    except GitHubHTTPError as exc:
        pytest.skip(f"GitHub API error: {exc}")
    except TransportError as exc:
        pytest.skip(f"Transport error: {exc}")


def test_get_authenticated_user(crawler: GitHubRESTCrawler):
    data = _call_or_skip(crawler.get_authenticated_user)
    assert isinstance(data, dict)
    assert data.get("login")
    assert data.get("id")


def test_get_user_by_userid_and_username(crawler: GitHubRESTCrawler):
    auth = _call_or_skip(crawler.get_authenticated_user)
    user_id = auth.get("id")
    username = auth.get("login")
    assert user_id and username

    me_by_id = _call_or_skip(crawler.get_user_with_userid, user_id)
    assert isinstance(me_by_id, dict)
    assert me_by_id.get("id") == user_id
    assert me_by_id.get("login") == username

    me_by_name = _call_or_skip(crawler.get_user_with_username, username)
    assert isinstance(me_by_name, dict)
    assert me_by_name.get("id") == user_id
    assert me_by_name.get("login") == username

    ghost_name = "ghost"
    ghost_by_name = _call_or_skip(crawler.get_user_with_username, ghost_name)
    assert isinstance(ghost_by_name, dict)
    assert ghost_by_name.get("login") == ghost_name
    assert ghost_by_name.get("id") == 10137


def test_list_users(crawler: GitHubRESTCrawler):
    users = _call_or_skip(crawler.list_users, since=None, per_page=5)
    assert isinstance(users, list)
    assert len(users) <= 5
    if users:
        assert "login" in users[0]
        assert users[0]["login"] == "mojombo"


@pytest.mark.skipif(
    not ENABLE_USER_MUTATION,
    reason="User profile mutation disabled (set ENABLE_USER_MUTATION_TESTS=1 to enable).",
)
def test_update_authenticated_user_noop(crawler: GitHubRESTCrawler):
    """
    Exercise the update endpoint with an empty payload to ensure the call path works.
    The API treats an empty body as a no-op but still requires proper scopes.
    """
    updated = _call_or_skip(
        crawler.update_authenticated_user,
        name=None,
        email=None,
        blog=None,
        twitter_username=None,
        company=None,
        location=None,
        hireable=None,
        bio=None,
    )
    assert isinstance(updated, dict)
    assert updated.get("login")
