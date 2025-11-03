#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10

"""
GitHub API Crawler Implementation
Implements various common APIs for REST API and gh CLI based crawlers.
Authors: edwardzcn
"""

import requests
from typing import Any
from .base import GitHubCrawlerBase
from .config import SupportMediaTypes


class GitHubRESTCrawler(GitHubCrawlerBase):
    """GitHub REST API implementation of GitHubCrawlerBase"""

    def __init__(
        self, owner: str | None, repo: str | None = None, token: str | None = None
    ):
        super().__init__(owner, repo, token)
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
    def _get_request(self, url: str, headers: dict[str, str] | None = None, **kwargs):
        """
        Implementation of abstract `_get_request()` method for REST API.
        Use requests.get() for making GET requests.
        :param url:
        :param headers:
        :param kwargs: Optional arguments
        """
        # Check if it is endpoint or full URL
        if not url.startswith("http"):
            url = self._build_url(endpoint=url)
        if headers is None:
            resp = requests.get(url, headers=self.headers, **kwargs)
        else:
            resp = requests.get(url, headers=headers, **kwargs)
        try:
            resp.raise_for_status()
        except Exception as e:
            print(f"[GitHubRESTCrawler] Error during GET request to {url}: {e}")
            print(f"Response Status Code: {resp.status_code}")
            print(f"Response Content: {resp.text[:200]}")
            raise
        return resp

    # --------------------------------------------------------
    # REST API Endpoints
    # --------------------------------------------------------
    def get_authenticated_user(self) -> dict[str, Any]:
        """
        Get the currently authenticated user's information.
        GitHub Docs:
        https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-the-authenticated-user
        """
        url = "/user"
        resp = self._get_request(url)
        user = resp.json()
        # get user_login and user_id
        user_login = user.get("login", "UNKNOWN")
        user_id = user.get("id", "UNKNOWN")
        # save to auth_user_{id}_{login}.json
        self._save_json_output(
            user,
            f"auth_user_{user_id}_{user_login}.json",
            post_msg="Fetched authenticated user info.",
        )
        return user

    def get_user_with_username(self, username: str) -> dict[str, Any]:
        """
        Get a user's public information with their username.
        GitHub Docs:
        https://docs.github.com/zh/rest/users/users?apiVersion=2022-11-28#get-a-user-using-their-id
        """
        # TODO: check if username is valid
        url = f"/user/{username}"
        resp = self._get_request(url)
        user = resp.json()
        # get user_login and user_id
        user_login = user.get("login", "UNKNOWN")
        user_id = user.get("id", "UNKNOWN")
        # save to user_{username}_{id}.json
        self._save_json_output(
            user,
            f"user_{user_id}_{user_login}.json",
            post_msg=f"Fetched user info for {username}.",
        )
        return user

    def get_repo_info(self) -> dict[str, Any]:
        """
        Get metadata of a specific repository.
        GitHub Docs:
        https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}"
        resp = self._get_request(url)
        repo_info = resp.json()
        self._save_json_output(
            repo_info,
            "repo_info.json",
            post_msg=f"Repository: {self.repo_owner}/{self.repo_name}",
        )
        return repo_info

    def list_repo_issues(
        self,
        state: str = "open",
        assignee: str | None = None,
        issue_type: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List issues in the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues
        TODO full parameter/filter support
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues"
        params = {"state": state, "per_page": per_page}
        resp = self._get_request(url, params=params)
        if assignee:
            params["assignee"] = assignee
        if issue_type:
            params["type"] = issue_type
        data = resp.json()
        self._save_json_output(
            data, "issues.json", post_msg=f"Fetched {len(data)} issues (state={state})"
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
        issue = resp.json()
        self._save_json_output(
            issue,
            f"issue_{issue_number}.json",
            post_msg=f"Issue #{issue_number} fetched.",
        )
        return issue

    # TODO
    # Need PATCH method
    def update_issue(
        self,
        issue_number: int,
        state: str,
        title: str | None = None,
        body: str | None = None,
        assignee: list[str] = [],
        issue_type: str | None = None,
    ):
        """
        Update an issue.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#update-an-issue
        TODO full parameter support
        """
        pass

    # TODO
    # Need PUT method
    def lock_issue(self, issue_number: int, lock_reason: str):
        """
        Lock an issue.
        GitHub Docs:
        https://docs.github.com/zh/rest/issues/issues?apiVersion=2022-11-28#lock-an-issue
        TODO full parameter support
        """
        pass

    # TODO
    # Need DELETE method
    def unlock_issue(self, issue_number: int):
        """
        Unlock an issue.
        GitHub Docs:
        https://docs.github.com/zh/rest/issues/issues?apiVersion=2022-11-28#unlock-an-issue
        """
        pass

    # TODO
    # Need POST method
    def render_markdown(self, text: str, mode: str, context: str):
        """
        Render a markdown document
        GitHub Docs
        https://docs.github.com/zh/rest/markdown/markdown?apiVersion=2022-11-28#render-a-markdown-document
        """
        pass

    # TODO
    # Need POST method
    def render_markdown_raw(self, text: str):
        """
        Render a markdown document in raw media
        GitHub Docs
        https://docs.github.com/en/rest/markdown/markdown?apiVersion=2022-11-28#render-a-markdown-document-in-raw-mode
        TODO official doc is not good
        """
        pass
