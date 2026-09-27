import httpx
import pytest

from bugpipe.api.client import Bugpipe
from bugpipe.api.models import (
    Comment,
    CommentsResult,
    Issue,
    IssueUpdatesResult,
    Priority,
    SearchResult,
    Status,
)


@pytest.fixture
def client():
    with Bugpipe() as bugpiper:
        yield bugpiper


class TestEcho:
    def test_echo_returns_yes(self, client: Bugpipe) -> None:
        """
        Verify that the issue tracker backend is reachable.

        :param client: Bugpipe client.
        """

        assert client.echo() == "yes"


class TestSearch:
    def test_returns_search_result(self, client: Bugpipe) -> None:
        """
        Verify that a search returns a valid :class:`SearchResult`.

        :param client: Bugpipe client.
        """

        result = client.search("status:open", page_size=5)

        assert isinstance(result, SearchResult)
        assert result.total_count > 0
        assert len(result.issues) > 0
        assert len(result.issues) <= 5

    def test_issues_have_basic_fields(self, client: Bugpipe) -> None:
        """
        Verify that each issue in a search result has the expected fields.

        :param client: Bugpipe client.
        """

        result = client.search("status:open", page_size=3)

        for issue in result.issues:
            assert isinstance(issue, Issue)
            assert isinstance(issue.id, int)
            assert issue.id > 0
            assert isinstance(issue.title, str)
            assert len(issue.title) > 0
            assert isinstance(issue.status, Status)
            assert isinstance(issue.priority, Priority)

    def test_pagination_token_present(self, client: Bugpipe) -> None:
        """
        Verify that a paginated search includes a next-page token.

        :param client: Bugpipe client.
        """

        result = client.search("status:open", page_size=1)

        assert result.has_more is True
        assert result.next_page_token is not None
        assert isinstance(result.next_page_token, str)

    def test_query_filters_work(self, client: Bugpipe) -> None:
        """
        Verify that component-based query filters return results.

        :param client: Bugpipe client.
        """

        result = client.search("component:Blink", page_size=3)

        assert isinstance(result, SearchResult)
        assert result.total_count > 0
        assert len(result.issues) > 0


class TestGetIssue:
    @staticmethod
    def _find_accessible_issue(client: Bugpipe) -> Issue:
        """
        Find an issue that isn't internal/redacted.

        :param client: Bugpipe client.
        :returns: The first accessible :class:`Issue`.
        """

        search = client.search("status:open", page_size=10)
        for candidate in search.issues:
            try:
                return client.issue(candidate.id)
            except (ValueError, httpx.HTTPStatusError):
                continue
        pytest.skip("All candidate issues are internal (empty response)")

    def test_returns_issue(self, client: Bugpipe) -> None:
        """
        Verify that fetching a single issue returns a valid :class:`Issue`.

        :param client: Bugpipe client.
        """

        issue = self._find_accessible_issue(client)

        assert isinstance(issue, Issue)
        assert isinstance(issue.id, int)

    def test_issue_has_all_basic_fields(self, client: Bugpipe) -> None:
        """
        Verify that a fetched issue has all expected basic fields populated.

        :param client: Bugpipe client.
        """

        issue = self._find_accessible_issue(client)

        assert isinstance(issue.id, int)
        assert isinstance(issue.title, str)
        assert len(issue.title) > 0
        assert isinstance(issue.status, Status)
        assert isinstance(issue.priority, Priority)
        assert issue.created_at is not None
        assert issue.modified_at is not None
        assert issue.url == f"https://issuetracker.google.com/issues/{issue.id}"

    def test_issue_has_reporter(self, client: Bugpipe) -> None:
        """
        Verify that the issue has a reporter with a valid email address.

        :param client: Bugpipe client.
        """

        issue = self._find_accessible_issue(client)

        assert issue.reporter is not None
        assert "@" in issue.reporter

    def test_timestamps_are_sane(self, client: Bugpipe) -> None:
        """
        Verify that ``created_at`` and ``modified_at`` are reasonable dates.

        :param client: Bugpipe client.
        """

        issue = self._find_accessible_issue(client)

        assert issue.created_at is not None and issue.modified_at is not None
        assert issue.created_at.year >= 2008  # Chromium tracker existed since ~2008
        assert issue.modified_at >= issue.created_at

    def test_issue_has_body(self, client: Bugpipe) -> None:
        """
        Verify that a single issue fetch includes the body/description.

        Some issues (e.g. Android Beta Feedback) have redacted bodies,
        so we search for a fixed Chromium issue which is more likely
        to have a visible description.

        :param client: Bugpipe client.
        """

        search = client.search("status:fixed", page_size=10)
        for candidate in search.issues:
            try:
                issue = client.issue(candidate.id)
            except (ValueError, httpx.HTTPStatusError):
                continue
            if issue.body is not None:
                assert isinstance(issue.body, str)
                assert len(issue.body) > 0
                return
        pytest.skip("No issue with a visible body found")


