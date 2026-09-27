import json
from datetime import UTC
from typing import Any

import pytest

from bugpipe.api.models import (
    Attachment,
    AttachmentRestriction,
    IssueType,
    Priority,
    Severity,
    Status,
)
from bugpipe.api.parser import (
    # The parser's helpers are name-mangled inside a class body, so they come in
    # under plain names the test classes below can call.
    __get as get,
    __parse_batch_response as parse_batch_response,
    __parse_ccs as parse_ccs,
    __parse_comment as parse_comment,
    __parse_custom_field_values as parse_custom_field_values,
    __parse_email as parse_email,
    __parse_field_changes as parse_field_changes,
    __parse_int_list as parse_int_list,
    __parse_issue_detail_response as parse_issue_detail_response,
    __parse_issue_from_entry as parse_issue_from_entry,
    __parse_json_response as parse_json_response,
    __parse_search_response as parse_search_response,
    __parse_timestamp as parse_timestamp,
    __parse_updates_response as parse_updates_response,
    __strip_response_prefix as strip_response_prefix,
)

XSSI_PREFIX = ")]}'\n"


def _make_issue_entry(
    issue_id: int = 100,
    component_id: int = 999,
    status: int = 3,
    priority: int = 1,
    title: str = "Test issue",
    reporter_email: str | None = "reporter@test.com",
    owner_email: str | None = "owner@test.com",
    comment_count: int = 5,
    star_count: int = 10,
    issue_type: int | None = 1,
    tracker_id: int = 157,
    created_ts: list[int] | None = None,
    custom_fields: list[list[Any]] | None = None,
    hotlist_ids: list[int] | None = None,
    duplicate_ids: list[int] | None = None,
    blocking_ids: list[int] | None = None,
    ccs: list[list[Any]] | None = None,
    severity: int | None = None,
    found_in: list[str] | None = None,
    in_prod: bool | None = None,
    collaborators: list[list[Any]] | None = None,
    views: list[int] | None = None,
) -> list[Any]:
    """Build a minimal 48-element issue entry array for testing."""
    # Details array (need at least 31 elements for collaborators at index 30)
    details: list[Any] = [None] * 31
    details[0] = component_id
    details[1] = issue_type
    details[2] = status
    details[3] = priority + 1  # API uses 1-indexed priority (P0=1, P1=2, ...)
    if severity is not None:
        details[4] = severity + 1  # API uses 1-indexed severity (S0=1, S1=2, ...)
    details[5] = title
    details[6] = [None, reporter_email, 1] if reporter_email else None
    details[9] = ccs or []
    details[13] = hotlist_ids or []
    details[14] = custom_fields or []
    details[16] = found_in
    details[19] = in_prod
    details[21] = duplicate_ids or []
    details[30] = collaborators or []

    # Top-level array (48 elements)
    entry: list[Any] = [None] * 48
    entry[1] = issue_id
    entry[2] = details
    entry[4] = created_ts or [1700000000, 0]
    entry[5] = [1700001000, 0]
    entry[9] = star_count
    entry[10] = [issue_type] if issue_type else None
    entry[11] = comment_count
    entry[13] = [None, owner_email, 1] if owner_email else None
    entry[36] = blocking_ids or []
    entry[41] = tracker_id
    entry[46] = views or []
    entry[47] = [None, "modifier@test.com", 1]
    return entry


# --- strip_response_prefix ---


class TestStripResponsePrefix:
    def test_strips_standard_prefix(self) -> None:
        assert strip_response_prefix(")]}'\n[1,2,3]") == "[1,2,3]"

    def test_strips_escaped_prefix(self) -> None:
        assert strip_response_prefix(")]}'\\n[1,2,3]") == "[1,2,3]"

    def test_strips_crlf_prefix(self) -> None:
        assert strip_response_prefix(")]}'\r\n[1,2,3]") == "[1,2,3]"

    def test_returns_unchanged_without_prefix(self) -> None:
        assert strip_response_prefix("[1,2,3]") == "[1,2,3]"


# --- parse_json_response ---


class TestParseJsonResponse:
    def test_parses_prefixed_json(self) -> None:
        raw = XSSI_PREFIX + '[["b.Response", 42]]'
        result = parse_json_response(raw)
        assert result == [["b.Response", 42]]

    def test_parses_plain_json(self) -> None:
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}


