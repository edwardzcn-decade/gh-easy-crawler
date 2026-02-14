#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10
"""
Base classes and utilities for GitHub API implementations (REST or GitHub CLI)
"""

import logging
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from .config import (
    APP_NAME,
    APP_VERSION,
    GITHUB_USER_NAME,
    GITHUB_USER_EMAIL,
    GITHUB_REPO_NAME,
    GITHUB_REPO_OWNER,
    GITHUB_API_VERSION,
    GITHUB_API_URL,
    OUTPUT_DIR_DEFAULT,
    SAVE_MODE_DEFAULT,
    SupportMediaTypes,
)

logger = logging.getLogger(__name__)


class GitHubBase(ABC):
    """The abstract base class for all GitHub API implementations"""

    def __init__(
        self,
        owner: str | None = None,
        repo: str | None = None,
        token: str | None = None,
        output_dir: str | None = None,
    ):
        """
        Initialize the GitHubBase.

        :param owner: GitHub repository owner name
        :param repo: GitHub repository name
        :param token: Access token for authentication (optional)
        """
        self.app_name = APP_NAME
        self.app_version = APP_VERSION
        self.user_name = GITHUB_USER_NAME
        self.user_email = GITHUB_USER_EMAIL
        # Only work >= Python 3.10
        match (owner, repo):
            case (None, None):
                logger.info("Using default repository from config.")
                self.repo_name = GITHUB_REPO_NAME
                self.repo_owner = GITHUB_REPO_OWNER
            case (str() as o, str() as r):
                logger.info(f"Using provided owner and repo: {o}/{r}")
                self.repo_owner = o
                self.repo_name = r
            case (_, _):
                logger.info("You must provide both owner and repo, or neither.")
                sys.exit(1)
        if token is None:
            logger.info("This app will operate in unauthenticated mode.")
        else:
            logger.info("Using provided token for authentication.")
        self.token = token

        # Set up output directory
        if (
            SAVE_MODE_DEFAULT == "always"
            or SAVE_MODE_DEFAULT == "auto"
            and logger.getEffectiveLevel() <= logging.INFO
        ):
            if output_dir is not None:
                logger.info(
                    f"This app will persist file in specified dir: {output_dir}"
                )
                self.output_dir = Path(output_dir)
            else:
                logger.info(
                    f"This app will persist file in default dir: {OUTPUT_DIR_DEFAULT}"
                )
                self.output_dir = Path(OUTPUT_DIR_DEFAULT)
            self.output_dir.mkdir(exist_ok=True)
        elif output_dir is not None:
            if SAVE_MODE_DEFAULT == "never":
                logger.warning(
                    f"⚠️ This app will not persist file due to the setting {SAVE_MODE_DEFAULT} of SAVE_MODE_DEFAULT. Omit output_dir."
                )
            else:
                logger.warning(
                    f"⚠️ This app will not persist file due to the setting {SAVE_MODE_DEFAULT} of SAVE_MODE_DEFAULT. It will follow the logger level and it is not in INFO/DEBUG. Omit output_dir"
                )

    def _get_user_agent_fake(self) -> str:
        """Return a realistic fake browser user agent string for debugging."""

        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Safari/537.36"
        )

    def _get_accept_media_default(self) -> str:
        return f"{SupportMediaTypes.DEFAULT.value}"

    def _get_user_agent_default(self) -> str:
        return f"{APP_NAME}/{APP_VERSION} ({self.user_name})"

    def _get_api_version(self) -> str:
        return GITHUB_API_VERSION

    def _persist(
        self,
        data,  # json data
        filename: str,
        pre_msg: str | None = None,
        post_msg: str | None = None,
    ):
        match SAVE_MODE_DEFAULT:
            case "always":
                self._save_json_output(data, filename, post_msg)
            case "never":
                pass
            case "auto":
                if logger.getEffectiveLevel() <= logging.INFO:
                    logger.info(
                        "Logger level is under INFO and SAVE_MODE_DEFAULT is set to auto. Persist the file."
                    )
                    self._save_json_output(data, filename, post_msg)

    def _save_json_output(
        self,
        data,
        filename: str,
        post_msg: str | None = None,
    ):
        """
        Save data as a JSON file
        :param data: Data to be saved as JSON
        :param filename: Name of the output JSON file
        """
        caller_name = self.__class__.__name__
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        msgs = []
        msgs.append(f"✅ [{caller_name}] Saved JSON → {output_path}")
        if post_msg:
            msgs.append(post_msg)
        m = " | ".join(msgs)
        logger.info(f"{m}")

    def _build_url(self, endpoint: str) -> str:
        """
        Construct full API URL from endpoint
        TODO make endpoint a type and checkable
        :param endpoint: API endpoint e.g. `/repos/{owner}/{repo}/issues`, `/user`, `/repos/{owner}/{repo}/pulls/{number}`
        """
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        return f"{GITHUB_API_URL}{endpoint}"

    @abstractmethod
    def _get(self, url: str, **kwargs):
        """
        Abstract method to perform a GET request
        REST subclasses should use requests.get();
        CLI subclasses should use subprocess.run("gh api --method GET ...").
        :param url: Full/endpoint URL to send the GET request to
        """
        pass

    @abstractmethod
    def _patch(self, url: str, **kwargs):
        """
        Abstract method to perform a PATCH request
        REST subclasses should use requests.patch();
        CLI subclasses should use subprocess.run("gh api --method PATCH ...").
        :param url: Full/endpoint URL to send the PATCH request to
        """
        pass

    @abstractmethod
    def _put(self, url: str, **kwargs):
        """
        Abstract method to perform a PUT request
        REST subclasses should use requests.put();
        CLI subclasses should use subprocess.run("gh api --method PUT ...").
        :param url: Full/endpoint URL to send the PUT request to
        """
        pass

    @abstractmethod
    def _post(self, url: str, **kwargs):
        """
        Abstract method to perform a POST request
        REST subclasses should use requests.post();
        CLI subclasses should use subprocess.run("gh api --method POST ...").
        :param url: Full/endpoint URL to send the POST request to
        """
        pass

    @abstractmethod
    def _delete(self, url: str, **kwargs):
        """
        Abstract method to perform a DELETE request
        REST subclasses should use requests.delete();
        CLI subclasses should use subprocess.run("gh api --method DELETE ...").
        :param url: Full/endpoint URL to send the DELETE request to
        """
        pass