class TestBatchGetIssues:
    def test_returns_all_requested_issues(self, client: Bugpipe) -> None:
        """
        Verify that a batch get returns exactly the requested issues.

        :param client: Bugpipe client.
        """

        # Get some issue IDs first
        search = client.search("status:open", page_size=3)
        ids = [i.id for i in search.issues]

        issues = client.issues(ids)

        assert len(issues) == len(ids)
        returned_ids = {i.id for i in issues}
        assert returned_ids == set(ids)

    def test_batch_issues_have_basic_fields(self, client: Bugpipe) -> None:
        """
        Verify that batch-fetched issues have all expected basic fields.

        :param client: Bugpipe client.
        """

        search = client.search("status:open", page_size=2)
        ids = [i.id for i in search.issues]

        issues = client.issues(ids)

        for issue in issues:
            assert isinstance(issue, Issue)
            assert issue.id > 0
            assert len(issue.title) > 0
            assert isinstance(issue.status, Status)
            assert isinstance(issue.priority, Priority)


class TestGetIssueUpdates:
    def test_returns_updates_result(self, client: Bugpipe) -> None:
        """
        Verify that fetching updates returns a valid :class:`IssueUpdatesResult`.

        :param client: Bugpipe client.
        """

        # Find an issue that has comments
        search = client.search("status:fixed", page_size=5)
        # Pick one with comments
        target = None
        for issue in search.issues:
            if issue.comment_count > 0:
                target = issue
                break
        if target is None:
            pytest.skip("No issue with comments found in search results")

        result = client.issue_updates(target.id)

        assert isinstance(result, IssueUpdatesResult)
        assert result.total_count > 0
        assert len(result.updates) > 0

    def test_updates_have_authors_and_timestamps(self, client: Bugpipe) -> None:
        """
        Verify that each update has an author and a timestamp.

        :param client: Bugpipe client.
        """

        search = client.search("status:fixed", page_size=5)
        target = next((i for i in search.issues if i.comment_count > 0), None)
        if target is None:
            pytest.skip("No issue with comments found")

        result = client.issue_updates(target.id)

        for update in result.updates:
            assert update.issue_id == target.id
            assert update.author is not None
            assert update.timestamp is not None


