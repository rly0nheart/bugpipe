from __future__ import annotations

import typing as t

import httpx

from .parser import (
    __parse_batch_response as parse_batch_response,
    __parse_comments_response as parse_comments_response,
    __parse_issue_detail_response as parse_issue_detail_response,
    __parse_search_response as parse_search_response,
    __parse_updates_response as parse_updates_response,
)

if t.TYPE_CHECKING:
    from httpx import Response

    from .models import CommentsResult, Issue, IssueUpdatesResult, Results, SearchResult

__all__ = ["TRACKERS", "Bugpipe"]

TRACKERS: list[dict[str, str | int]] = [
    {
        "id": 1,
        "slug": "pigweed",
        "name": "Pigweed",
        "url": "https://issues.pigweed.dev",
    },
    {
        "id": 27,
        "slug": "gerrit",
        "name": "Gerrit",
        "url": "https://issues.gerritcodereview.com",
    },
    {
        "id": 53,
        "slug": "git",
        "name": "Git",
        "url": "https://git.issues.gerritcodereview.com",
    },
    {"id": 79, "slug": "skia", "name": "Skia", "url": "https://issues.skia.org"},
    {"id": 105, "slug": "webrtc", "name": "WebRTC", "url": "https://issues.webrtc.org"},
    {
        "id": 131,
        "slug": "libyuv",
        "name": "libyuv",
        "url": "https://libyuv.issues.chromium.org",
    },
    {
        "id": 157,
        "slug": "chromium",
        "name": "Chromium",
        "url": "https://issues.chromium.org",
    },
    {
        "id": 183,
        "slug": "fuchsia",
        "name": "Fuchsia",
        "url": "https://issues.fuchsia.dev",
    },
    {
        "id": 235,
        "slug": "angle",
        "name": "ANGLE",
        "url": "https://issues.angleproject.org",
    },
    {
        "id": 261,
        "slug": "aomedia",
        "name": "AOMedia",
        "url": "https://aomedia.issues.chromium.org",
    },
    {
        "id": 287,
        "slug": "webm",
        "name": "WebM",
        "url": "https://issues.webmproject.org",
    },
    {"id": 339, "slug": "gn", "name": "GN", "url": "https://gn.issues.chromium.org"},
    {
        "id": 365,
        "slug": "project-zero",
        "name": "Project Zero",
        "url": "https://project-zero.issues.chromium.org",
    },
    {
        "id": 391,
        "slug": "oss-fuzz",
        "name": "OSS Fuzz",
        "url": "https://issues.oss-fuzz.com",
    },
]

USER_AGENT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


