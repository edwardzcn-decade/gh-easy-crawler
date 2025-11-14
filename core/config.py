#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10
"""
Configuration and global constants for GitHub Crawler
"""

import os
from pathlib import Path
from enum import StrEnum

# Application information
APP_NAME = "gh-crawler"
APP_VERSION = "0.1.0"
APP_AUTHOR = "edwardzcn <edwardzcn98@gmail.com>"

# GitHub API configuration
# GitHub API base
GITHUB_API_URL = "https://api.github.com"
# API version (as X-GitHub-Api-Version header)
GITHUB_API_VERSION = "2022-11-28"

# User information
# TODO: Optionally get from git config
GITHUB_USER_NAME = os.getenv("GITHUB_USER_NAME", "edwardzcn")
GITHUB_USER_EMAIL = os.getenv("GITHUB_USER_EMAIL", "edwardzcn98@gmail.com")
# Default target repository owner and name
# https://github.com/octocat/Hello-World
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "octocat")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "Hello-World")
# Default test repository (should be private) to run UTs
# Make sure you have required permission sets
GITHUB_REPO_OWNER_TEST = os.getenv("GITHUB_REPO_OWNER_TEST", "edwardzcn-decade")
GITHUB_REPO_NAME_TEST = os.getenv("GITHUB_REPO_NAME_TEST", "gh-api-test-repo")

# Token from environment variable
GITHUB_TOKEN_DEFAULT = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_CLI_API_TOKEN")
GITHUB_TOKEN_TEST = None

# Output directory
# TODO: Make configurable and add sqlite support
OUTPUT_DIR_DEFAULT = "output"
OUTPUT_DIR_TEST = "test_output"
SAVE_MODE_DEFAULT = "auto" # could be "auto" "never" "always"


# Supported Media Types for GitHub API
class SupportMediaTypes(StrEnum):
    """Supported Media Types for GitHub API"""

    DEFAULT = "application/vnd.github+json"
    RAW = "application/vnd.github.raw+json"
    TEXT = "application/vnd.github.text+json"
    HTML = "application/vnd.github.html"
    # return all
    FULL = "application/vnd.github.full+json"
    TEXT_PLAIN = "text/plain"
    TEXT_HTML = "text/html"

    # def _get_default_media_type_str(self) -> str:
    #     return SupportMediaTypes.DEFAULT.value


# Util functions
def get_github_token_default() -> str | None:
    """Get GitHub token from environment variables."""
    return GITHUB_TOKEN_DEFAULT


def get_github_token_test() -> str | None:
    """Get GitHub token used for UTs"""
    if GITHUB_TOKEN_TEST is not None:
        return GITHUB_TOKEN_TEST
    else:
        return GITHUB_TOKEN_DEFAULT


def unwrap_or(x, default):
    return x if x is not None else default


def sanitize_fragment(value: str) -> str:
    return (
        "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)
        or "rendered"
    )
