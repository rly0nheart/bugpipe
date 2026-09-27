from bugpipe.api.models import (
    AttachmentRestriction,
    Comment,
    FieldChange,
    Issue,
    IssueType,
    IssueUpdate,
    IssueUpdatesResult,
    Priority,
    Results,
    SearchResult,
    Severity,
    Status,
)


class TestAttachmentRestriction:
    def test_known_values(self):
        assert AttachmentRestriction.NO_RESTRICTION == 1
        assert AttachmentRestriction.RESTRICTED == 2
        assert AttachmentRestriction.RESTRICTED_PLUS == 3

    def test_missing_value_creates_unknown(self):
        unknown = AttachmentRestriction(4)
        assert unknown.value == 4
        assert unknown.name == "UNKNOWN_4"


class TestStatus:
    def test_known_values(self):
        assert Status.NEW == 1
        assert Status.FIXED == 4
        assert Status.DUPLICATE == 10

    def test_missing_value_creates_unknown(self):
        unknown = Status(99)
        assert unknown.value == 99
        assert unknown.name == "UNKNOWN_99"

    def test_is_open_for_open_statuses(self):
        assert Status.NEW.is_open is True
        assert Status.ASSIGNED.is_open is True
        assert Status.ACCEPTED.is_open is True

    def test_is_open_for_closed_statuses(self):
        assert Status.FIXED.is_open is False
        assert Status.VERIFIED.is_open is False
        assert Status.NOT_REPRODUCIBLE.is_open is False
        assert Status.DUPLICATE.is_open is False


class TestPriority:
    def test_known_values(self):
        assert Priority.P0 == 0
        assert Priority.P4 == 4

    def test_missing_value(self):
        p99 = Priority(99)
        assert p99.value == 99
        assert p99.name == "P99"


class TestSeverity:
    def test_known_values(self):
        assert Severity.S0 == 0
        assert Severity.S4 == 4

    def test_missing_value(self):
        s99 = Severity(99)
        assert s99.value == 99
        assert s99.name == "S99"


class TestIssueType:
    def test_known_values(self):
        assert IssueType.BUG == 1
        assert IssueType.VULNERABILITY == 6

    def test_missing_value(self):
        unknown = IssueType(42)
        assert unknown.value == 42
        assert unknown.name == "TYPE_42"


class TestIssue:
    def test_url_property(self):
        issue = Issue(id=12345, title="test")
        assert issue.url == "https://issuetracker.google.com/issues/12345"

    def test_defaults(self):
        issue = Issue(id=1, title="t")
        assert issue.status == Status.NEW
        assert issue.priority == Priority.P2
        assert issue.severity is None
        assert issue.ccs == []
        assert issue.collaborators == []
        assert issue.found_in == []
        assert issue.in_prod is None
        assert issue.duplicate_issue_ids == []
        assert issue.os == []
        assert issue.custom_fields == {}
        assert issue.comment_count == 0
        assert issue.star_count == 0
        assert issue.views_24h == 0
        assert issue.views_7d == 0
        assert issue.views_30d == 0


class TestSearchResult:
    def test_has_more_with_token(self):
        result = SearchResult(issues=Results(), total_count=100, next_page_token="abc")
        assert result.has_more is True

    def test_has_more_without_token(self):
        result = SearchResult(issues=Results(), total_count=0)
        assert result.has_more is False


class TestIssueUpdatesResult:
    def test_comments_filters_and_reverses(self):
        comment_a = Comment(issue_id=1, comment_number=1, body="first")
        comment_b = Comment(issue_id=1, comment_number=2, body="second")

        updates = Results(
            [
                IssueUpdate(issue_id=1, comment=comment_b),  # newest first
                IssueUpdate(
                    issue_id=1, field_changes=[FieldChange(field="status")]
                ),  # no comment
                IssueUpdate(issue_id=1, comment=comment_a),  # oldest
            ]
        )
        result = IssueUpdatesResult(updates=updates, total_count=3)

        comments = result.comments
        assert len(comments) == 2
        assert comments[0].body == "first"
        assert comments[1].body == "second"

    def test_comments_empty_when_no_comments(self):
        updates = Results(
            [IssueUpdate(issue_id=1, field_changes=[FieldChange(field="priority")])]
        )
        result = IssueUpdatesResult(updates=updates, total_count=1)
        assert result.comments == []

    def test_has_more(self):
        result = IssueUpdatesResult(
            updates=Results(), total_count=0, next_page_token="tok"
        )
        assert result.has_more is True

        result2 = IssueUpdatesResult(updates=Results(), total_count=0)
        assert result2.has_more is False
