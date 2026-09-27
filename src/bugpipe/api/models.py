"""
Data models for the Google Issue Tracker.

Every model here carries the fields the API sends, and writes itself out::

    with Bugpipe() as client:
        issues = client.issues([40060244, 486077869])

        issues.to_csv("issues.csv")        # one row per issue
        issues[0].to_json("issue.json")    # one object
        issues[0].to_dict()                # the fields as a plain dict

A read that hands back several items hands back a :class:`Results` list, which
writes itself out the same way one item does.
"""

import csv
import enum
import json
import typing as t
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from pathlib import Path

__all__ = [
    "CUSTOM_FIELD_IDS",
    "Attachment",
    "AttachmentRestriction",
    "Comment",
    "CommentsResult",
    "CustomFieldValue",
    "Exportable",
    "FieldChange",
    "Issue",
    "IssueType",
    "IssueUpdate",
    "IssueUpdatesResult",
    "Priority",
    "Results",
    "SearchResult",
    "Severity",
    "Status",
    "UnquotedValue",
]


class UnquotedValue(str):
    """
    One field value that prints as itself, without the quotes a string carries.

    An enum name and a timestamp are values, not prose, so they read better
    unquoted: ``status=FIXED``, not ``status='FIXED'``.
    """

    def __repr__(self) -> str:
        return str(self)


def _for_console(value: t.Any) -> t.Any:
    """
    Swap a single field value for how it reads on screen.

    An enum shows its name rather than its numeric repr, and a datetime its
    ISO form rather than the constructor call, both unquoted.

    :param value: A field value.
    :return: The readable form of the value.
    """

    if isinstance(value, enum.Enum):
        return UnquotedValue(value.name)
    if isinstance(value, datetime):
        return UnquotedValue(value.isoformat())
    return value