class TestGetComments:
    @staticmethod
    def _find_public_comments(
        client: Bugpipe, min_comments: int = 1
    ) -> tuple[Issue, CommentsResult]:
        """
        Search for a non-internal issue with at least ``min_comments`` visible
        comments.

        Internal issues are identified by all comment authors being @google.com
        — these typically have redacted/empty bodies. The API can also return
        fewer comments than the issue's ``comment_count`` field suggests, so
        the actual count is re-checked here.

        :param client: Bugpipe client.
        :param min_comments: Minimum number of visible comments required.
        :returns: A tuple of the matching :class:`Issue` and its :class:`CommentsResult`.
        """

        search = client.search("status:fixed", page_size=10)
        candidates = [
            issue for issue in search.issues if issue.comment_count >= min_comments
        ]
        if not candidates:
            pytest.skip(f"No issue with {min_comments}+ comments found")

        for candidate in candidates:
            result = client.comments(candidate.id)
            if len(result.comments) < min_comments:
                continue
            if all(
                comment.author and comment.author.endswith("@google.com")
                for comment in result.comments
            ):
                continue
            return candidate, result

        pytest.skip("All candidate issues are internal (@google.com)")

    def test_returns_comments_result(self, client: Bugpipe) -> None:
        """
        Verify that comments() returns a CommentsResult with expected fields.

        :param client: Bugpipe client.
        """

        _, result = self._find_public_comments(client)

        assert isinstance(result, CommentsResult)
        assert result.total_count > 0
        assert result.total_count == len(result.comments) or result.has_more

    def test_returns_comments_in_chronological_order(self, client: Bugpipe) -> None:
        """
        Verify that ASC sort returns comments in chronological order.

        :param client: Bugpipe client.
        """

        candidate, result = self._find_public_comments(client, min_comments=2)

        assert len(result.comments) >= 2
        for comment in result.comments:
            assert isinstance(comment, Comment)
            assert comment.issue_id == candidate.id
            assert isinstance(comment.comment_number, int)
            assert comment.comment_number >= 1

        for earlier, later in zip(result.comments, result.comments[1:]):
            if earlier.timestamp and later.timestamp:
                assert earlier.timestamp <= later.timestamp

    def test_desc_sort_reverses_order(self, client: Bugpipe) -> None:
        """
        Verify that DESC sort returns newest comments first.

        :param client: Bugpipe client.
        """

        candidate, asc_result = self._find_public_comments(client, min_comments=2)
        desc_result = client.comments(candidate.id, sort_order="DESC")

        asc_seqs = [c.comment_number for c in asc_result.comments]
        desc_seqs = [c.comment_number for c in desc_result.comments]
        assert asc_seqs == list(reversed(desc_seqs))

    def test_pagination(self, client: Bugpipe) -> None:
        """
        Verify that pagination returns subsequent comments and eventually ends.

        :param client: Bugpipe client.
        """

        candidate, _ = self._find_public_comments(client, min_comments=2)

        page1 = client.comments(candidate.id, page_size=1)
        assert len(page1.comments) == 1
        assert page1.has_more

        page2 = client.comments(
            candidate.id,
            page_size=1,
            page_token=page1.next_page_token,
        )
        assert len(page2.comments) == 1
        assert page1.comments[0].comment_number != page2.comments[0].comment_number

    def test_comments_have_content(self, client: Bugpipe) -> None:
        """
        Verify that at least one comment has a non-empty body.

        :param client: Bugpipe client.
        """

        _, result = self._find_public_comments(client)

        assert len(result.comments) > 0
        assert any(len(comment.body) > 0 for comment in result.comments)

    def test_comment_authors_are_emails(self, client: Bugpipe) -> None:
        """
        Verify that comment authors are valid email addresses.

        :param client: Bugpipe client.
        """

        _, result = self._find_public_comments(client)

        for comment in result.comments:
            if comment.author:
                assert "@" in comment.author

    def test_comment_numbers_are_one_indexed(self, client: Bugpipe) -> None:
        """
        Verify that comment numbers start at 1, not 0.

        :param client: Bugpipe client.
        """

        _, result = self._find_public_comments(client)

        assert result.comments[0].comment_number >= 1

    def test_total_count_matches_returned(self, client: Bugpipe) -> None:
        """
        Verify that total_count matches the number of comments returned
        when all comments fit in a single page.

        :param client: Bugpipe client.
        """

        _, result = self._find_public_comments(client)

        if not result.has_more:
            assert result.total_count == len(result.comments)