# --- get ---


class TestSafeGet:
    def test_single_index(self) -> None:
        assert get([10, 20, 30], 1) == 20

    def test_nested_indices(self) -> None:
        assert get([[1, 2], [3, 4]], 1, 0) == 3

    def test_out_of_bounds_returns_default(self) -> None:
        assert get([1, 2], 5, default="nope") == "nope"

    def test_none_input_returns_default(self) -> None:
        assert get(None, 0, default="d") == "d"

    def test_nested_out_of_bounds(self) -> None:
        assert get([[1]], 0, 5, default=-1) == -1


# --- _parse_timestamp ---


class TestParseTimestamp:
    def test_seconds_only(self) -> None:
        dt = parse_timestamp([1700000000])
        assert dt is not None
        assert dt.tzinfo == UTC
        assert dt.year == 2023

    def test_seconds_and_nanos(self) -> None:
        dt = parse_timestamp([1700000000, 500000000])
        assert dt is not None
        assert dt.microsecond == 500000

    def test_none_returns_none(self) -> None:
        assert parse_timestamp(None) is None

    def test_empty_list_returns_none(self) -> None:
        assert parse_timestamp([]) is None

    def test_non_list_returns_none(self) -> None:
        assert parse_timestamp("not a list") is None


# --- _parse_email ---


class TestParseEmail:
    def test_standard_user_array(self) -> None:
        assert parse_email([None, "user@example.com", 1]) == "user@example.com"

    def test_none_returns_none(self) -> None:
        assert parse_email(None) is None

    def test_empty_list_returns_none(self) -> None:
        assert parse_email([]) is None

    def test_no_string_returns_none(self) -> None:
        assert parse_email([None, None, 1]) is None

    def test_non_list_returns_none(self) -> None:
        assert parse_email(42) is None


# --- _parse_ccs ---


class TestParseCcs:
    def test_multiple_ccs(self) -> None:
        raw = [
            [None, "a@test.com", 1],
            [None, "b@test.com", 1],
        ]
        assert parse_ccs(raw) == ["a@test.com", "b@test.com"]

    def test_empty_returns_empty(self) -> None:
        assert parse_ccs([]) == []
        assert parse_ccs(None) == []

    def test_skips_invalid_entries(self) -> None:
        raw = [
            [None, "a@test.com", 1],
            [None, None, None],  # no email
        ]
        assert parse_ccs(raw) == ["a@test.com"]


# --- _parse_int_list ---


class TestParseIntList:
    def test_filters_ints(self) -> None:
        assert parse_int_list([1, "x", 2, None, 3]) == [1, 2, 3]

    def test_empty_returns_empty(self) -> None:
        assert parse_int_list([]) == []
        assert parse_int_list(None) == []


# --- _parse_custom_field_values ---


class TestParseCustomFieldValues:
    def test_value_precedence_and_empty_label_fallback(self) -> None:
        """Use numeric, label, enum, then display values in that order."""
        for numeric, labels, enums, expected in [
            (0, [["label"]], [["enum"]], 0),
            (None, [["label", 1], "other"], [["enum"]], ["label", "other"]),
            (None, [[None, 1]], [["enum"]], ["enum"]),
            (None, "invalid", [["enum"]], ["enum"]),
            (None, [], [[None, 1]], "display"),
        ]:
            entry = [
                9999999,
                None,
                None,
                None,
                numeric,
                labels,
                None,
                enums,
                None,
                "display",
            ]
            assert parse_custom_field_values(raw_field_entries=[entry]) == {
                "field_9999999": expected
            }

    def test_numeric_field(self) -> None:
        # field_id 1410892 = "cwe_id", numeric value at index 4
        entry = [1410892, None, None, None, 79.0, None, None, None, None, None]
        result = parse_custom_field_values([entry])
        assert result["cwe_id"] == 79.0

    def test_label_field(self) -> None:
        # field_id 1223084 = "os", labels at index 5
        entry = [
            1223084,
            None,
            None,
            None,
            None,
            [["Linux", "Mac"]],
            None,
            None,
            None,
            None,
        ]
        result = parse_custom_field_values([entry])
        assert result["os"] == ["Linux", "Mac"]

    def test_enum_field(self) -> None:
        # field_id 1223087 = "merge", enum values at index 7
        entry = [
            1223087,
            None,
            None,
            None,
            None,
            None,
            None,
            [["Approved"]],
            None,
            None,
        ]
        result = parse_custom_field_values([entry])
        assert result["merge"] == ["Approved"]

    def test_display_string_fallback(self) -> None:
        # Unknown field with only a display string at index 9
        entry = [9999999, None, None, None, None, None, None, None, None, "some value"]
        result = parse_custom_field_values([entry])
        assert result["field_9999999"] == "some value"

    def test_empty_returns_empty(self) -> None:
        assert parse_custom_field_values(None) == {}
        assert parse_custom_field_values([]) == {}

    def test_skips_non_list_entries(self) -> None:
        result = parse_custom_field_values(["not a list", 42])
        assert result == {}


