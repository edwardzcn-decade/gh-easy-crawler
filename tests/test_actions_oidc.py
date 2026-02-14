#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest

from core.api import GitHubRESTCrawler


class DummyResponse:
    def __init__(self, payload: dict | None = None, status_code: int = 200):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = str(self._payload)
        self.content = b""

    def json(self):
        return self._payload


@pytest.fixture
def call_log():
    return []


@pytest.fixture
def crawler(tmp_path, call_log, monkeypatch) -> GitHubRESTCrawler:
    crawler = GitHubRESTCrawler("owner", "repo", token=None, output_dir=tmp_path)
    monkeypatch.setattr(crawler, "_persist", lambda *_, **__: None)

    def make_stub(method: str, status_code: int = 200):
        def _stub(
            url,
            headers=None,
            params=None,
            payload=None,
            data=None,
            timeout=None,
            **kwargs,
        ):
            call_log.append(
                {
                    "method": method,
                    "url": url,
                    "params": params,
                    "payload": payload,
                    "data": data,
                }
            )
            body = {
                "method": method,
                "url": url,
                "params": params,
                "payload": payload,
            }
            return DummyResponse(body, status_code=status_code)

        return _stub

    monkeypatch.setattr(crawler, "_get_request", make_stub("GET"))
    monkeypatch.setattr(crawler, "_put_request", make_stub("PUT"))
    return crawler


def test_org_oidc_get_and_set(crawler, call_log):
    crawler.get_org_oidc_customization_sub(org="acme")
    last = call_log[-1]
    assert last["method"] == "GET"
    assert last["url"] == "/orgs/acme/actions/oidc/customization/sub"

    with pytest.raises(ValueError):
        crawler.set_org_oidc_customization_sub(use_default=False, org="acme")

    crawler.set_org_oidc_customization_sub(use_default=True, org="acme")
    last = call_log[-1]
    assert last["method"] == "PUT"
    assert last["payload"] == {"use_default": True}
    assert last["url"] == "/orgs/acme/actions/oidc/customization/sub"

    crawler.set_org_oidc_customization_sub(
        use_default=False, subject_claim_template="repo/{repo}", org="acme"
    )
    last = call_log[-1]
    assert last["payload"] == {
        "use_default": False,
        "subject_claim_template": "repo/{repo}",
    }


def test_repo_oidc_get_and_set(crawler, call_log):
    crawler.get_repo_oidc_customization_sub()
    last = call_log[-1]
    assert last["method"] == "GET"
    assert last["url"] == "/repos/owner/repo/actions/oidc/customization/sub"

    crawler.set_repo_oidc_customization_sub(use_default=True)
    last = call_log[-1]
    assert last["method"] == "PUT"
    assert last["payload"] == {"use_default": True}
    assert last["url"] == "/repos/owner/repo/actions/oidc/customization/sub"

    crawler.set_repo_oidc_customization_sub(
        use_default=False, subject_claim_template="repo/{repo}"
    )
    last = call_log[-1]
    assert last["payload"] == {
        "use_default": False,
        "subject_claim_template": "repo/{repo}",
    }
