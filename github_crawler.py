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



class GitHubRESTCrawler(GitHubCrawlerBase):
    """GitHub Crawler using REST API"""

    def __init__(self,owner: str | None = None, repo: str | None = None, token: str | None = None):
        super().__init__(owner, repo, token)
        self.base_url = GITHUB_API_URL
        self.headers = self._get_headers()



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

    # List all comments in one repo ordered by ascending ID by default
    def list_all_comments_repo(self, owner: str | None = None, repo: str | None = None):
        o = unwrap_or(owner, self.repo_owner)
        r = unwrap_or(repo, self.repo_name)
        request_url = f"{self.base_url}/repos/{o}/{r}/issues/comments"
        request_headers = self.headers
        response = requests.get(request_url, headers=request_headers)
        response.raise_for_status()
        comments = response.json()
        self.save_json(comments, "all_comments.json")

    def list_issue_all_comments(self, issue_number: int, owner: str | None = None, repo: str | None = None):
        o = unwrap_or(owner, self.repo_owner)
        r = unwrap_or(repo, self.repo_name)
        request_url = f"{self.base_url}/repos/{o}/{r}/issues/{issue_number}/comments"
        request_headers = self.headers
        response = requests.get(request_url, headers=request_headers)
        response.raise_for_status()
        comments = response.json()
        self.save_json(comments, f"issue_{issue_number}_comments.json")
    
    def list_issue_meta(self, issue_number: int, owner: str | None = None, repo: str | None = None):
        o = unwrap_or(owner, self.repo_owner)
        r = unwrap_or(repo, self.repo_name)
        request_url = f"{self.base_url}/repos/{o}/{r}/pulls/{issue_number}"
        request_headers = self.headers
        response = requests.get(request_url, headers=request_headers)
        response.raise_for_status()
        issue_meta = response.json()
        self.save_json(issue_meta, f"issue_{issue_number}_meta.json")

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
        crawler.list_issue_meta(issue_number=3285)
        crawler.list_issue_all_comments(issue_number=3285)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()