# --- parse_issue_from_entry ---


class TestParseIssueFromEntry:
    def test_basic_fields(self) -> None:
        entry = _make_issue_entry(
            issue_id=42,
            title="Hello world",
            status=4,
            priority=0,
            issue_type=1,
        )
        issue = parse_issue_from_entry(entry)

        assert issue.id == 42
        assert issue.title == "Hello world"
        assert issue.status == Status.FIXED
        assert issue.priority == Priority.P0
        assert issue.issue_type == IssueType.BUG

    def test_people_fields(self) -> None:
        entry = _make_issue_entry(
            reporter_email="r@test.com",
            owner_email="o@test.com",
        )
        issue = parse_issue_from_entry(entry)

        assert issue.reporter == "r@test.com"
        assert issue.owner == "o@test.com"
        assert issue.last_modifier == "modifier@test.com"

    def test_counts(self) -> None:
        entry = _make_issue_entry(comment_count=7, star_count=20)
        issue = parse_issue_from_entry(entry)

        assert issue.comment_count == 7
        assert issue.star_count == 20

    def test_timestamps(self) -> None:
        entry = _make_issue_entry(created_ts=[1700000000, 0])
        issue = parse_issue_from_entry(entry)

        assert issue.created_at is not None
        assert issue.created_at.year == 2023
        assert issue.modified_at is not None

    def test_custom_fields_extracted(self) -> None:
        os_field = [
            1223084,
            None,
            None,
            None,
            None,
            [["Linux", "Windows"]],
            None,
            None,
            None,
            None,
        ]
        cve_field = [
            1223136,
            None,
            None,
            None,
            None,
            [["CVE-2024-1234"]],
            None,
            None,
            None,
            None,
        ]
        entry = _make_issue_entry(custom_fields=[os_field, cve_field])
        issue = parse_issue_from_entry(entry)

        assert issue.os == ["Linux", "Windows"]
        assert issue.cve == ["CVE-2024-1234"]

    def test_hotlist_ids(self) -> None:
        entry = _make_issue_entry(hotlist_ids=[100, 200, 300])
        issue = parse_issue_from_entry(entry)
        assert issue.hotlist_ids == [100, 200, 300]

    def test_blocking_ids(self) -> None:
        entry = _make_issue_entry(blocking_ids=[10, 20])
        issue = parse_issue_from_entry(entry)
        assert issue.blocking_issue_ids == [10, 20]

    def test_duplicate_ids(self) -> None:
        entry = _make_issue_entry(duplicate_ids=[30, 40])
        issue = parse_issue_from_entry(entry)
        assert issue.duplicate_issue_ids == [30, 40]

    def test_severity(self) -> None:
        entry = _make_issue_entry(severity=2)
        issue = parse_issue_from_entry(entry)
        assert issue.severity == Severity.S2

    def test_severity_none_when_missing(self) -> None:
        entry = _make_issue_entry()
        issue = parse_issue_from_entry(entry)
        assert issue.severity is None

    def test_found_in(self) -> None:
        entry = _make_issue_entry(found_in=["M120", "M121"])
        issue = parse_issue_from_entry(entry)
        assert issue.found_in == ["M120", "M121"]

    def test_in_prod_true(self) -> None:
        entry = _make_issue_entry(in_prod=True)
        issue = parse_issue_from_entry(entry)
        assert issue.in_prod is True

    def test_in_prod_none_when_missing(self) -> None:
        entry = _make_issue_entry()
        issue = parse_issue_from_entry(entry)
        assert issue.in_prod is None

    def test_collaborators(self) -> None:
        collab_list = [
            [None, "alice@test.com", 1],
            [None, "bob@test.com", 1],
        ]
        entry = _make_issue_entry(collaborators=collab_list)
        issue = parse_issue_from_entry(entry)
        assert issue.collaborators == ["alice@test.com", "bob@test.com"]

    def test_views(self) -> None:
        entry = _make_issue_entry(views=[5, 20, 100])
        issue = parse_issue_from_entry(entry)
        assert issue.views_24h == 5
        assert issue.views_7d == 20
        assert issue.views_30d == 100

    def test_views_empty(self) -> None:
        entry = _make_issue_entry()
        issue = parse_issue_from_entry(entry)
        assert issue.views_24h == 0
        assert issue.views_7d == 0
        assert issue.views_30d == 0

    def test_views_preserve_positions_and_default_invalid_values(self) -> None:
        """Keep valid counts in place and default missing or invalid counts to zero."""
        for views, expected in [
            ([5, "invalid", 100], (5, 0, 100)),
            ([5], (5, 0, 0)),
            ({0: 5, 1: 20, 2: 100}, (0, 0, 0)),
        ]:
            entry = _make_issue_entry()
            entry[46] = views
            issue = parse_issue_from_entry(raw_entry=entry)
            assert (issue.views_24h, issue.views_7d, issue.views_30d) == expected

    def test_url_property(self) -> None:
        entry = _make_issue_entry(issue_id=12345)
        issue = parse_issue_from_entry(entry)
        assert issue.url == "https://issuetracker.google.com/issues/12345"

    def test_unknown_custom_fields_go_to_custom_fields_dict(self) -> None:
        unknown_field = [
            9999999,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "mystery",
        ]
        entry = _make_issue_entry(custom_fields=[unknown_field])
        issue = parse_issue_from_entry(entry)
        assert issue.custom_fields.get("field_9999999") == "mystery"

    def test_ccs(self) -> None:
        cc_list = [
            [None, "a@test.com", 1],
            [None, "b@test.com", 1],
        ]
        entry = _make_issue_entry(ccs=cc_list)
        issue = parse_issue_from_entry(entry)
        assert issue.ccs == ["a@test.com", "b@test.com"]

    def test_minimal_entry(self) -> None:
        """Parsing a very sparse entry shouldn't crash."""
        entry: list[Any] = [None] * 48
        entry[1] = 1
        details: list[Any] = [None] * 22
        details[5] = "sparse"
        entry[2] = details
        issue = parse_issue_from_entry(entry)
        assert issue.id == 1
        assert issue.title == "sparse"


