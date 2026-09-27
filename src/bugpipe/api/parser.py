import json
import re
from datetime import UTC, datetime
from typing import Any

from ..api.models import (
    CUSTOM_FIELD_IDS,
    Attachment,
    AttachmentRestriction,
    Comment,
    CommentsResult,
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

_RESPONSE_PREFIX = re.compile(r"^\)\]\}'(\\n|\r?\n)")


def __strip_response_prefix(raw_text: str) -> str:
    """
    Remove the )]}' anti-XSSI prefix that the API prepends to all JSON responses.

    :param raw_text: Raw response body from the API.
    :return: The response body with the prefix stripped, ready for json.loads().
    """

    return _RESPONSE_PREFIX.sub("", raw_text, count=1)


def __parse_json_response(raw_text: str) -> Any:
    """
    Strip the anti-XSSI prefix and parse the JSON body.

    :param raw_text: Raw response body from the API.
    :return: The parsed JSON (usually a nested list).
    """

    return json.loads(__strip_response_prefix(raw_text))


def __get(array: Any, *indices: int, default=None) -> Any:
    """
    Safely traverse nested arrays/lists by index.

    :param array: The root array to traverse.
    :param indices: One or more integer indices to follow.
    :param default: Value to return if any index is out of bounds.
    :return: The value at the given path, or default if not reachable.
    """

    current = array
    for index in indices:
        try:
            current = current[index]
        except (IndexError, TypeError, KeyError):
            return default
    return current


def __parse_timestamp(raw_timestamp: Any) -> datetime | None:
    """
    Parse a [seconds, nanos] timestamp array into a UTC datetime.

    :param raw_timestamp: A list like [1657579144] or [1657579144, 285000000].
    :return: A timezone-aware UTC datetime, or None if unparseable.
    """

    if (
        not raw_timestamp
        or not isinstance(raw_timestamp, list)
        or len(raw_timestamp) < 1
    ):
        return None
    try:
        seconds = raw_timestamp[0]
        nanos = raw_timestamp[1] if len(raw_timestamp) > 1 else 0
        return datetime.fromtimestamp(seconds + nanos / 1e9, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def __parse_email(user_array: Any) -> str | None:
    """
    Extract an email address from a user field array.

    User fields look like [null, "user@example.com", 1, [...]].
    We find the first string that looks like an email.

    :param user_array: A list representing a user, or None.
    :return: The email address, or None if not found.
    """

    if not user_array or not isinstance(user_array, list):
        return None
    for item in user_array:
        if isinstance(item, str) and "@" in item:
            return item
    return None


def __parse_ccs(raw_ccs: Any) -> list[str]:
    """
    Parse a CC list where each entry is a user array like [null, "email", type].

    :param raw_ccs: List of user arrays.
    :return: List of email addresses.
    """

    if not raw_ccs or not isinstance(raw_ccs, list):
        return []
    return [email for entry in raw_ccs if (email := __parse_email(entry))]


def __parse_int_list(raw_list: Any) -> list[int]:
    """
    Extract integers from a list, ignoring non-int values.

    :param raw_list: A list that should contain integers (e.g. hotlist IDs).
    :return: Only the integer values from the list.
    """

    if not raw_list or not isinstance(raw_list, list):
        return []
    return [item for item in raw_list if isinstance(item, int)]


def __parse_custom_field_values(raw_field_entries: Any) -> dict[str, Any]:
    """
    Parse custom field value entries from the issue details array at [2][14].

    Each entry is an array like::

        [field_id, null, null, null, numeric_val?, label_values?,
         null, enum_values?, null, display_string, ...]

    The field_id is looked up in CUSTOM_FIELD_IDS to get a canonical name.
    Unknown fields get a ``field_{id}`` name.

    :param raw_field_entries: List of custom field arrays from the API.
    :return: Mapping of field names to their parsed values. Values are
        list[str] for multi-value fields, float for numeric fields,
        or str for single-value text fields.
    """

    if not raw_field_entries or not isinstance(raw_field_entries, list):
        return {}

    parsed_fields: dict[str, Any] = {}
    for entry in raw_field_entries:
        if not isinstance(entry, list) or len(entry) < 1:
            continue

        field_id = entry[0]
        field_name = CUSTOM_FIELD_IDS.get(field_id, f"field_{field_id}")

        display_string = __get(entry, 9)

        # Numeric value at index 4.
        numeric_value = __get(entry, 4)
        if isinstance(numeric_value, (int, float)):
            parsed_fields[field_name] = numeric_value
            continue

        for index in (5, 7):
            values = __get(entry, index)
            if not isinstance(values, list):
                continue
            flat_values = []
            for group in values:
                if isinstance(group, list):
                    flat_values.extend(s for s in group if isinstance(s, str))
                elif isinstance(group, str):
                    flat_values.append(group)
            if flat_values:
                parsed_fields[field_name] = flat_values
                break
        else:
            if display_string and isinstance(display_string, str):
                parsed_fields[field_name] = display_string

    return parsed_fields


def __parse_issue_from_entry(raw_entry: list) -> Issue:
    """
    Parse a single issue from the 48-element array format used across all endpoints.

    This is the core parser. Every endpoint (search, get, batch) ultimately
    produces these 48-element arrays, just nested at different paths.

    Array index map::

        Top-level (48 elements):
          [1]  = issue ID (int)
          [2]  = details array (32 elements, see below)
          [4]  = created timestamp [seconds, nanos]
          [5]  = modified timestamp [seconds, nanos]
          [6]  = verified timestamp [seconds, nanos]
          [9]  = star count (int or None)
          [10] = unknown constant (always 3)
          [11] = comment count (int)
          [13] = owner user array
          [14] = custom field definitions (schema, not values)
          [34] = last substantive activity timestamp [seconds, nanos]
          [36] = blocking issue IDs (list of ints)
          [41] = tracker ID (int)
          [46] = view counts [24h, 7d, 30d] (empty list = 0 views)
          [47] = last modifier user array

        Details array [2] (32 elements):
          [0]  = component ID (int)
          [1]  = issue type (int, maps to IssueType enum)
          [2]  = status (int, maps to Status enum)
          [3]  = priority (int, 1-indexed: P0=1, P1=2, P2=3, P3=4, P4=5)
          [4]  = severity (int, 1-indexed: S0=1, S1=2, S2=3, S3=4, S4=5)
          [5]  = title (str)
          [6]  = reporter user array
          [7]  = verifier user array
          [9]  = CCs list (list of user arrays)
          [13] = hotlist IDs (list of ints)
          [14] = custom field values (list of field arrays)
          [16] = found_in versions (list of strings)
          [19] = in_prod flag (True = yes, None = no)
          [21] = duplicate issue IDs (list of ints)
          [30] = collaborators (list of user arrays)

    :param raw_entry: The 48-element array representing one issue.
    :return: A fully populated Issue dataclass.
    """

    issue_id = __get(raw_entry, 1, default=0)
    details = __get(raw_entry, 2, default=[]) or []

    # --- Details array fields ---
    component_id = __get(details, 0)
    issue_type_detail = __get(details, 1)
    status_value = __get(details, 2, default=1)
    priority_raw = __get(details, 3, default=3)  # 1-indexed: P0=1, P1=2, ...
    # Convert 1-indexed API priority to 0-indexed enum (P0=0, P1=1, ...)
    priority_value = (priority_raw - 1) if isinstance(priority_raw, int) else 2
    severity_raw = __get(details, 4)  # 1-indexed: S0=1, S1=2, ...
    title = __get(details, 5, default="") or ""
    reporter_array = __get(details, 6)
    verifier_array = __get(details, 7)
    ccs_array = __get(details, 9)
    hotlist_ids_array = __get(details, 13)
    custom_field_entries = __get(details, 14)
    found_in_raw = __get(details, 16)
    in_prod_raw = __get(details, 19)
    duplicate_ids_array = __get(details, 21)
    collaborators_array = __get(details, 30)

    # --- Top-level fields ---
    created_timestamp = __get(raw_entry, 4)
    modified_timestamp = __get(raw_entry, 5)
    verified_timestamp = __get(raw_entry, 6)
    last_activity_timestamp = __get(raw_entry, 34)
    star_count = __get(raw_entry, 9, default=0)
    if not isinstance(star_count, int):
        star_count = 0
    comment_count = __get(raw_entry, 11, default=0) or 0
    owner_array = __get(raw_entry, 13)
    blocking_ids_array = __get(raw_entry, 36)
    body_array = __get(raw_entry, 43)
    body = body_array[0] if isinstance(body_array, list) and body_array else None
    tracker_id = __get(raw_entry, 41)
    views_array = __get(raw_entry, 46, default=[]) or []
    last_modifier_array = __get(raw_entry, 47)

    # --- Parse custom fields into a mutable dict, then pop known ones ---
    custom_fields = __parse_custom_field_values(custom_field_entries)

    def pop_string_list(key: str) -> list[str]:
        """
        Pop a key from custom_fields and return it as a list of strings.
        """

        value = custom_fields.pop(key, None)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return []

    def pop_string(key: str) -> str | None:
        """
        Pop a key from custom_fields and return it as a single string.
        """

        value = custom_fields.pop(key, None)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    def pop_float(key: str) -> float | None:
        """
        Pop a key from custom_fields and return it as a float.
        """

        value = custom_fields.pop(key, None)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    # Parse severity (1-indexed like priority: S0=1, S1=2, ...)
    severity_value = None
    if isinstance(severity_raw, int):
        severity_value = Severity(severity_raw - 1)

    # Parse found_in version strings
    found_in: list[str] = []
    if isinstance(found_in_raw, list):
        found_in = [v for v in found_in_raw if isinstance(v, str)]

    # Parse in_prod flag (True = yes, None = no)
    in_prod = True if in_prod_raw is True else None

    # Parse view counts [24h, 7d, 30d]
    views_24h, views_7d, views_30d = (
        (
            views_array[index]
            if isinstance(views_array, list)
            and len(views_array) > index
            and isinstance(views_array[index], int)
            else 0
        )
        for index in range(3)
    )

    return Issue(
        id=issue_id,
        title=title,
        status=Status(status_value) if status_value else Status.NEW,
        priority=Priority(priority_value),
        severity=severity_value,
        issue_type=IssueType(issue_type_detail) if issue_type_detail else None,
        reporter=__parse_email(reporter_array),
        owner=__parse_email(owner_array),
        verifier=__parse_email(verifier_array),
        component_id=component_id,
        ccs=__parse_ccs(ccs_array),
        collaborators=__parse_ccs(collaborators_array),
        found_in=found_in,
        in_prod=in_prod,
        created_at=__parse_timestamp(created_timestamp),
        modified_at=__parse_timestamp(modified_timestamp),
        verified_at=__parse_timestamp(verified_timestamp),
        last_activity_at=__parse_timestamp(last_activity_timestamp),
        comment_count=comment_count,
        star_count=star_count,
        body=body,
        tracker_id=tracker_id,
        last_modifier=__parse_email(last_modifier_array),
        hotlist_ids=__parse_int_list(hotlist_ids_array),
        blocking_issue_ids=__parse_int_list(blocking_ids_array),
        duplicate_issue_ids=__parse_int_list(duplicate_ids_array),
        views_24h=views_24h,
        views_7d=views_7d,
        views_30d=views_30d,
        component_tags=pop_string_list("component_tags"),
        component_ancestor_tags=pop_string_list("component_ancestor_tags"),
        labels=pop_string_list("chromium_labels"),
        os=pop_string_list("os"),
        milestone=pop_string_list("milestone"),
        merge=pop_string_list("merge"),
        merge_request=pop_string_list("merge_request"),
        release_block=pop_string_list("release_block"),
        cve=pop_string_list("cve"),
        cwe_id=pop_float("cwe_id"),
        vrp_reward=pop_float("vrp_reward"),
        estimated_days=pop_float("estimated_days"),
        build_number=pop_string("build_number"),
        flaky_test=pop_string("flaky_test"),
        next_action=pop_string("next_action"),
        notice=pop_string("notice"),
        introduced_in=pop_string("introduced_in"),
        irm_link=pop_string("irm_link"),
        security_release=pop_string_list("security_release"),
        fixed_by_code_changes=pop_string_list("fixed_by_code_changes"),
        custom_fields=custom_fields,
    )


def __parse_search_response(
    raw_text: str,
    query: str = "",
    page_size: int = 50,
) -> SearchResult:
    """
    Parse a search/list response.

    Response shape::

        [["b.IssueSearchResponse", ..., [issues, page_token, total_count]]]

    Issues at ``[0][6][0]``, pagination token at ``[0][6][1]``,
    total count at ``[0][6][2]``.

    :param raw_text: Raw response body from POST /action/issues/list.
    :param query: The query string used (stored on the result for pagination).
    :param page_size: The page size used (stored on the result for pagination).
    :return: Parsed issues with pagination info.
    """

    data = __parse_json_response(raw_text)

    response_wrapper = __get(data, 0, default=[])
    result_block = __get(response_wrapper, 6, default=[])

    raw_issues = __get(result_block, 0, default=[]) or []
    page_token = __get(result_block, 1)
    total_count = __get(result_block, 2, default=0) or 0

    issues = Results(
        __parse_issue_from_entry(entry)
        for entry in raw_issues
        if isinstance(entry, list)
    )

    return SearchResult(
        issues=issues,
        total_count=total_count,
        next_page_token=page_token if page_token else None,
        query=query,
        page_size=page_size,
    )


def __parse_issue_detail_response(raw_text: str) -> Issue:
    """
    Parse a getIssue response.

    Response shape::

        [["b.IssueFetchResponse", [<23-element payload>]]]

    The 48-element issue entry is at ``data[0][1][22]``
    (last element of the payload).

    :param raw_text: Raw response body from POST /action/issues/{id}/getIssue.
    :return: The fully parsed issue.
    :raises ValueError: If the issue entry can't be located in the response.
    """

    data = __parse_json_response(raw_text)

    response_wrapper = __get(data, 0, default=[])
    payload = __get(response_wrapper, 1, default=[])

    issue_entry = next(
        (
            candidate
            for candidate in reversed(payload if isinstance(payload, list) else [])
            if isinstance(candidate, list) and isinstance(__get(candidate, 1), int)
        ),
        None,
    )

    if issue_entry is None:
        raise ValueError("Could not locate issue entry in getIssue response")

    return __parse_issue_from_entry(issue_entry)


def __parse_batch_response(raw_text: str) -> Results[Issue]:
    """
    Parse a batch get response.

    Response shape::

        [["b.BatchGetIssuesResponse", null, [[issue1, issue2, ...]]]]

    Each issue at ``data[0][2][0][i]`` is a standard 48-element array.

    :param raw_text: Raw response body from POST /action/issues/batch.
    :return: List of parsed issues.
    """

    data = __parse_json_response(raw_text)

    response_wrapper = __get(data, 0, default=[])
    entries_wrapper = __get(response_wrapper, 2, default=[])
    raw_issues = __get(entries_wrapper, 0, default=[]) or []

    return Results(
        __parse_issue_from_entry(entry)
        for entry in raw_issues
        if isinstance(entry, list) and isinstance(__get(entry, 1), int)
    )


def __parse_field_changes(raw_changes: Any) -> list[FieldChange]:
    """
    Parse field change entries from an update's changes array.

    Each change looks like ``["field_name", null, old_value_wrapper, new_value_wrapper]``.
    We currently only extract the field name.

    :param raw_changes: The field changes array from an update entry.
    :return: List of parsed field changes.
    """

    if not raw_changes or not isinstance(raw_changes, list):
        return []
    changes = []
    for entry in raw_changes:
        if not isinstance(entry, list) or len(entry) < 1:
            continue
        field_name = entry[0] if isinstance(entry[0], str) else str(entry[0])
        changes.append(FieldChange(field=field_name))
    return changes


def __parse_attachments(raw_attachments: Any, issue_id: int) -> list[Attachment] | None:
    """
    Parse attachment entries from an issue update.

    The API returns attachment metadata as nested arrays. The attachment ID,
    MIME type, size, and filename are at indices 0 through 3. The restriction
    level is stored at ``[9][0][0]``.

    :param raw_attachments: The raw attachment array from an update entry.
    :param issue_id: The parent issue ID.
    :return: Parsed attachments, or ``None`` when no attachments are present.
    """

    if not raw_attachments or not isinstance(raw_attachments, list):
        return None

    attachments: list[Attachment] = []

    for raw_attachment in raw_attachments:
        attachment_id = __get(raw_attachment, 0)
        mime_type = __get(raw_attachment, 1)
        size = __get(raw_attachment, 2)
        filename = __get(raw_attachment, 3)
        restriction = AttachmentRestriction(__get(raw_attachment, 9, 0, 0))

        attachments.append(
            Attachment(
                issue_id=issue_id,
                id=attachment_id,
                mime_type=mime_type,
                size=size,
                filename=filename,
                restriction=restriction,
            )
        )

    return attachments


def __parse_comment(
    raw_comment: Any, issue_id: int, number_offset: int = 1
) -> Comment | None:
    """
    Parse a comment body array (19 elements) into a Comment.

    Comment array index map::

        [0]  = comment text (str)
        [2]  = author user array
        [3]  = last-modified timestamp [seconds, nanos]
        [5]  = issue ID (int)
        [6]  = comment sequence number
        [17] = last editor user array (equals author if never edited)
        [18] = creation timestamp [seconds, nanos] (equals [3] if never edited)

    :param raw_comment: The 19-element comment array from an update entry.
    :param issue_id: The issue ID this comment belongs to.
    :param number_offset: Added to the raw sequence number. The /updates
        endpoint is 0-indexed (pass 1), /listComments is already 1-indexed
        (pass 0).
    :return: The parsed comment, or None if raw_comment is invalid.
    """

    if not raw_comment or not isinstance(raw_comment, list):
        return None

    comment_text = __get(raw_comment, 0, default="") or ""
    author_array = __get(raw_comment, 2)
    timestamp_array = __get(raw_comment, 3)
    sequence_number = __get(raw_comment, 6, default=0) or 0
    last_editor_array = __get(raw_comment, 17)
    created_array = __get(raw_comment, 18)

    return Comment(
        issue_id=issue_id,
        comment_number=sequence_number + number_offset,
        author=__parse_email(author_array),
        timestamp=__parse_timestamp(timestamp_array),
        created_at=__parse_timestamp(created_array),
        body=comment_text,
        last_editor=__parse_email(last_editor_array),
    )


def __parse_updates_response(raw_text: str) -> IssueUpdatesResult:
    """
    Parse a ListIssueUpdatesResponse (comments + field changes).

    Response shape::

        [["b.ListIssueUpdatesResponse", [[update, ...], page_token, total_count]]]

    Each update is a 10-element array::

        [0] = author user array
        [1] = timestamp [seconds, nanos]
        [2] = comment body (19-element array) or None
        [3] = update sequence number
        [5] = field changes array
        [6] = comment number (descending in response order)
        [9] = issue ID

    Updates are returned newest-first. Use ``.comments`` on the result to get
    comments in chronological order.

    :param raw_text: Raw response body from POST /action/issues/{id}/updates.
    :return: Parsed updates with pagination info.
    """

    data = __parse_json_response(raw_text)

    response_wrapper = __get(data, 0, default=[])
    result_block = __get(response_wrapper, 1, default=[])

    raw_updates = __get(result_block, 0, default=[]) or []
    page_token = __get(result_block, 1)
    total_count = __get(result_block, 2, default=0) or 0

    updates: Results[IssueUpdate] = Results()
    for update_entry in raw_updates:
        if not isinstance(update_entry, list):
            continue

        issue_id = __get(update_entry, 9, default=0) or 0
        author_array = __get(update_entry, 0)
        timestamp_array = __get(update_entry, 1)
        comment_array = __get(update_entry, 2)
        sequence_number = __get(update_entry, 3)
        changes_array = __get(update_entry, 5)
        attachments_array = __get(update_entry, 7)

        comment = __parse_comment(comment_array, issue_id) if comment_array else None
        attachments = __parse_attachments(attachments_array, issue_id)

        updates.append(
            IssueUpdate(
                issue_id=issue_id,
                sequence_number=sequence_number,
                author=__parse_email(author_array),
                timestamp=__parse_timestamp(timestamp_array),
                comment=comment,
                field_changes=__parse_field_changes(changes_array),
                attachments=attachments,
            )
        )

    return IssueUpdatesResult(
        updates=updates,
        total_count=total_count,
        next_page_token=page_token if page_token else None,
    )


def __parse_comments_response(raw_text: str) -> CommentsResult:
    """
    Parse a ListIssueCommentsResponse.

    Response shape::

        [["b.ListIssueCommentsResponse", [[comment, ...], page_token, total_count]]]

    Each comment is a 19-element array. Unlike the ``/updates`` endpoint,
    sequence numbers here are **1-indexed** (no ``+1`` adjustment needed).

    :param raw_text: Raw response body from POST /action/issues/{id}/listComments.
    :return: Parsed comments with pagination info.
    """

    data = __parse_json_response(raw_text)

    response_wrapper = __get(data, 0, default=[])
    result_block = __get(response_wrapper, 1, default=[])

    raw_comments = __get(result_block, 0, default=[]) or []
    page_token = __get(result_block, 1)
    total_count = __get(result_block, 2, default=0) or 0

    comments: Results[Comment] = Results()
    for raw_comment in raw_comments:
        # /listComments sequence numbers are already 1-indexed, so no offset.
        issue_id = __get(raw_comment, 5, default=0) or 0
        comment = __parse_comment(raw_comment, issue_id, number_offset=0)
        if comment is not None:
            comments.append(comment)

    return CommentsResult(
        comments=comments,
        total_count=total_count,
        next_page_token=page_token if page_token else None,
    )