class Bugpipe:
    """
    Python client for the Google Issue Tracker.

    Wraps the non-public JSON-array API at issuetracker.google.com. Supports
    searching issues, fetching individual issues, batch fetching, and
    reading comments/updates.

    Can be used as a context manager::

        with Bugpipe() as client:
            result = client.search("priority:p1")

    :param trackers: Trackers to query. Accepts names (e.g. ``["chromium"]``)
        or numeric ID strings (e.g. ``["157"]``). Names are resolved via
        ``TRACKERS``. Pass multiple to search across specific trackers.
        Defaults to None (search all public trackers).
    :param timeout: HTTP request timeout in seconds. Defaults to 30.
    :param proxy: Proxy URL to route all requests through, e.g.
        ``"http://localhost:8080"``. Defaults to None, which honours the
        ``HTTP_PROXY``/``HTTPS_PROXY`` environment variables.
    """

    def __init__(
        self,
        trackers: list[str | int] | None = None,
        timeout: float = 30.0,
        proxy: str | None = None,
    ):
        """
        Configure the underlying :class:`httpx.Client` and resolve any
        tracker slugs to their numeric IDs. See the class docstring for
        parameter details.
        """

        self.base_endpoint: str = "https://issuetracker.google.com/action"

        self.tracker_ids: list[str | int] | None = None
        if trackers:
            tracker_by_slug = {tracker["slug"]: tracker["id"] for tracker in TRACKERS}
            self.tracker_ids = [tracker_by_slug.get(name, name) for name in trackers]

        self._http = httpx.Client(
            headers={
                "Content-Type": "application/json",
                "Origin": "https://issuetracker.google.com",
                "Referer": "https://issuetracker.google.com/",
                "User-Agent": USER_AGENT,
            },
            timeout=timeout,
            proxy=proxy,
        )

    def close(self):
        """
        Close the client and release its resources.

        Should be called when the client is no longer needed if not using
        it as a context manager.
        """

        self._http.close()

    def __enter__(self):
        """
        Context-manager entry. Returns ``self`` unchanged.
        """

        return self

    def __exit__(self, *args):
        """
        Context-manager exit. Closes the underlying HTTP client.
        """

        self.close()

    def echo(self) -> str:
        """
        Ping the issue tracker backend and return its raw response.

        :return: The raw response text, which is ``"yes"`` when the backend
            is reachable and healthy. Returns ``"no"`` when the backend is
            unreachable or responds with a non-200 status.
        """

        url = f"{self.base_endpoint}/yes"
        try:
            response: Response = self._http.get(url)
            if response.status_code == 200:
                return response.text.strip()
            return "no"
        except httpx.HTTPError:
            return "no"

    def search(
        self,
        query: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> SearchResult:
        """
        Search for issues in the Google Issue Tracker.

        :param query: Search query string (e.g. "status:open", "component:Blink").
        :param page_size: Number of results per page (25, 50, 100, or 250).
        :param page_token: Pagination token from a previous SearchResult.next_page_token.
        :return: Matching issues, total count, and pagination token.
        """

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        query_payload: list = (
            [query, None, page_size, page_token]
            if page_token
            else [query, None, page_size]
        )
        tracker_filter = self.tracker_ids if self.tracker_ids else None
        request_body: list = [
            None,
            None,
            None,
            None,
            None,
            tracker_filter,
            query_payload,
        ]
        url: str = f"{self.base_endpoint}/issues/list"

        response: Response = self._http.post(url, json=request_body)
        response.raise_for_status()
        return parse_search_response(
            raw_text=response.text, query=query, page_size=page_size
        )

    def next_page(self, result: SearchResult) -> SearchResult | None:
        """
        Fetch the next page of a search result.

        :param result: A previous SearchResult.
        :return: The next page of results, or None if there are no more pages.
        """

        if not result.has_more:
            return None

        return self.search(
            query=result.query,
            page_size=result.page_size,
            page_token=result.next_page_token,
        )

    def issue(self, issue_id: int) -> Issue:
        """
        Fetch a single issue by its numeric ID.

        :param issue_id: The issue ID (e.g. 40060244).
        :return: The fully populated issue.
        """

        request_body: list = [issue_id, 2, 1]
        url: str = f"{self.base_endpoint}/issues/{issue_id}/getIssue"

        response: Response = self._http.post(url=url, json=request_body)
        response.raise_for_status()
        return parse_issue_detail_response(raw_text=response.text)

    def issues(self, issue_ids: list[int]) -> Results[Issue]:
        """
        Fetch multiple issues by ID in a single request.

        :param issue_ids: List of issue IDs to fetch.
        :return: The fetched issues (order may not match input), as a list that
            writes itself out via ``to_json()``/``to_csv()``.
        """

        request_body: list = ["b.BatchGetIssuesRequest", None, None, [issue_ids, 2, 2]]
        url: str = f"{self.base_endpoint}/issues/batch"

        response: Response = self._http.post(url, json=request_body)
        response.raise_for_status()
        return parse_batch_response(raw_text=response.text)

    def issue_updates(self, issue_id: int) -> IssueUpdatesResult:
        """
        Fetch all updates (comments and field changes) for an issue.

        Returns updates in reverse chronological order (newest first).
        Use ``result.comments`` to get just the comments in chronological order.

        :param issue_id: The issue ID to fetch updates for.
        :return: Updates, total count, and pagination token.
        """

        url: str = f"{self.base_endpoint}/issues/{issue_id}/updates"
        # currentTrackerId appears unnecessary, issue IDs are unique across all trackers,
        # and resolve correctly regardless of what tracker is sent to the server.
        # params=QueryParams({"currentTrackerId": self.tracker_ids[0] if self.tracker_ids else None}),
        response: Response = self._http.post(url=url, json=[issue_id])
        response.raise_for_status()

        return parse_updates_response(raw_text=response.text)

    def comments(
        self,
        issue_id: int,
        sort_order: str = "ASC",
        page_size: int = 500,
        page_token: str | None = None,
    ) -> CommentsResult:
        """
        Fetch comments for an issue.

        Returns only text comments (no field-change-only updates).
        Use :meth:`issue_updates` if you need field changes.

        :param issue_id: The issue ID to fetch comments for.
        :param sort_order: ``"ASC"`` for oldest-first, ``"DESC"`` for newest-first.
        :param page_size: Number of comments per page (max 500).
        :param page_token: Pagination token from a previous CommentsResult.
        :return: Comments and pagination info.
        """

        url: str = f"{self.base_endpoint}/issues/{issue_id}/listComments"
        request_body: list = [issue_id, sort_order, page_size]
        if page_token:
            request_body.append(page_token)

        response: Response = self._http.post(url, json=request_body)
        response.raise_for_status()
        return parse_comments_response(raw_text=response.text)
