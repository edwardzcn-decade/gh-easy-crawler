#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10

"""
GitHub Crawler
This script crawls GitHub repositories (flink-cdc) to collect data for analysis.
REST API and gh CLI based crawlers are supported.
Authors: edwardzcn
"""

import os
import sys

# if sys.version_info < (3, 10):
#     raise RuntimeError(
#         f"Python 3.10 or higher is required. Current Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
#     )
import json
import subprocess
import requests

from pathlib import Path
from typing import Optional
from enum import StrEnum

APP_NAME = "CDCCrawler"
APP_VERSION = "0.1.0"

# Base configurations
GITHUB_API_URL = "https://api.github.com"
# User information
# TODO: get from git config
GITHUB_USER_NAME = "edwardzcn"
GITHUB_USER_EMAIL = "edwardzcn98@gmail.com"
# Get token from environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_CLI_API_TOKEN")


# Target repo information
GITHUB_REPO_OWNER = "apache"
GITHUB_REPO_NAME = "flink-cdc"


class SupportMediaTypes(StrEnum):
    """Supported Media Types for GitHub API"""

    DEFAULT = "application/vnd.github+json"
    RAW = "application/vnd.github.raw+json"
    TEXT = "application/vnd.github.text+json"
    HTML = "application/vnd.github.html"
    # return all
    FULL = "application/vnd.github.full+json"


class GitHubCrawlerBase:
    """Base class for GitHub Crawlers"""

    def __init__(
        self, owner: str | None, repo: str | None = None, token: str | None = None
    ):
        """
        Initialize the GitHubCrawlerBase
        :param repo: GitHub repository in the format "owner/repo" (e.g., "apache/flink-cdc")
        :param token: GitHub access token for authentication
        """
        self.user_name = GITHUB_USER_NAME
        self.user_email = GITHUB_USER_EMAIL
        self.repo_owner = owner or GITHUB_REPO_OWNER
        self.repo_name = repo or GITHUB_REPO_NAME
        self.token = token or os.getenv("GITHUB_TOKEN")

        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def save_json(self, data, filename: str):
        """
        Save data as a JSON file
        :param data: Data to be saved as JSON
        :param filename: Name of the output JSON file
        """
        # TODO: make the tmp_name dynamic based on the class name
        tmp_name = "G"
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{tmp_name} saved to {path}")

    def fetch_issues(self):
        """
        Fetch issues from the GitHub repository
        """
        raise NotImplementedError("Subclasses must implement fetch_issues method")

    def list_prs(self):
        """
        List pull requests from a specified GitHub repository
        """
        raise NotImplementedError("Subclasses must implement fetch_prs method")

    def fetch_docs(self):
        """ "
        Fetch main docs (including README and wiki)
        """
        raise NotImplementedError("Subclasses must implement fetch_docs method")


class GitHubRESTCrawler(GitHubCrawlerBase):
    """GitHub Crawler using REST API"""

    def __init__(self,owner: str | None = None, repo: str | None = None, token: str | None = None):
        super().__init__(owner, repo, token)
        self.base_url = GITHUB_API_URL
        self.headers = self._get_headers()

    def _get_default_accept_header(self):
        return SupportMediaTypes.DEFAULT

    def _get_headers(self):
        user_agent = f"{APP_NAME}/{APP_VERSION}"
        media_type = self._get_default_accept_header().value
        headers = {
            "Accept": media_type,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": user_agent,
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def get_zen(self):
        request_url = f"{GITHUB_API_URL}/zen"
        response = requests.get(request_url, headers=self.headers)
        response.raise_for_status()
        zen = response.text
        print(f"GitHub Zen: {zen}")
        return zen

    def list_prs(self):
        request_url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls"
        request_headers = self.headers
        # response = requests.get(
        #     request_url, request_headers, params={"state": "all"}
        # )
        response = requests.get(request_url, headers=request_headers)
        response.raise_for_status()
        prs = response.json()
        self.save_json(prs, "pull_requests.json")

    def get_readme(self):
        request_url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/readme"
        request_headers = self.headers
        response = requests.get(request_url, headers=request_headers)
        response.raise_for_status()
        readme = response.json()
        self.save_json(readme, "readme.json")

    def get_user(self):
        requests_url = f"{self.base_url}/user"
        request_headers = self.headers
        response = requests.get(requests_url, headers=request_headers)
        response.raise_for_status()
        user = response.json()
        print(f"Authenticated user: {user}")

def main():
    crawler = GitHubRESTCrawler(token=GITHUB_TOKEN)
    try:
        crawler.get_zen()
        crawler.get_user()
        crawler.list_prs()
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()