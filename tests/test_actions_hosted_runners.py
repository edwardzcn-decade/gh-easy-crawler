#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import pytest
from requests.exceptions import HTTPError

from core.api import GitHubRESTCrawler
from core.config import (
    GITHUB_REPO_NAME_TEST,
    GITHUB_REPO_OWNER_TEST,
    OUTPUT_DIR_TEST,
    get_github_token_test,
)

# Organization used for hosted-runner tests; default to test repo owner.

# Opt-in flag for destructive mutation tests.
ENABLE_MUTATION = os.getenv("ENABLE_HOSTED_RUNNER_MUTATION_TESTS", "") == "1"


@pytest.fixture(scope="module")
def crawler() -> GitHubRESTCrawler:
    token = get_github_token_test()
    if not token:
        pytest.skip("GITHUB_TOKEN is required to run GitHub API tests.")
    return GitHubRESTCrawler(
        GITHUB_REPO_NAME_TEST,
        token,
        OUTPUT_DIR_TEST,
    )



def test_list_org_hosted_runners_smoke(crawler: GitHubRESTCrawler):
    for org in ("apache", "tttt-notexist"):
        with pytest.raises(HTTPError) as excinfo:
            crawler.list_org_hosted_runners(org=org, per_page=10, page=1)

        resp = excinfo.value.response
        assert resp is not None
        assert resp.status_code == 401
        assert "Bad credentials" in resp.text

