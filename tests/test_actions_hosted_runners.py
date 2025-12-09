#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import pytest

from core.exceptions import (
    AuthenticationFailed,
    GitHubHTTPError,
    NotFoundError,
    ForbiddenError,
)
from core.api import GitHubRESTCrawler
from core.config import (
    GITHUB_REPO_OWNER_TEST,
    GITHUB_REPO_NAME_TEST,
    OUTPUT_DIR_TEST,
    get_github_token_test,
)

# Organization used for hosted-runner tests; default to test repo owner.


@pytest.fixture(scope="module")
def crawler() -> GitHubRESTCrawler:
    token = get_github_token_test()
    if not token:
        pytest.skip("GITHUB_TOKEN is required to run GitHub API tests.")
    return GitHubRESTCrawler(
        owner=GITHUB_REPO_OWNER_TEST,
        repo=GITHUB_REPO_NAME_TEST,
        token=token,
        output_dir=OUTPUT_DIR_TEST,
    )


@pytest.fixture(scope="module")
def assert_valid_token(crawler):
    try:
        crawler.get_authenticated_user()
    except AuthenticationFailed:
        print("Authentication Failed")
        raise
    except GitHubHTTPError as e:
        print(f"Other GitHubHTTPError, {e!r}")
        raise
    except Exception as e:
        print(f"Other Exceiption {e!r}")
        raise
    return True


def test_list_org_hosted_runners_smoke(
    crawler: GitHubRESTCrawler, assert_valid_token: bool
):
    with pytest.raises(ForbiddenError) as e1:
        crawler.list_org_hosted_runners(org="apache", per_page=10, page=1)
    err = e1.value
    assert err.code == 403
    assert "Resource not accessible by personal access token" in err.text
    with pytest.raises(NotFoundError) as e2:
        crawler.list_org_hosted_runners(org="test-org-not-existed")
    err = e2.value
    assert err.code == 404
    assert "Not Found" in err.text
