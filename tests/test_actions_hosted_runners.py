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
    monkeypatch.setattr(crawler, "_post_request", make_stub("POST", status_code=201))
    monkeypatch.setattr(crawler, "_patch_request", make_stub("PATCH"))
    monkeypatch.setattr(crawler, "_put_request", make_stub("PUT"))
    monkeypatch.setattr(crawler, "_delete_request", make_stub("DELETE", status_code=204))
    return crawler


def test_list_org_hosted_runners_builds_query(crawler, call_log):
    data = crawler.list_org_hosted_runners(org="acme", per_page=10, page=2)
    last = call_log[-1]
    assert last["method"] == "GET"
    assert last["url"] == "/orgs/acme/actions/hosted-runners"
    assert last["params"] == {"per_page": 10, "page": 2}
    assert data["method"] == "GET"


def test_create_org_hosted_runner_payload(crawler, call_log):
    crawler.create_org_hosted_runner(
        name="runner-1",
        image={"id": "ubuntu-latest", "source": "github"},
        size="4-core",
        runner_group_id=7,
        maximum_runners=5,
        enable_static_ip=True,
        image_gen=True,
    )
    last = call_log[-1]
    assert last["method"] == "POST"
    assert last["url"] == "/orgs/owner/actions/hosted-runners"
    assert last["payload"]["name"] == "runner-1"
    assert last["payload"]["image"]["id"] == "ubuntu-latest"
    assert last["payload"]["size"] == "4-core"
    assert last["payload"]["runner_group_id"] == 7
    assert last["payload"]["maximum_runners"] == 5
    assert last["payload"]["enable_static_ip"] is True
    assert last["payload"]["image_gen"] is True


def test_get_org_hosted_runner_uses_path(crawler, call_log):
    crawler.get_org_hosted_runner(42, org="acme")
    last = call_log[-1]
    assert last["method"] == "GET"
    assert last["url"] == "/orgs/acme/actions/hosted-runners/42"


def test_update_org_hosted_runner_requires_field(crawler):
    with pytest.raises(ValueError):
        crawler.update_org_hosted_runner(9)


def test_update_org_hosted_runner_payload(crawler, call_log):
    crawler.update_org_hosted_runner(
        9, name="updated", maximum_runners=3, enable_static_ip=False
    )
    last = call_log[-1]
    assert last["method"] == "PATCH"
    assert last["url"] == "/orgs/owner/actions/hosted-runners/9"
    assert last["payload"] == {
        "name": "updated",
        "maximum_runners": 3,
        "enable_static_ip": False,
    }


def test_delete_org_hosted_runner_returns_success(crawler, call_log):
    assert crawler.delete_org_hosted_runner(11, org="acme") is True
    last = call_log[-1]
    assert last["method"] == "DELETE"
    assert last["url"] == "/orgs/acme/actions/hosted-runners/11"


@pytest.mark.parametrize(
    "invocation, expected_url",
    [
        (
            lambda c: c.list_org_hosted_runner_platforms(org="acme"),
            "/orgs/acme/actions/hosted-runners/platforms",
        ),
        (
            lambda c: c.list_org_hosted_runner_machine_sizes(org="acme"),
            "/orgs/acme/actions/hosted-runners/machine-sizes",
        ),
        (
            lambda c: c.list_org_hosted_runner_limits(org="acme"),
            "/orgs/acme/actions/hosted-runners/limits",
        ),
        (
            lambda c: c.list_org_hosted_runner_custom_images(org="acme"),
            "/orgs/acme/actions/hosted-runners/images/custom",
        ),
        (
            lambda c: c.get_org_hosted_runner_custom_image("img-1", org="acme"),
            "/orgs/acme/actions/hosted-runners/images/custom/img-1",
        ),
        (
            lambda c: c.list_org_hosted_runner_custom_image_versions("img-1", org="acme"),
            "/orgs/acme/actions/hosted-runners/images/custom/img-1/versions",
        ),
        (
            lambda c: c.get_org_hosted_runner_custom_image_version("img-1", "v1", org="acme"),
            "/orgs/acme/actions/hosted-runners/images/custom/img-1/versions/v1",
        ),
        (
            lambda c: c.list_org_hosted_runner_github_owned_images(org="acme"),
            "/orgs/acme/actions/hosted-runners/images/github-owned",
        ),
        (
            lambda c: c.list_org_hosted_runner_partner_images(org="acme"),
            "/orgs/acme/actions/hosted-runners/images/partner",
        ),
    ],
)
def test_hosted_runner_simple_get_endpoints(crawler, call_log, invocation, expected_url):
    invocation(crawler)
    last = call_log[-1]
    assert last["method"] == "GET"
    assert last["url"] == expected_url


def test_delete_custom_image_and_version(crawler, call_log):
    assert crawler.delete_org_hosted_runner_custom_image("img-2", org="acme")
    first = call_log[-1]
    assert first["method"] == "DELETE"
    assert first["url"] == "/orgs/acme/actions/hosted-runners/images/custom/img-2"

    assert crawler.delete_org_hosted_runner_custom_image_version("img-3", "v2", org="acme")
    second = call_log[-1]
    assert second["method"] == "DELETE"
    assert second["url"] == "/orgs/acme/actions/hosted-runners/images/custom/img-3/versions/v2"