# --- parse_search_response ---


class TestParseSearchResponse:
    def test_parses_issues_and_metadata(self) -> None:
        issue1 = _make_issue_entry(issue_id=1, title="First")
        issue2 = _make_issue_entry(issue_id=2, title="Second")

        response_data = [
            [
                "b.IssueSearchResponse",
                None,
                None,
                None,
                None,
                None,
                [[issue1, issue2], "next_token_abc", 42],
            ]
        ]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_search_response(raw)
        assert len(result.issues) == 2
        assert result.issues[0].id == 1
        assert result.issues[1].id == 2
        assert result.total_count == 42
        assert result.next_page_token == "next_token_abc"
        assert result.has_more is True

    def test_empty_results(self) -> None:
        response_data: list[list[Any]] = [
            ["b.IssueSearchResponse", None, None, None, None, None, [[], None, 0]]
        ]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_search_response(raw)
        assert len(result.issues) == 0
        assert result.total_count == 0
        assert result.has_more is False

    def test_no_pagination_token(self) -> None:
        response_data: list[list[Any]] = [
            ["b.IssueSearchResponse", None, None, None, None, None, [[], None, 5]]
        ]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_search_response(raw)
        assert result.next_page_token is None
        assert result.has_more is False


# --- parse_issue_detail_response ---


