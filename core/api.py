#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10

"""
GitHub API Crawler Implementation
Implements various common APIs for REST API and gh CLI based crawlers.
Authors: edwardzcn
"""

import requests
from pathlib import Path
from typing import Any
from .base import GitHubCrawlerBase
from .config import SupportMediaTypes


class GitHubRESTCrawler(GitHubCrawlerBase):
    """GitHub REST API implementation of GitHubCrawlerBase"""

    def __init__(
        self,
        owner: str | None,
        repo: str | None = None,
        token: str | None = None,
        output_dir: str | None = None,
    ):
        super().__init__(owner, repo, token, output_dir)
        # Build default headers
        # TODO: Make media type configurable rather than default
        self.headers = {
            "Accept": SupportMediaTypes.DEFAULT.value,
            "User-Agent": self._get_user_agent_default(),
            "X-GitHub-Api-Version": self._get_api_version(),
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    # --------------------------------------------------------
    # Abstract Method Implementation
    # --------------------------------------------------------
    def _get_request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | tuple[float, float] | None = None,
    ):
        return self._request(
            "GET", url, headers, params=params, json_payload=None, timeout=timeout
        )

    def _post_request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        payload: Any | None = None,
        timeout: float | tuple[float, float] | None = None,
    ):
        return self._request(
            "POST",
            url,
            headers,
            params=params,
            raw_data=data,
            json_payload=payload,
            timeout=timeout,
        )

    def _patch_request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        payload: Any | None = None,
        timeout: float | tuple[float, float] | None = None,
    ):
        return self._request(
            "PATCH", url, headers, params=params, json_payload=payload, timeout=timeout
        )

    def _put_request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        payload: Any | None = None,
        timeout: float | tuple[float, float] | None = None,
    ):
        return self._request(
            "PUT", url, headers, params=params, json_payload=payload, timeout=timeout
        )

    def _delete_request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | tuple[float, float] | None = None,
    ):
        return self._request("DELETE", url, headers, params=params, timeout=timeout)

    def _request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        raw_data: Any | None = None,
        json_payload: Any | None = None,
        timeout: float | tuple[float, float] | None = None,
    ):
        """
        Unified low-level HTTP request handler for REST API calls.
        :param method: HTTP method to use (e.g., 'GET', 'POST', 'PATCH', 'PUT', 'DELETE').
        :param url: Full URL or API endpoint path to send the request to.
        :param headers: Optional dictionary of HTTP headers to include in the request.
                        These headers override the default headers.
        :param params: Optional dictionary to send as a list of params in the query string.
        :param json_payload: Optional data to send in the request body as JSON.
                        This maps to the `json` argument of `requests.request`.
        :param raw_data: Optional raw data or bytes (e.g. for /markdown/raw)
                        This maps to the `data` argument of `requests.request`
        :param timeout: Optional timeout setting for the request in seconds.
                        Can be a float or a tuple (connect timeout, read timeout).
        :return: The `requests.Response` object resulting from the HTTP request.
        :raises: Raises exceptions from `requests` if the request fails or returns an HTTP error status.
        """
        # Check if it is endpoint or full URL
        if not url.startswith("http"):
            url = self._build_url(endpoint=url)
        # Merge default headers with any provided ones.
        # For Python <3.9, use: {**self.headers, **(headers or {})}
        # For Python >=3.9, the dict union operator: self.headers | (headers or {}) is available.
        # In both cases, keys from `headers` override those in `self.headers`.
        request_headers = self.headers | (headers or {})
        resp = None
        try:
            resp = requests.request(
                method.upper(),
                url=url,
                headers=request_headers,
                params=params,
                data=raw_data,
                json=json_payload,
                timeout=timeout,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ Error during {method.upper()} request → {url}")
            print(f"Reason: {e}")
            if resp is not None:
                print(f"Response Status Code: {resp.status_code}")
                print(f"Response Content: {resp.text[:200]}")
            raise
        return resp

    # --------------------------------------------------------
    # REST API Endpoints
    # --------------------------------------------------------
    # Actions
    def list_repo_artifacts(
        self, per_page: int = 30, page: int = 1, name: str | None = None
    ) -> dict[str, Any]:
        """
        Get artifacts for a repository
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#list-artifacts-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts"
        params: dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if name is not None:
            params["name"] = name
        resp = self._get_request(url, params=params)
        data = resp.json()
        self._persist(
            data,
            # TODO configurable repo owner, repo name
            filename="repo_artifacts.json",
            level="log",
        )
        return data

    def get_artifact(self, artifact_id: int) -> dict[str, Any]:
        """
        Get a single artifact by ID.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#get-an-artifact
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts/{artifact_id}"
        )
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"artifact_{artifact_id}.json",
            level="log",
            post_msg=f"Fetched artifact #{artifact_id}",
        )
        return data

    def delete_artifact(self, artifact_id: int) -> bool:
        """
        Delete an artifact by ID.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#delete-an-artifact
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts/{artifact_id}"
        )
        resp = self._delete_request(url)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "artifact_id": artifact_id,
                "status_code": resp.status_code,
                "success": success,
            },
            filename=f"artifact_{artifact_id}_deleted.json",
            level="log",
            post_msg=f"Artifact #{artifact_id} deleted (status {resp.status_code}).",
        )
        return success

    def download_artifact(
        self,
        artifact_id: int,
        archive_format: str = "zip",
        output_path: str | Path | None = None,
    ) -> Path:
        """
        Download an artifact and save it locally.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#download-an-artifact
        """
        archive_format = archive_format.lower()
        if archive_format != "zip":
            raise ValueError(
                "GitHub currently supports only the 'zip' archive format. Please set archive_format as 'zip'."
            )
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts/{artifact_id}/{archive_format}"
        resp = self._get_request(url)
        target_path = (
            Path(output_path)
            if output_path is not None
            else self.output_dir / f"artifact_download_{artifact_id}.{archive_format}"
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as artifact_file:
            artifact_file.write(resp.content)
        written_bytes = target_path.stat().st_size
        self._persist(
            {
                "artifact_id": artifact_id,
                "archive_format": archive_format,
                "output_path": str(target_path),
                "bytes": written_bytes,
            },
            filename=f"artifact_{artifact_id}_{archive_format}_download.json",
            level="log",
            post_msg=f"Artifact #{artifact_id} downloaded to {target_path} ({written_bytes} bytes).",
        )
        return target_path

    def list_action_runs_artifact(
        self, run_id: int, name: str | None = None, per_page: int = 30, page: int = 1
    ) -> dict[str, Any]:
        """
        List artifacts generated by a specific workflow run.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#list-workflow-run-artifacts
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/artifacts"
        )
        params: dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if name is not None:
            params["name"] = name
        resp = self._get_request(url, params=params)
        data = resp.json()
        artifacts_count = len(data.get("artifacts", []))
        self._persist(
            data,
            filename=f"workflow_run_{run_id}_artifacts.json",
            level="log",
            post_msg=f"Fetched {artifacts_count} artifacts for workflow run #{run_id}.",
        )
        return data

    def get_org_actions_cache_usage(self, org: str | None = None) -> dict[str, Any]:
        """
        Get cache usage for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#get-github-actions-cache-usage-for-an-organization
        """
        # default org_name is the repo_owner e.g. apache
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/cache/usage"
        resp = self._get_request(url)
        data = resp.json()
        usage_bytes = data.get("total_usage_in_bytes")
        self._persist(
            data,
            filename=f"org_{org_name}_cache_usage.json",
            level="log",
            post_msg=f"Org {org_name} cache usage: {usage_bytes} bytes.",
        )
        return data

    def list_org_actions_cache_usage_by_repo(
        self, org: str | None = None, per_page: int = 30, page: int = 1
    ) -> dict[str, Any]:
        """
        List cache usage for repositories within an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#list-repositories-with-github-actions-cache-usage-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/cache/usage-by-repository"
        params = {"per_page": per_page, "page": page}
        resp = self._get_request(url, params=params)
        data = resp.json()
        repo_count = len(data.get("repository_cache_usages", []))
        self._persist(
            data,
            filename=f"org_{org_name}_cache_usage_by_repo.json",
            level="log",
            post_msg=f"Fetched cache usage for {repo_count} repositories in org {org_name}.",
        )
        return data

    def get_repo_actions_cache_usage(self) -> dict[str, Any]:
        """
        Get cache usage for the current repository.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#get-github-actions-cache-usage-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/cache/usage"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename="repo_cache_usage.json",
            level="log",
            post_msg=(
                f"Repo {self.repo_owner}/{self.repo_name} cache usage: "
                f"{data.get('full_size_in_bytes')} bytes."
            ),
        )
        return data

    def list_repo_actions_caches(
        self,
        ref: str | None = None,
        key: str | None = None,
        sort: str | None = None,
        direction: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> dict[str, Any]:
        """
        List caches configured for the current repository.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#list-github-actions-caches-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/caches"
        params: dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if key is not None:
            params["key"] = key
        if ref is not None:
            params["ref"] = ref
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        resp = self._get_request(url, params=params)
        data = resp.json()
        total_count = data.get("total_count", 0)
        self._persist(
            data,
            filename="repo_actions_caches.json",
            level="log",
            post_msg=f"Fetched {total_count} caches for repo {self.repo_owner}/{self.repo_name}.",
        )
        return data

    def delete_repo_actions_cache_with_key(
        self, key: str, ref: str | None = None
    ) -> bool:
        """
        Delete a cache entry by key
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#delete-github-actions-caches-for-a-repository-using-a-cache-key
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/caches"
        params: dict[str, Any] = {"key": key}
        if ref is not None:
            params["ref"] = ref
        resp = self._delete_request(url, params=params)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "key": key,
                "ref": ref,
                "status_code": resp.status_code,
                "success": success,
            },
            filename="repo_actions_cache_delete_by_key.json",
            level="log",
            post_msg=f"Deleted cache with key={key} ref={ref}.",
        )
        return success

    def delete_repo_actions_cache_with_id(self, cache_id: int) -> bool:
        """
        Delete a cache entry by cache ID.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#delete-a-github-actions-cache-for-a-repository-using-a-cache-id
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/caches/{cache_id}"
        resp = self._delete_request(url)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "cache_id": cache_id,
                "status_code": resp.status_code,
                "success": success,
            },
            filename=f"repo_actions_cache_{cache_id}_deleted.json",
            level="log",
            post_msg=f"Deleted cache #{cache_id}.",
        )
        return success

    # 🏠 Repository
    def get_repo_info(self) -> dict[str, Any]:
        """
        Get metadata of a specific repository.
        GitHub Docs:
        https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            # TODO configurable repo owner, repo name
            filename="repo_info.json",
            level="log",
            post_msg="Repository: {self.repo_owner}/{self.repo_name}",
        )
        return data

    # 📦 Issues
    def list_user_issues(
        self,
        filter: str = "assigned",
        state: str = "open",
        label_list: list[str] | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List issues assigned to the authenticated user across all visible repositories including owned repositories
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-issues-assigned-to-the-authenticated-user
        TODO full parameter/filter support
        TODO full media types support
        """
        url = "/issues"
        params = {
            "filter": filter,
            "state": state,
            "per_page": per_page,
            "page": page,
        }
        if label_list is not None:
            params["labels"] = ",".join(label_list)
        resp = self._get_request(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename="user_issues.json",
            level="log",
            post_msg=f"Fetched {len(data)} issues (filter={filter}, state={state})",
        )
        return data

    def list_repo_issues(
        self,
        milestone: list[str] | None = None,
        state: str = "open",
        assignee_list: list[str] | None = None,
        issue_type_list: list[str] | None = None,
        creator: str | None = None,
        mentioned: str | None = None,
        label_list: list[str] | None = None,
        sort: str | None = None,
        direction: str | None = None,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
        output_filename: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List issues in the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues"
        params: dict[str, Any] = {"state": state, "per_page": per_page, "page": page}
        if milestone is not None:
            # like milestone in update_issue
            if len(milestone) == 0:
                params["milestone"] = "none"
            elif len(milestone) == 1:
                params["milestone"] = milestone[0]
            else:
                raise ValueError(
                    'Invalid `milestone` field in the param: expected an empty list [] or ["none"] to get issues without milestones '
                    'or a single-element list ["*"] to get issues with any milstone '
                    'or ["i"] an `integer` to get issues by `number` field.'
                )
        if assignee_list is not None:
            # Pass `none` for issues with no assigned user,
            # or `*` for issues assigned to any user
            if len(assignee_list) == 0:
                # Pass empty list
                params["assignee"] = "none"
            elif len(assignee_list) == 1:
                # only support single assignee query
                params["assignee"] = assignee_list[0]
            else:
                raise ValueError("Invalid `assignee` field in the param: TODO")
        if issue_type_list is not None:
            if len(issue_type_list) == 0:
                # Pass empty list
                params["type"] = "none"
            elif len(issue_type_list) == 1:
                params["type"] = issue_type_list[0]
            else:
                raise ValueError("Invalid `type` field in the param: TODO")
        if label_list is not None and label_list != []:
            params["labels"] = ",".join(label_list)
        if creator is not None:
            params["creator"] = creator
        if mentioned is not None:
            params["mentioned"] = mentioned
        # The `direction` parameter only takes effect when `sort` is explicitly specified.
        # Default behavior is sorted by `created` `desc`
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            print("⚠️ Ignoring direction since sort is not specified.")
        if since is not None:
            params["since"] = since
        resp = self._get_request(url, params=params)
        data = resp.json()
        # Allow callers to override the output name while retaining a descriptive default.
        filename = output_filename or f"repo_issues_page_{page}_per_{per_page}.json"
        self._persist(
            data,
            filename=filename,
            level="log",
            post_msg=f"Fetched {len(data)} issues (state={state})",
        )
        return data

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        """
        Get a single issue.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#get-an-issue
        :param issue_number: Issue or PR number
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"get_issue_{issue_number}.json",
            level="log",
            post_msg=f"Issue #{issue_number} fetched.",
        )
        return data

    def update_issue(
        self,
        issue_number: int,
        state: str,
        # Reason for the state change, choose from `completed`, `not_planned`, `duplicate`, `reopened`, `null`
        state_reason: str | None = None,
        title: str | None = None,
        body: str | None = None,
        # The number of the milestone, use `null` to remove the current milestone
        milestone: list[Any] | None = None,
        label_list: list[Any] | None = None,
        assignee_list: list[str] | None = None,
        # The name of the issue type to associate with this issue or use null to remove the current issue type
        issue_type_list: list[str] | None = None,
    ):
        """
        Update an issue.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#update-an-issue
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"

        # TODO check legal string of state
        payload: dict[str, Any] = {"state": state, "assignees": assignee_list}
        if state_reason is not None:
            # TODO check legal string of state_reason
            payload["state_reason"] = state_reason
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if milestone is not None:
            # Interpret `milestone` as a wrapper list encoding different operations:
            # None → Do not modify (field omitted)
            # [] → Remove milestone (sends JSON null)
            # [v] → Set milestone (int or str)
            # _ → Raise error (more than one element)
            # Note: Python's `None` will correctly serialize to JSON `null` via `requests`.
            if len(milestone) == 0:
                payload["milestone"] = None
            elif len(milestone) == 1:
                payload["milestone"] = milestone[0]
            else:
                raise ValueError(
                    "Invalid `milestone` field in the payload: expected an empty list [] to remove existing milestone or a single-element list [m] to set m as the new milestone."
                )
        if label_list is not None:
            payload["labels"] = label_list
        if assignee_list is not None:
            payload["assignees"] = assignee_list
        if issue_type_list is not None:
            # Like milestone, use a wrapper list to translate the meaning of setting JSON `null`
            if len(issue_type_list) == 0:
                # []
                payload["type"] = None
            elif len(issue_type_list) == 1:
                payload["type"] = issue_type_list[0]
            else:
                raise ValueError(
                    "Invalid `type` field in the payload: expected an empty list [] to remove issue type or a single-element list [t] to set the issue type."
                )

        resp = self._patch_request(url, payload=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"update_issue_{issue_number}.json",
            level="log",
            post_msg=f"Issue #{issue_number} updated (state={data.get('state', state)}).",
        )
        return data

    def lock_issue(self, issue_number: int, lock_reason: str):
        """
        Lock an issue.
        GitHub Docs:
        https://docs.github.com/zh/rest/issues/issues?apiVersion=2022-11-28#lock-an-issue
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/lock"
        # TODO check legal string of lock_reason
        # It must be one of these reasons: `off-topic`, `too heated`, `resolved`, `spam`
        payload: dict[str, Any] = {"lock_reason": lock_reason}
        resp = self._put_request(url, payload=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"lock_issue_{issue_number}.json",
            level="log",
            # Print status code
            post_msg=f"Try lock Issue #{issue_number} (reason={lock_reason}). HTTP response status {resp.status_code}",
        )
        return data

    def unlock_issue(self, issue_number: int):
        """
        Unlock an issue.
        GitHub Docs:
        https://docs.github.com/zh/rest/issues/issues?apiVersion=2022-11-28#unlock-an-issue
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/lock"
        resp = self._delete_request(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"unlock_issue_{issue_number}.json",
            level="log",
            post_msg=f"Try unlock Issue #{issue_number}. HTTP response status {resp.status_code}",
        )
        return resp.status_code

    # 📦 Pull requets
    # Pull requests are a type of issue. The common actions should be performed through the issues API endpoints
    # Link relations:
    # `self``: The API location of this pull request
    # `html`: The HTML location of this pull request
    # `issue`: The API location of this pull request's issue
    # `comments`: The API location of this pull request's issue comments
    # `review_comments`: The API location of this pull request's review comments
    # `review_comment`: The URL template to construct the API location for a review comment in this pull request's repository
    # `commits`: The API location of this pull request's commits
    # `statuses`: The API location of this pull request's commit statuses, which are the statuses of its head branch
    def list_repo_pulls(
        self,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        sort: str | None = None,
        direction: str | None = None,
        per_page: int = 30,
        page: int = 1,
        output_filename: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List pull requests in the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls"
        params: dict[str, Any] = {"state": state, "per_page": per_page, "page": page}
        if head is not None:
            params["head"] = head
        if base is not None:
            params["base"] = base
        # The `direction` parameter only takes effect when `sort` is explicitly specified.
        # Default behavior is sorted by `created` `desc`
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            print("⚠️ Ignoring direction since sort is not specified.")
        resp = self._get_request(url, params=params)
        data = resp.json()
        # Mirror issue-list output behavior so consumers can control where results land.
        filename = output_filename or f"repo_pulls_page_{page}_per_{per_page}.json"
        self._persist(
            data,
            filename=filename,
            level="log",
            post_msg=f"Fetched {len(data)} pulls (state={state})",
        )
        return data

    def get_pull(self, pull_number: int):
        """
        Get a single pull request by number.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request
        :param pull_number: Pull request number (i.e., issue number of PR)
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}.json",
            level="log",
            post_msg=f"Fetched pull request #{pull_number}.",
        )
        return data

    def create_pull(
        self,
        title: str,  # required unless `issue` is specified
        head: str,
        head_repo,  # required for cross-repository prs
        base: str,
        body: str | None = None,
        draft: bool | None = None,
        issue_number: int | None = None,  # required unless `title` is specified
        maintainer_can_modify: bool | None = None,
    ) -> dict[str, Any]:
        """
        Create a pull request in the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#create-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls"
        payload: dict[str, Any] = {"title": title, "head": head, "base": base}
        if body is not None:
            payload["body"] = body
        if maintainer_can_modify is not None:
            payload["maintainer_can_modify"] = maintainer_can_modify
        if draft is not None:
            payload["draft"] = draft
        # TODO Verify if `title` and `body` are respected when `issue` is provided.
        if issue_number is not None:
            payload["issue"] = issue_number
        resp = self._post_request(url, payload=payload)
        resp.raise_for_status()
        data = resp.json()
        # Check use `id` or `number`
        new_pull_number = data.get("number", "unknown")
        self._persist(
            data,
            filename=f"pull_{new_pull_number}_created.json",
            level="log",
            post_msg=f"New pull request #{new_pull_number} created.",
        )
        return data

    def update_pull(
        self,
        pull_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        base: str | None = None,
        maintainer_can_modify: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#update-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}"
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        # Can be `open`, `closed`
        if state is not None:
            payload["state"] = state
        if base is not None:
            payload["base"] = base
        if maintainer_can_modify is not None:
            payload["maintainer_can_modify"] = maintainer_can_modify
        resp = self._patch_request(url, payload=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_updated.json",
            level="log",
            post_msg=f"Pull request #{pull_number} updated.",
        )
        return data

    def list_pull_commits(
        self, pull_number: int, per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        """
        List commits on a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-commits-on-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/commits"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        resp = self._get_request(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_commits_page_{page}.json",
            level="log",
            post_msg=f"Fetched {len(data)} commits for pull #{pull_number}.",
        )
        return data

    def list_pull_files(
        self, pull_number: int, per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        """
        List files changed in a specified pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/files"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        resp = self._get_request(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_files_page_{page}.json",
            level="log",
            post_msg=f"Fetched {len(data)} files for pull #{pull_number}.",
        )
        return data

    def is_pull_merged(self, pull_number: int) -> bool:
        """
        Check if a pull request has been merged.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#check-if-a-pull-request-has-been-merged
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/merge"
        resp = self._get_request(url)
        # If status code 204 => merged, 404 => not merged
        merge_status = resp.status_code == 204
        self._persist(
            merge_status,
            filename=f"merge_status.json",
            level="log",
            post_msg=f"Pull request #{pull_number} merged status: {merge_status}.",
        )

        return merge_status

    # TODO implement merge_pull and update_pull_branch
    # def merge_pull(
    #     self,
    #     pull_number: int,
    #     commit_title: str | None = None,
    #     commit_message: str | None = None,
    #     sha: str | None = None,
    #     merge_method: str | None = None
    # ):
    #     pass
    # def update_pull_branch(
    #     self,
    #     pull_number: int,
    #     expected_head_sha: str | None = None,
    # ):
    #     pass

    # 📘 Markdown
    def render_markdown(
        self,
        text: str,
        mode: str = "markdown",
        context: str | None = None,
        output_filename: str | None = None,
    ):
        """
        Render a markdown document
        GitHub Docs
        https://docs.github.com/zh/rest/markdown/markdown?apiVersion=2022-11-28#render-a-markdown-document
        """
        url = "/markdown"
        payload = {"text": text, "mode": mode}
        if context is not None:
            # use when use `gfm` mode
            if mode == "gfm":
                payload["context"] = context
            elif mode == "markdown":
                print(
                    "Try to render a markdown with `markdown` mode. `context` setting does not work."
                )
        resp = self._post_request(url, payload=payload)
        rendered = resp.text
        # Always persist
        if output_filename is None:
            filename = f"markdown_rendered_{mode}.html"
        else:
            filename = output_filename
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"Rendered markdown saved -> {output_path}")
        return rendered

    def render_markdown_raw(
        self,
        text: str,
        output_filename: str | None = None,
    ):
        """
        Render a markdown document in raw media
        GitHub Docs
        https://docs.github.com/en/rest/markdown/markdown?apiVersion=2022-11-28#render-a-markdown-document-in-raw-mode
        TODO official doc is not good
        """
        url = "/markdown/raw"
        # using `text/plain` ir `text/x-markdown`
        headers: dict[str, str] = {
            "Content-Type": SupportMediaTypes.TEXT_PLAIN.value,
            "Accept": SupportMediaTypes.TEXT_HTML.value,
        }
        resp = self._post_request(url, headers=headers, data=text.encode("utf-8"))
        rendered = resp.text
        # Always persist
        if output_filename is None:
            filename = "markdown_rendered_raw.html"
        else:
            filename = output_filename
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"Rendered markdown raw saved -> {output_path}")
        return rendered

    # 💬 Comments
    def list_repo_issue_comments(
        self,
        sort: str | None = None,
        direction: str | None = None,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List issue comments for a repository
        GitHub Docs
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#list-issue-comments-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        # The `direction` parameter only takes effect when `sort` is explicitly specified.
        # Default behavior is sorted by `created` `desc`
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            print("⚠️ Ignoring direction since sort is not specified.")
        if since is not None:
            params["since"] = since
        resp = self._get_request(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"repo_issue_comments_{sort}_page_{page}.json",
            level="log",
            post_msg=f"Fetched {len(data)} repo issue comments (sort={sort}).",
        )
        return data

    def list_issue_comments(
        self,
        issue_number: int,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List issue comments with specific `issue_number` (Every pr is an issue, but not every issue is a pr)
        GitHub Docs
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#list-issue-comments
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/comments"
        )
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if since is not None:
            params["since"] = since
        resp = self._get_request(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"issue_{issue_number}_comments_page_{page}.json",
            level="log",
            post_msg=f"Fetched {len(data)} comments for issue #{issue_number}.",
        )
        return data

    def create_single_issue_comment(
        self, issue_number: int, body: str
    ) -> dict[str, Any]:
        """
        Create an issue comment
        GitHub Docs
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#create-an-issue-comment
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/comments"
        )
        payload: dict[str, Any] = {"body": body}
        resp = self._post_request(url, payload=payload)
        resp.raise_for_status()
        data = resp.json()
        new_comment_id = data.get("id", "unknown")
        self._persist(
            data,
            filename=f"issue_comment_{new_comment_id}_created.json",
            level="log",
            post_msg=f"Issue comment #{new_comment_id} for issue #{issue_number} created.",
        )
        return data

    def get_single_issue_comment(
        self,
        comment_id: int,
    ) -> dict[str, Any]:
        """
        Get an issue comment with specific `comment_id`
        GitHub Docs
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#get-an-issue-comment
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments/{comment_id}"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"issue_comment_{comment_id}_readed.json",
            level="log",
            post_msg=f"Issue comment #{comment_id} fetched.",
        )
        return data

    def update_single_issue_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        """
        Update an issue comment
        GitHub Docs
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#update-an-issue-comment
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments/{comment_id}"
        payload: dict[str, Any] = {"body": body}
        resp = self._patch_request(url, payload=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"issue_comment_{comment_id}_updated.json",
            level="log",
            post_msg=f"Issue comment #{comment_id} updated.",
        )
        return data

    def delete_single_issue_comment(
        self,
        comment_id: int,
    ):
        """
        Delete an issue comment
        GitHub Docs
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#delete-an-issue-comment
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments/{comment_id}"
        resp = self._delete_request(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"issue_comment_{comment_id}_deleted.json",
            level="log",
            post_msg="Delete issue comment #{comment_id}. HTTP response status {resp.status_code}",
        )
        return data

    # ⚙️ Meta
    def get_zen(self) -> str:
        """
        Get the Zen of GitHub.
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-the-zen-of-github
        """
        url = "/zen"
        resp = self._get_request(url)
        zen_text = resp.text.strip()
        self._persist(
            {"zen": zen_text},
            filename="github_zen.json",
            level="log",
            post_msg=f'Fetched GitHub Zen text:\n"{zen_text}"',
        )
        return zen_text

    def get_octocat(self, speech_str: str | None = None) -> str:
        """
        Get the Octocat of GitHub
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-octocat
        """
        url = "/octocat"
        params: dict[str, Any] = {}
        if speech_str is not None:
            params["s"] = speech_str
        resp = self._get_request(url, params=params)
        octocat = resp.text
        self._persist(
            {"speech": speech_str, "octocat": octocat},
            filename="github_octocat.json",
            level="log",
            post_msg=f"🐙 Octocat fetched\n{octocat}",
        )
        return octocat

    def get_api_root(self) -> dict[str, Any]:
        """
        Get GitHub API root hypermedia links to top-level API resources.
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-apiname-meta-information
        """
        url = "/"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename="github_api_root.json",
            level="log",
            post_msg=f"Fetched GitHub API root with {len(data)} keys.",
        )
        return data

    def get_github_meta(self) -> dict[str, Any]:
        """
        Get meta information about GitHub
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-github-meta-information
        """
        url = "/meta"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename="github_meta.json",
            level="log",
            post_msg=f"Fetched GitHub API metadata with {len(data)} keys.",
        )
        return data

    def get_api_versions(self) -> list[str]:
        """
        Get all supported GitHub API versions
        """
        url = "/versions"
        resp = self._get_request(url)
        data = resp.json()
        self._persist(
            data,
            filename="github_api_versions.json",
            level="log",
            post_msg=f"List all supported GitHub API versions:\n {data}",
        )
        return data

    # 🧑‍💻 User
    def get_authenticated_user(self) -> dict[str, Any]:
        """
        Get the currently authenticated user's information.
        GitHub Docs:
        https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-the-authenticated-user
        """
        url = "/user"
        resp = self._get_request(url)
        data = resp.json()
        # get user_login and user_id
        user_login = data.get("login", "UNKNOWN")
        user_id = data.get("id", "UNKNOWN")
        # save to auth_user_{id}_{login}.json
        self._persist(
            data,
            filename=f"auth_user_{user_id}_{user_login}.json",
            level="log",
            post_msg="Fetched authenticated user info.",
        )
        return data

    def get_user_with_username(self, username: str) -> dict[str, Any]:
        """
        Get a user's public information with their username.
        GitHub Docs:
        https://docs.github.com/zh/rest/users/users?apiVersion=2022-11-28#get-a-user-using-their-id
        """
        # TODO: check if username is valid
        url = f"/user/{username}"
        resp = self._get_request(url)
        data = resp.json()
        # get user_login and user_id
        user_login = data.get("login", "UNKNOWN")
        user_id = data.get("id", "UNKNOWN")
        # save to user_{username}_{id}.json
        self._persist(
            data,
            filename=f"user_{user_id}_{user_login}.json",
            level="log",
            post_msg=f"Fetched user info for {username}.",
        )
        return data