def _for_file(value: t.Any) -> t.Any:
    """
    Reduce a field value to something JSON and CSV can both hold.

    Enums become their names, datetimes their ISO form, and nested
    dataclasses, lists, and dicts are converted item by item.

    :param value: A field value.
    :return: The plain form of the value.
    """

    if isinstance(value, enum.Enum):
        return value.name
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _for_file(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {key: _for_file(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_for_file(item) for item in value]
    return value


def _writable_path(path: str) -> Path:
    """
    Make the parent directory of an output path when it is missing.

    :param path: Output file path.
    :return: The path, ready to write to.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _write_json(path: str, data: t.Any, indent: int) -> str:
    """
    Write ``data`` to a JSON file and return the path written.

    :param path: Output file path. Missing parent directories are made.
    :param data: JSON-serialisable value.
    :param indent: Spaces to indent by. ``0`` writes it on one line.
    :return: The path written.
    """

    target = _writable_path(path)
    target.write_text(
        json.dumps(data, indent=indent or None, ensure_ascii=False), encoding="utf-8"
    )
    return str(target)


class Exportable:
    """
    Writes a dataclass out as a dict, or to a JSON or CSV file, and prints it
    with its enums and timestamps read as text.

    Only the dataclass's own fields are covered; properties such as
    :attr:`Issue.url` are left out.
    """

    __dataclass_fields__: t.ClassVar[dict[str, t.Any]]

    def __rich_repr__(self) -> t.Iterator[tuple[str, t.Any]]:
        for f in fields(self):
            yield f.name, _for_console(getattr(self, f.name))

    def to_dict(self) -> dict[str, t.Any]:
        """
        Return the item's fields as a plain dict.

        :return: Every field, with enums, datetimes, and nested dataclasses
            reduced to plain values.
        """

        return {f.name: _for_file(getattr(self, f.name)) for f in fields(self)}

    def to_json(self, path: str, indent: int = 4) -> str:
        """
        Write the item to a JSON file as one object.

        :param path: Output file path. Missing parent directories are made.
        :param indent: Spaces to indent by. ``0`` writes it on one line.
        :return: The path written.
        """

        return _write_json(path=path, data=self.to_dict(), indent=indent)

    def to_csv(self, path: str) -> str:
        """
        Write the item to a CSV file as one row.

        :param path: Output file path. Missing parent directories are made.
        :return: The path written.
        """

        return Results([self]).to_csv(path)


class Results[T: Exportable](list[T]):
    """
    The list of items a read hands back. It writes itself out the way one item does.

    It is a plain list, so it indexes, slices, and iterates as always. It just
    also carries :meth:`to_dict`, :meth:`to_json`, and :meth:`to_csv`::

        issues = client.issues([40060244, 486077869])

        issues.to_csv("issues.csv")
        issues[0].to_json("first.json")
    """

    @staticmethod
    def _as_cell(value: t.Any) -> t.Any:
        """
        Make one value fit in a CSV cell.

        A cell holds text, so nested lists and dicts go in as JSON rather than
        as a Python repr, which keeps them readable by whatever opens the file next.

        :param value: A field value.
        :return: The value, or its JSON form when it nests.
        """

        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return value

    def to_dict(self) -> list[dict[str, t.Any]]:
        """
        Return the items as a list of plain dicts.

        :return: One dict of fields per item.
        """

        return [item.to_dict() for item in self]

    def to_json(self, path: str, indent: int = 4) -> str:
        """
        Write the items to a JSON file as one array.

        :param path: Output file path. Missing parent directories are made.
        :param indent: Spaces to indent by. ``0`` writes it on one line.
        :return: The path written.
        """

        return _write_json(path=path, data=self.to_dict(), indent=indent)

    def to_csv(self, path: str) -> str:
        """
        Write the items to a CSV file, one row each.

        The columns are the union of every row's keys, in the order they were
        first seen, since items of the same kind can still carry different fields.

        :param path: Output file path. Missing parent directories are made.
        :return: The path written.
        """

        target = _writable_path(path)
        rows = self.to_dict()

        fieldnames = list(dict.fromkeys(key for row in rows for key in row))

        with target.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {key: self._as_cell(value) for key, value in row.items()}
                )
        return str(target)


class _LenientIntEnum(enum.IntEnum):
    """
    IntEnum that synthesises a member for values the API sends but we don't know.

    The member is named ``<prefix><value>``, where subclasses set the prefix.
    """

    _unknown_prefix = enum.nonmember("UNKNOWN_")

    @classmethod
    def _missing_(cls, value):
        """
        Build a pseudo-member for an unknown value instead of raising.

        :param value: Numeric value returned by the API.
        :return: A new member named ``<prefix><value>``.
        """

        value = t.cast(int, value)
        # noinspection PyTypeChecker
        obj = int.__new__(cls, value)
        obj._name_ = f"{cls._unknown_prefix}{value}"
        obj._value_ = value
        return obj


class Status(_LenientIntEnum):
    """
    Issue status values used by the Google Issue Tracker.

    The first three (NEW, ASSIGNED, ACCEPTED) are considered open.
    Everything else is a closed/resolved state. Unknown values from
    the API get an auto-generated UNKNOWN_N name instead of crashing.
    """

    NEW = 1
    ASSIGNED = 2
    ACCEPTED = 3
    FIXED = 4
    VERIFIED = 5
    NOT_REPRODUCIBLE = 6
    INTENDED_BEHAVIOR = 7
    OBSOLETE = 8
    INFEASIBLE = 9
    DUPLICATE = 10

    @property
    def is_open(self) -> bool:
        """
        Whether this status represents an open (unresolved) issue.
        """

        return self in (Status.NEW, Status.ASSIGNED, Status.ACCEPTED)


class Priority(_LenientIntEnum):
    """
    Issue priority levels. P0 is the most urgent, P4 is the lowest.

    Unknown values from the API get an auto-generated PN name.
    """

    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

    _unknown_prefix = enum.nonmember("P")


class Severity(_LenientIntEnum):
    """
    Issue severity levels. S0 is the most severe, S4 is the lowest.

    Severity often matches priority but can diverge, especially on
    security issues. Unknown values from the API get an auto-generated SN name.
    """

    S0 = 0
    S1 = 1
    S2 = 2
    S3 = 3
    S4 = 4

    _unknown_prefix = enum.nonmember("S")


class IssueType(_LenientIntEnum):
    """
    Issue type categories.

    Unknown values from the API get an auto-generated TYPE_N name.
    """

    BUG = 1
    FEATURE_REQUEST = 2
    CUSTOMER_ISSUE = 3
    INTERNAL_CLEANUP = 4
    PROCESS = 5
    VULNERABILITY = 6

    _unknown_prefix = enum.nonmember("TYPE_")


class AttachmentRestriction(_LenientIntEnum):
    """
    Access restriction levels for issue attachments.

    ``NO_RESTRICTION`` allows users with issue-view permission to access the
    attachment. ``RESTRICTED`` and ``RESTRICTED_PLUS`` require the respective
    restricted-content permission.

    Unknown values from the API get an auto-generated UNKNOWN_N name.
    """

    NO_RESTRICTION = 1
    RESTRICTED = 2
    RESTRICTED_PLUS = 3


# Maps numeric custom field IDs to human-readable names.
# These are the 24 well-known fields in the Chromium tracker (tracker 157).
# Other trackers may use different field IDs; unrecognized fields go to custom_fields.
# The parser uses this to turn raw field IDs into named attributes.
CUSTOM_FIELD_IDS: dict[int, str] = {
    1225362: "backlog_rank",
    1223033: "build_number",
    1223031: "chromium_labels",
    1222907: "component_tags",
    1223136: "cve",
    1410892: "cwe_id",
    1223032: "design_doc",
    1223131: "design_summary",
    1225337: "estimated_days",
    1223081: "flaky_test",
    1223087: "merge",
    1223134: "merge_request",
    1223085: "milestone",
    1225154: "next_action",
    1223083: "notice",
    1223084: "os",
    1223086: "release_block",
    1223034: "respin",
    1300460: "irm_link",
    1223088: "security_release",
    1223135: "vrp_reward",
    1358989: "fixed_by_code_changes",
    1253656: "component_ancestor_tags",
    1544844: "introduced_in",
}


@dataclass
class CustomFieldValue(Exportable):
    """
    A single custom field value that didn't map to a known attribute.

    Attributes:
        field_id: Numeric ID of the custom field.
        name: Human-readable name (from CUSTOM_FIELD_IDS or "field_N").
        values: String values for multi-value fields.
        numeric_value: Numeric value for number-type fields.
    """

    field_id: int
    name: str
    values: list[str] = field(default_factory=list)
    numeric_value: float | None = None


@dataclass
class Issue(Exportable):
    """
    A single issue from the Google Issue Tracker.

    Basic fields (id, title, status, priority, etc.) are always populated.
    Custom fields (os, milestone, cve, etc.) come from the tracker's
    configurable field system and may be empty.

    Attributes:
        id: Unique numeric issue ID.
        title: Issue title/summary.
        status: Current status (open, fixed, etc.).
        priority: Priority level (P0-P4).
        severity: Severity level (S0-S4). Often matches priority but can diverge.
        issue_type: Category (bug, feature request, etc.).
        reporter: Email of the person who filed the issue.
        owner: Email of the currently assigned owner.
        verifier: Email of the person who verified the fix.
        component_id: Numeric ID of the primary component.
        ccs: List of CC'd email addresses.
        collaborators: List of collaborator email addresses.
        found_in: "Found In" version strings (e.g. ["CP21.260116.011.A1"]).
        in_prod: Whether the issue has been observed in production.
        created_at: When the issue was created (UTC).
        modified_at: When the issue was last modified (UTC). Also moves on
            automated metadata churn (hotlist/custom-field bot updates).
        verified_at: When the fix was verified (UTC).
        last_activity_at: When the issue last had a substantive update (a
            comment or meaningful field change), excluding the automated
            metadata churn that bumps modified_at. May be None.
        comment_count: Total number of comments.
        star_count: Number of stars (watchers/votes).
        body: Issue description text. Only populated in batch/detail responses, not in search results.
        tracker_id: Tracker ID (e.g. 157 for Chromium, 183 for Fuchsia).
        last_modifier: Email of the last person to modify the issue.
        hotlist_ids: IDs of hotlists this issue belongs to.
        blocking_issue_ids: IDs of issues this one blocks.
        duplicate_issue_ids: IDs of issues marked as duplicates of this one.
        views_24h: Number of views in the last 24 hours.
        views_7d: Number of views in the last 7 days.
        views_30d: Number of views in the last 30 days.
        component_tags: Component tags (e.g. ["Blink>JavaScript"]).
        component_ancestor_tags: Full component ancestry.
        labels: Tracker-specific labels.
        os: Affected operating systems (e.g. ["Linux", "Mac", "Windows"]).
        milestone: Affected milestones.
        merge: Merge status labels.
        merge_request: Merge request labels.
        release_block: Release-blocking labels.
        cve: CVE identifiers.
        cwe_id: CWE weakness ID.
        vrp_reward: Bug bounty (VRP) reward amount.
        estimated_days: Estimated engineer-days to complete.
        build_number: Affected build number string.
        flaky_test: Flaky test identifier.
        next_action: Next expected action or deadline.
        notice: Notice text.
        introduced_in: Milestone the vulnerability was first introduced.
        irm_link: Link to related IRM incident.
        security_release: Security release labels.
        fixed_by_code_changes: Gerrit URLs of fixing code changes.
        custom_fields: Catch-all dict for any fields not mapped to attributes above.
    """

    id: int
    title: str
    status: Status = Status.NEW
    priority: Priority = Priority.P2
    severity: Severity | None = None
    issue_type: IssueType | None = None
    reporter: str | None = None
    owner: str | None = None
    verifier: str | None = None
    component_id: int | None = None
    ccs: list[str] = field(default_factory=list)
    collaborators: list[str] = field(default_factory=list)
    found_in: list[str] = field(default_factory=list)
    in_prod: bool | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    verified_at: datetime | None = None
    last_activity_at: datetime | None = None
    comment_count: int = 0
    star_count: int = 0
    body: str | None = None
    tracker_id: int | None = None
    last_modifier: str | None = None
    hotlist_ids: list[int] = field(default_factory=list)
    blocking_issue_ids: list[int] = field(default_factory=list)
    duplicate_issue_ids: list[int] = field(default_factory=list)
    views_24h: int = 0
    views_7d: int = 0
    views_30d: int = 0
    component_tags: list[str] = field(default_factory=list)
    component_ancestor_tags: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    os: list[str] = field(default_factory=list)
    milestone: list[str] = field(default_factory=list)
    merge: list[str] = field(default_factory=list)
    merge_request: list[str] = field(default_factory=list)
    release_block: list[str] = field(default_factory=list)
    cve: list[str] = field(default_factory=list)
    cwe_id: float | None = None
    vrp_reward: float | None = None
    estimated_days: float | None = None
    build_number: str | None = None
    flaky_test: str | None = None
    next_action: str | None = None
    notice: str | None = None
    introduced_in: str | None = None
    irm_link: str | None = None
    security_release: list[str] = field(default_factory=list)
    fixed_by_code_changes: list[str] = field(default_factory=list)
    custom_fields: dict[str, t.Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        """
        Direct link to this issue on issuetracker.google.com.
        """

        return f"https://issuetracker.google.com/issues/{self.id}"


@dataclass
class Comment(Exportable):
    """
    A single comment on an issue.

    Attributes:
        issue_id: The issue this comment belongs to.
        comment_number: 1-indexed comment number.
        author: Email of the comment author.
        timestamp: When the comment was last modified (UTC). Equals
            created_at when the comment has never been edited.
        created_at: When the comment was originally posted (UTC).
        body: The comment text.
        last_editor: Email of the last person to edit the comment. Equals
            author when the comment has never been edited.
    """

    issue_id: int
    comment_number: int
    author: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    body: str = ""
    last_editor: str | None = None

    @property
    def is_edited(self) -> bool:
        """
        Whether the comment has been edited since it was posted.

        True when the last-modified timestamp is later than the creation
        time (catches self-edits, where the author edits their own comment
        and stays the last_editor), or when a known last_editor differs
        from the author.
        """

        if self.created_at and self.timestamp and self.created_at != self.timestamp:
            return True
        return self.last_editor is not None and self.last_editor != self.author


@dataclass
class Attachment(Exportable):
    """
    A file attached to an issue update.

    Attributes:
        issue_id: The issue this attachment belongs to.
        id: The attachment ID.
        mime_type: The attachment MIME type.
        size: File size in bytes, or ``None`` after deletion.
        filename: The attachment filename.
        restriction: Access restriction level for the attachment.

    The API returns ``size=None`` after the attachment has been deleted.
    """

    issue_id: int
    id: int
    mime_type: str
    size: int | None
    filename: str
    restriction: AttachmentRestriction


@dataclass
class CommentsResult:
    """
    Result from fetching comments via the listComments endpoint.

    Attributes:
        comments: The comments for this page.
        total_count: Total number of text comments on this issue.
        next_page_token: Token for fetching the next page, if there are more.
    """

    comments: Results[Comment]
    total_count: int
    next_page_token: str | None = None

    @property
    def has_more(self) -> bool:
        """
        Whether there are more comments beyond this page.
        """

        return self.next_page_token is not None


@dataclass
class FieldChange(Exportable):
    """
    A single field change within an issue update.

    Attributes:
        field: Name of the changed field (e.g. "status", "priority").
        old_value: Previous value (not always available from the API).
        new_value: New value (not always available from the API).
    """

    field: str
    old_value: str | None = None
    new_value: str | None = None


@dataclass
class IssueUpdate(Exportable):
    """
    An issue update entry. May contain a comment, field changes, or both.

    Attributes:
        issue_id: The issue this update belongs to.
        sequence_number: Ordering number for this update.
        author: Email of the person who made this update.
        timestamp: When the update happened (UTC).
        comment: The comment attached to this update, if any.
        field_changes: List of field changes in this update.
        attachments: Attachments associated with this update, if any.
    """

    issue_id: int
    sequence_number: int | None = None
    author: str | None = None
    timestamp: datetime | None = None
    comment: Comment | None = None
    field_changes: list[FieldChange] = field(default_factory=list)
    attachments: list[Attachment] | None = None


@dataclass
class IssueUpdatesResult:
    """
    Result from fetching issue updates (comments + field changes).

    The API returns updates in reverse chronological order (newest first).
    Use the .comments property to get just the comments in chronological order.

    Attributes:
        updates: All updates, newest first.
        total_count: Total number of updates for this issue.
        next_page_token: Token for fetching the next page, if there are more.
    """

    updates: Results[IssueUpdate]
    total_count: int
    next_page_token: str | None = None

    @property
    def comments(self) -> Results[Comment]:
        """
        Only the updates that have comments, in chronological order (oldest first).
        """

        return Results(
            update.comment
            for update in reversed(self.updates)
            if update.comment is not None
        )

    @property
    def has_more(self) -> bool:
        """
        Whether there are more updates beyond this page.
        """

        return self.next_page_token is not None


@dataclass
class SearchResult:
    """
    Result from searching/listing issues.

    Attributes:
        issues: The matching issues for this page.
        total_count: Total number of matching issues (across all pages).
        next_page_token: Token for fetching the next page, if there are more.
        query: The query string used for this search (stored for pagination).
        page_size: The page size used for this search (stored for pagination).
    """

    issues: Results[Issue]
    total_count: int
    next_page_token: str | None = None
    query: str = ""
    page_size: int = 50

    @property
    def has_more(self) -> bool:
        """
        Whether there are more results beyond this page.
        """

        return self.next_page_token is not None
