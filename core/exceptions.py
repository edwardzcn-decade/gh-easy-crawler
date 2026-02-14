"""
Custom exception hierarchy for GitHub crawler

This is a **minimal** subset adapted from github3.py's exceptions, focusing mainly on HTTP errors.

Future versions may extend this exception tree.

GitHubException                 # The single root base exception type
├── TransportError              # Error underlying HTTP client request without a valid response
└── GitHubHTTPError             # Error with HTTP response (base, middle layer)
    ├── IncompleteResponseError    # Error with incomplete response
    └── CompleteResponseError      # Error with complete response (middle layer)
        ├── AuthenticationFailed   # 401
        ├── ForbiddenError         # 403
        ├── NotFoundError          # 404
        ├── ClientError            # 4xx
        └── ServerError            # 5xx
"""

from __future__ import annotations  # default setting from python 3.11
from requests import Response


class GitHubException(Exception):
    """The base GitHub exception class."""

    pass


class TransportError(GitHubException):
    """Exception class for errors occurred while making a request to GitHub on the transport layer.

    E.g. connection errors, DNS failures or timeouts.
    """

    def __init__(self, exception: BaseException) -> None:
        # Keep the original exception for debugging or further classification
        self.msg = f"Error while making a request to GitHub: {exception!r}"
        self.exc = exception
        super().__init__(self.msg)

    def __str__(self) -> str:
        # return self.msg
        # With type notation
        return f"{type(self.exc).__name__}: {self.msg}"


class GitHubHTTPError(GitHubException):
    """The base exception class for all response-related exceptions.

    May have complete/incomplete response
    """

    def __init__(self, resp: Response):
        self.resp = resp
        self.code = resp.status_code
        self.text = resp.text
        super().__init__(self.code, self.text)

    def __str__(self) -> str:
        return f"{type(self).__name__}: {self.code} {self.text}"


class IncompleteResponseError(GitHubHTTPError):
    """Error when the response body is incomplete"""

    pass


class CompleteResponseError(GitHubHTTPError):
    """The base exception class for all specific HTTP *status* errors.

    All concrete 4xx / 5xx errors inherit from this. Catch this if you
    want to handle "anything that came back from GitHub but was not 2xx".
    """

    pass


class AuthenticationFailed(CompleteResponseError):
    """Exception class for 401 responses (Unauthorized).

    Typical reasons:
    - Invalid token ("Bad credentials")
    - Missing authentication
    - Need one-time-password (OTP for two-factor authentication)
    """

    pass


class ForbiddenError(CompleteResponseError):
    """Exception class for 403 responses (Forbidden).

    Typical reasons:
    - Token lacks required scopes / permissions (further requirements)
    - Rate limit exceeded (too many requests)
    - Login times limit (too many login failures)
    """

    pass


class NotFoundError(CompleteResponseError):
    """Exception class for 404 responses (Not Found).

    Typical reasons:
    - Wrong endpoints
    - Resources not existing
    """

    pass


class UnprocessableEntity(CompleteResponseError):
    """Exception class for 422 responses.

    Typical reasons:
    - Self-request review
    """

    pass


class ClientError(CompleteResponseError):
    """Catch-all for 4xx responses that aren't mapped to a specific class."""

    pass


class ServerError(CompleteResponseError):
    """Any 5xx responses from GitHub."""

    pass


def error_from_response(response: Response) -> GitHubHTTPError:
    """Return an initialized exception for the given non-2xx response."""
    status_code = response.status_code

    if status_code == 401:
        return AuthenticationFailed(response)
    if status_code == 403:
        return ForbiddenError(response)
    if status_code == 404:
        return NotFoundError(response)
    if status_code == 422:
        return UnprocessableEntity(response)
    if 400 <= status_code < 500:
        return ClientError(response)
    if 500 <= status_code < 600:
        return ServerError(response)

    # This should not normally be hit if you only call it for non-2xx,
    # but we keep a conservative fallback.
    return CompleteResponseError(response)
