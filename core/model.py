"""
This module provides the basic models.
"""

import logging
import requests

from .base import GitHubBase
from .exceptions import GitHubHTTPError, TransportError, error_from_response
from .config import GITHUB_API_URL

logger = logging.getLogger(__name__)


class GitHubCore(GitHubBase):
    """The base object for all objects required a session.

    Provide basic attributes e.g. request
    """

    api_root: str = GITHUB_API_URL

    def __init__(
        self,
        session_user: str | None,
        session_repo: str | None,
        session_token: str | None,
        output_dir: str | None,
        session: requests.Session | None = None,
    ) -> None:
        super().__init__(session_user, session_repo, session_token, output_dir)
        # TODO implement session
        self.session = session
        # TODO: Make media type configurable
        self.headers = {
            "Accept": self._get_accept_media_default(),
            "User-Agent": self._get_user_agent_default(),
            "X-GitHub-Api-Version": self._get_api_version(),
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _boolean(self, response: requests.Response, true_code: int, false_code: int):
        if response is not None:
            status_code = response.status_code
            if status_code == true_code:
                return True
            if status_code != false_code and status_code >= 400:
                raise error_from_response(response)
        return False

    def _request(self, method: str, url: str, **kwargs):
        """
        Unified low-level HTTP request handler for API calls.
        :param method: HTTP method to use (e.g., 'GET', 'POST', 'PATCH', 'PUT', 'DELETE').
        :param url: Full URL or API endpoint path to send the request to.

        Other selected arguments in kwargs
        :param headers: Optional dictionary of HTTP headers to include in the request.
                        These headers override the default headers.
        :param params: Optional dictionary to send as a list of params in the query string.
        :param json: Optional json payload to send in the request body.
        :param data: Optional raw data or bytes (e.g. for /markdown/raw)
        :param timeout: Optional timeout setting for the request in seconds.
                        Can be a float or a tuple (connect timeout, read timeout).
        :return: The `requests.Response` object resulting from the HTTP request.
        :raises: Raises `TransportError` or `GitHubHTTPError` from custom exceptions.
        """
        # Check endpoint and construct url
        if not url.startswith("http"):
            url = self._build_url(endpoint=url)
        # Merge headers with extra provided headers
        # - For Python <3.9, use: {**self.headers, **(headers or {})}
        # - For Python >=3.9, use the dict union operator: self.headers | (headers or {})
        extra_headers: dict[str, str] = kwargs.pop("headers", None) or {}
        request_headers = self.headers | extra_headers
        kwargs["headers"] = request_headers
        # TODO implement session
        # http = self.session or requests
        try:
            # TODO Use session as the original: request_method = getattr(self.session, method)
            # TODO                              return request_method(*args, **kwargs)
            resp = requests.request(method.upper(), url, **kwargs)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exc:
            # TODO add ConnectionError or maybe retry
            raise TransportError(exc)
        except requests.exceptions.RequestException as exc:
            raise TransportError(exc)
        # For HTTP success code
        if 200 <= resp.status_code < 300:
            return resp
        # For HTTP error code
        err: GitHubHTTPError = error_from_response(resp)
        logger.error(
            "GitHub HTTP error during %s %s: status=%s, text(partial)=%s",
            method.upper(),
            url,
            err.code,
            err.text[:200],
        )
        raise err

    def _delete(self, url: str, **kwargs):
        logger.debug("DELETE %s with %s", url, kwargs)
        return self._request("DELETE", url, **kwargs)

    def _get(self, url: str, **kwargs):
        logger.debug("GET %s with %s", url, kwargs)
        if "json" in kwargs:
            logger.warning(
                "⚠️ A json payload exists in GET request. You may want to use `params` instead"
            )
        # Pop/clear json
        kwargs.pop("json", None)
        return self._request("GET", url, **kwargs)

    def _patch(self, url: str, **kwargs):
        logger.debug("PATCH %s with %s", url, kwargs)
        return self._request("PATCH", url, **kwargs)

    def _post(self, url: str, data=None, if_json: bool = True, **kwargs):
        if if_json:
            # Just pass data to json param (let requests do serialization)
            if data is not None:
                if "json" in kwargs:
                    logger.warning(
                        "⚠️ Both 'json' and 'data' are provided in POST request. 'data' argument will be ignored"
                    )
                kwargs.setdefault("json", data)
        else:
            # pass the raw data
            if data is not None:
                kwargs.setdefault("data", data)

        logger.debug("POST %s with %s, %s", url, data, kwargs)
        return self._request("POST", url, **kwargs)

    def _put(self, url: str, **kwargs):
        logger.debug("PUT %s with %s", url, kwargs)
        return self._request("PUT", url, **kwargs)

    # def _build_url(self, *args, **kwargs):
    #     """Build a new API url from scratch."""
    #     return self.session.build_url(*args, **kwargs)