class TestParseIssueDetailResponse:
    def test_finds_issue_in_payload(self) -> None:
        issue = _make_issue_entry(issue_id=42, title="Detail test")
        # 23-element payload, issue at the end
        payload = [None] * 22 + [issue]
        response_data = [["b.IssueFetchResponse", payload]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_issue_detail_response(raw)
        assert result.id == 42
        assert result.title == "Detail test"

    def test_raises_when_issue_not_found(self) -> None:
        response_data = [["b.IssueFetchResponse", [None, None, None]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        with pytest.raises(ValueError, match="Could not locate issue entry"):
            parse_issue_detail_response(raw)


# --- parse_batch_response ---


class TestParseBatchResponse:
    def test_parses_multiple_issues(self) -> None:
        issue1 = _make_issue_entry(issue_id=10, title="Batch 1")
        issue2 = _make_issue_entry(issue_id=20, title="Batch 2")

        response_data = [["b.BatchGetIssuesResponse", None, [[issue1, issue2]]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        results = parse_batch_response(raw)
        assert len(results) == 2
        assert results[0].id == 10
        assert results[1].id == 20

    def test_empty_batch(self) -> None:
        response_data: list[list[Any]] = [["b.BatchGetIssuesResponse", None, [[]]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        results = parse_batch_response(raw)
        assert results == []


# --- _parse_field_changes ---


class TestParseFieldChanges:
    def test_parses_field_names(self) -> None:
        raw = [["status", None, None, None], ["priority", None, None, None]]
        changes = parse_field_changes(raw)
        assert len(changes) == 2
        assert changes[0].field == "status"
        assert changes[1].field == "priority"

    def test_empty_returns_empty(self) -> None:
        assert parse_field_changes(None) == []
        assert parse_field_changes([]) == []

    def test_skips_non_list_entries(self) -> None:
        changes = parse_field_changes([["status"], "bad", 42])
        assert len(changes) == 1


# --- _parse_comment ---


class TestParseComment:
    def test_parses_comment(self) -> None:
        # 18-element comment array
        raw: list[Any] = [None] * 18
        raw[0] = "Hello world"
        raw[2] = [None, "author@test.com", 1]
        raw[3] = [1700000000, 0]
        raw[6] = 4  # 0-indexed sequence

        comment = parse_comment(raw, issue_id=42)
        assert comment is not None
        assert comment.body == "Hello world"
        assert comment.author == "author@test.com"
        assert comment.comment_number == 5  # 4 + 1
        assert comment.issue_id == 42
        assert comment.timestamp is not None

    def test_none_returns_none(self) -> None:
        assert parse_comment(None, issue_id=1) is None

    def test_non_list_returns_none(self) -> None:
        assert parse_comment("not a list", issue_id=1) is None


# --- parse_updates_response ---


class TestParseUpdatesResponse:
    @staticmethod
    def _make_update_entry(
        issue_id: int = 42,
        author_email: str | None = "user@test.com",
        timestamp: list[int] | None = None,
        comment_text: str | None = None,
        sequence: int = 0,
        field_changes: list[list[Any]] | None = None,
        attachments: list[list[Any]] | None = None,
    ) -> list[Any]:
        """Build a minimal 10-element update entry."""
        entry: list[Any] = [None] * 10
        entry[0] = [None, author_email, 1] if author_email else None
        entry[1] = timestamp or [1700000000, 0]
        if comment_text is not None:
            comment: list[Any] = [None] * 18
            comment[0] = comment_text
            comment[2] = [None, author_email, 1] if author_email else None
            comment[3] = timestamp or [1700000000, 0]
            comment[6] = sequence
            entry[2] = comment
        entry[3] = sequence
        entry[5] = field_changes
        entry[7] = attachments
        entry[9] = issue_id
        return entry

    def test_parses_updates_with_comments(self) -> None:
        update1 = self._make_update_entry(comment_text="newer", sequence=1)
        update2 = self._make_update_entry(comment_text="older", sequence=0)

        response_data = [["b.ListIssueUpdatesResponse", [[update1, update2], None, 2]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_updates_response(raw)
        assert result.total_count == 2
        assert len(result.updates) == 2
        first, second = result.updates[0].comment, result.updates[1].comment
        assert first is not None and second is not None
        assert first.body == "newer"
        assert second.body == "older"

    def test_comments_property_reverses_order(self) -> None:
        update1 = self._make_update_entry(comment_text="newer", sequence=1)
        update2 = self._make_update_entry(comment_text="older", sequence=0)

        response_data = [["b.ListIssueUpdatesResponse", [[update1, update2], None, 2]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_updates_response(raw)
        comments = result.comments
        assert comments[0].body == "older"
        assert comments[1].body == "newer"

    def test_field_change_only_updates(self) -> None:
        update = self._make_update_entry(
            field_changes=[["status", None, None, None]],
        )

        response_data = [["b.ListIssueUpdatesResponse", [[update], None, 1]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_updates_response(raw)
        assert len(result.updates) == 1
        assert result.updates[0].comment is None
        assert len(result.updates[0].field_changes) == 1
        assert result.updates[0].field_changes[0].field == "status"

    def test_parses_attachments(self) -> None:
        attachments = [
            [
                64413762,
                "application/octet-stream",
                None,
                "deleted",
                ["attachment:407328533:64413762"],
                [],
                "TkRBM016STROVE16TFRZME5ERXpOell5TFRFME9UTTJOVEUxTmpRPQ\\u003d\\u003d",
                None,
                None,
                [[1]],
                None,
                None,
                407328533,
            ],
            [
                64413763,
                "video/mp4",
                332301,
                "chrome_2025-03-30_19-51-07.mp4",
                ["attachment:407328533:64413763"],
                [],
                "TkRBM016STROVE16TFRZME5ERXpOell6TFRFeE1qSTJOek16TkRFPQ\\u003d\\u003d",
                None,
                None,
                [[1]],
                None,
                None,
                407328533,
            ],
        ]
        update = self._make_update_entry(
            issue_id=407328533,
            attachments=attachments,
        )

        response_data = [["b.ListIssueUpdatesResponse", [[update], None, 1]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_updates_response(raw)

        parsed = result.updates[0].attachments
        assert parsed is not None
        assert parsed == [
            Attachment(
                issue_id=407328533,
                id=64413762,
                mime_type="application/octet-stream",
                size=None,
                filename="deleted",
                restriction=AttachmentRestriction.NO_RESTRICTION,
            ),
            Attachment(
                issue_id=407328533,
                id=64413763,
                mime_type="video/mp4",
                size=332301,
                filename="chrome_2025-03-30_19-51-07.mp4",
                restriction=AttachmentRestriction.NO_RESTRICTION,
            ),
        ]

    def test_parses_attachment_restrictions(self) -> None:
        attachments = [
            [
                52928287,
                "video/mp4",
                937910,
                "Chrome File URL.mp4",
                ["attachment:40068570:52928287"],
                [],
                None,
                None,
                None,
                [[3]],
                None,
                1,
                40068570,
            ],
            [
                52928288,
                "video/mp4",
                668191,
                "Chrome Links.mp4",
                ["attachment:40068570:52928288"],
                [],
                None,
                None,
                None,
                [[2]],
                None,
                1,
                40068570,
            ],
            [
                52928289,
                "text/plain",
                578,
                "PufIndex.html",
                ["attachment:40068570:52928289"],
                [],
                None,
                None,
                None,
                [[1]],
                None,
                None,
                40068570,
            ],
        ]
        update = self._make_update_entry(
            issue_id=40068570,
            attachments=attachments,
        )
        response_data = [["b.ListIssueUpdatesResponse", [[update], None, 1]]]

        result = parse_updates_response(XSSI_PREFIX + json.dumps(response_data))

        parsed = result.updates[0].attachments
        assert parsed is not None
        assert parsed[0].restriction is AttachmentRestriction.RESTRICTED_PLUS
        assert parsed[1].restriction is AttachmentRestriction.RESTRICTED
        assert parsed[2].restriction is AttachmentRestriction.NO_RESTRICTION

    def test_updates_without_attachments_return_none(self) -> None:
        update = self._make_update_entry()
        response_data = [["b.ListIssueUpdatesResponse", [[update], None, 1]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_updates_response(raw)

        assert result.updates[0].attachments is None

    def test_pagination(self) -> None:
        response_data = [["b.ListIssueUpdatesResponse", [[], "page2_token", 50]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_updates_response(raw)
        assert result.has_more is True
        assert result.next_page_token == "page2_token"
        assert result.total_count == 50

    def test_empty_updates(self) -> None:
        response_data: list[list[Any]] = [["b.ListIssueUpdatesResponse", [[], None, 0]]]
        raw = XSSI_PREFIX + json.dumps(response_data)

        result = parse_updates_response(raw)
        assert result.updates == []
        assert result.total_count == 0
        assert result.has_more is False
