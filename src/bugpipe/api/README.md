# Google Issue Tracker API reference

Bugpipe reads public Google Issue Tracker issues through the JSON API at
`https://issuetracker.google.com/action`. It sends requests without cookies
or authentication tokens.

This reference records the request formats and response fields found through
browser traffic and API tests. {doc}`AUDIT.md <audit>` contains further
observations and marks which were tested.

## Requests and headers

The base URL is `https://issuetracker.google.com/action`. Endpoint paths below
include `/action`.

Search, issue fetches, comments, and updates use POST with JSON arrays.
Components, trackers, hotlists, relationships, and the health check use GET.

| Header       | Value                              | POST | Resource GET |
|--------------|------------------------------------|------|--------------|
| Content-Type | `application/json`                 | Yes  | Omit         |
| Origin       | `https://issuetracker.google.com`  | Yes  | Yes          |
| Referer      | `https://issuetracker.google.com/` | Yes  | Yes          |
| User-Agent   | Browser or Googlebot user agent    | Yes  | Yes          |

Recorded resource GET requests returned HTTP 400 when sent with
`Content-Type: application/json`. Omit that header for those requests.

The Python client provides search, single and batch issue fetches, comments,
updates, and the health check. The other endpoints below describe direct HTTP
requests.

## Response prefix

JSON responses start with `)]}'` followed by a newline. Strip this prefix
before parsing the JSON:

```python
import json

clean = raw_text.removeprefix(")]}'\n")
data = json.loads(s=clean)
```

The parser also accepts the prefix followed by CRLF or a literal `\n`.
The health check returns plain text and has no prefix.

## Known trackers

The client's `TRACKERS` list contains these 14 trackers. The root component
IDs below come from the recorded API observations.

| Tracker ID | Name         | Root Component | Public URL                               |
|------------|--------------|----------------|------------------------------------------|
| `1`        | Pigweed      | 1194524        | https://issues.pigweed.dev               |
| `27`       | Gerrit       | 1370273        | https://issues.gerritcodereview.com      |
| `53`       | Git          | 1320275        | https://git.issues.gerritcodereview.com  |
| `79`       | Skia         | 1363359        | https://issues.skia.org                  |
| `105`      | WebRTC       | 1363538        | https://issues.webrtc.org                |
| `131`      | libyuv       | 1363539        | https://libyuv.issues.chromium.org       |
| `157`      | Chromium     | 1363614        | https://issues.chromium.org              |
| `183`      | Fuchsia      | 1360843        | https://issues.fuchsia.dev               |
| `235`      | ANGLE        | 853171         | https://issues.angleproject.org          |
| `261`      | AOMedia      | 1597128        | https://aomedia.issues.chromium.org      |
| `287`      | WebM         | 1615215        | https://issues.webmproject.org           |
| `339`      | GN           | 1636803        | https://gn.issues.chromium.org           |
| `365`      | Project Zero | 1638259        | https://project-zero.issues.chromium.org |
| `391`      | OSS Fuzz     | 1638179        | https://issues.oss-fuzz.com              |

Use `Bugpipe(trackers=None)` to search without a tracker filter, or pass names
or IDs such as `Bugpipe(trackers=["chromium", "fuchsia"])`. For direct tracker
lookups, pass the numeric ID to `/action/trackers/{id}`.

## Endpoints

### Search issues

```text
POST /action/issues/list
```

Request shape:

```text
[null, null, null, null, null, TRACKER_FILTER, QUERY_PAYLOAD]
```

| Position | Field          | Type                             | Value                                                                      |
|----------|----------------|----------------------------------|----------------------------------------------------------------------------|
| `[5]`    | tracker_filter | `list[str] \| null`              | `["157"]` for Chromium, `["157", "183"]` for both, or `null` for no filter |
| `[6][0]` | query          | `str`                            | Search query, such as `"status:open"`                                      |
| `[6][1]` | reserved       | `null`                           | Leave as `null`; recorded tests returned HTTP 400 for other values         |
| `[6][2]` | page_size      | `int`                            | 25, 50, 100, or 250                                                        |
| `[6][3]` | page_token     | `str`, omitted on the first page | Token from the previous response                                           |

Search all trackers:

```json
[null, null, null, null, null, null, ["status:open", null, 50]]
```

Fetch the next page for Chromium:

```json
[null, null, null, null, null, ["157"], ["status:open", null, 50, "SOME_PAGE_TOKEN"]]
```

### Get a single issue

```text
POST /action/issues/{issue_id}/getIssue
POST /action/issues/{issue_id}/getIssue?currentTrackerId={tracker_id}
```

Request shape:

```text
[ISSUE_ID, DETAIL_LEVEL, FLAG_2]
```

| Position | Field        | Type  | Value                                                                 |
|----------|--------------|-------|-----------------------------------------------------------------------|
| `[0]`    | issue_id     | `int` | Issue ID                                                              |
| `[1]`    | detail_level | `int` | Use `2` to include the body, links, and relationship graph            |
| `[2]`    | flag_2       | `int` | The client uses `1`; recorded tests with 0 through 10 found no change |

The client sends `[issue_id, 2, 1]` without `currentTrackerId`.
In the recorded tests, detail levels other than `2` left `TOP[37]`, `TOP[40]`,
and `TOP[43]` as `null`.

### Batch get issues

```text
POST /action/issues/batch
```

Request shape:

```text
["b.BatchGetIssuesRequest", null, null, [ISSUE_IDS, DETAIL_LEVEL, FLAG_2]]
```

| Position | Field | Type | Value |
|----------|-------|------|-------|
| `[1]`, `[2]` | unused | `null` | The client sends `null` |
| `[3][0]` | issue_ids | `list[int]` | Issue IDs to fetch |
| `[3][1]` | detail_level | `int` | Use `2` to include the body, links, and relationship graph |
| `[3][2]` | flag_2 | `int` | The client uses `2`; recorded tests with 0 through 10 found no change |

Match results by issue ID. Their order may differ from the request order.

### List comments

```text
POST /action/issues/{issue_id}/listComments
```

Request shape:

```text
[ISSUE_ID, SORT_ORDER, PAGE_SIZE, PAGE_TOKEN]
```

| Position | Field | Type | Value |
|----------|-------|------|-------|
| `[0]` | issue_id | `int` | Issue ID |
| `[1]` | sort_order | `str \| null` | `"ASC"` for oldest first, `"DESC"` or `null` for newest first |
| `[2]` | page_size | `int` | Up to 500 comments |
| `[3]` | page_token | `str`, omitted on the first page | Token from the previous response |

This endpoint returns text comments. Its `total_count` excludes updates that
only change fields. Use `/updates` to include field changes.

The client defaults to `sort_order="ASC"` and `page_size=500`.
To request the first three comments, oldest first:

```json
[496840714, "ASC", 3]
```

### List issue updates

```text
POST /action/issues/{issue_id}/updates
POST /action/issues/{issue_id}/updates?currentTrackerId={tracker_id}
```

The client sends the short form, which requests updates newest first:

```text
[ISSUE_ID]
```

The API also accepts this format, tested in {doc}`AUDIT.md <audit>`:

```text
[ISSUE_ID, SORT_ORDER, PAGE_SIZE, PAGE_TOKEN, UNKNOWN_FLAG]
```

| Position | Field | Type | Value |
|----------|-------|------|-------|
| `[0]` | issue_id | `int` | Issue ID |
| `[1]` | sort_order | `str`, optional | `"ASC"` or `"DESC"`; defaults to `"DESC"` |
| `[2]` | page_size | `int`, optional | Updates per page; 1100 was tested |
| `[3]` | page_token | `str \| null` | Token from the previous response |
| `[4]` | unknown_flag | `int`, optional | `2` in captured browser requests; purpose unknown |

Updates can contain comments, field changes, and attachments.
`IssueUpdatesResult.comments` selects comments and reverses the default
response order to put the oldest first.

### Get a component

```text
GET /action/components/{id}
```

The response type is `b.Component`. The recorded response places the component
array at `data[0][28]`:

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[1]` | component_id | `int` | Component ID |
| `[2]` | parent_component_id | `int` | Parent ID |
| `[3]` | component_name | `str` | Component name |
| `[6][0]` | breadcrumb_ids | `list[int]` | IDs from the root to this component |
| `[6][1]` | breadcrumb_names | `list[str]` | Names from the root to this component |
| `[6][2]` | custom_field_defs | `list` | Custom field definitions |
| `[19]` | tracker_id | `int` | Tracker ID |

### Batch get components

```text
GET /action/components?id=X&id=Y&id=Z
```

Pass each ID as an `id` query parameter. The response type is
`b.ListComponentsResponse`. Each component has the same inner array at `[28]`
as the single component response.

### Get a tracker

```text
GET /action/trackers/{id}
```

The response type is `b.Tracker`. The recorded response places the tracker
array at `data[0][9]`:

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[0]` | tracker_id | `int` | Tracker ID |
| `[1]` | root_component_id | `int` | Root component ID |
| `[2]` | name | `str` | Tracker name |
| `[5]` | branding | `list` | `[logo_url, type_int, code_of_conduct_url]` |
| `[7]` | internal_url | `str` | Internal URL, such as `https://g-issues.chromium.org` |
| `[8]` | public_url | `str` | Public URL, such as `https://issues.chromium.org` |
| `[10]` | slug | `str \| null` | URL name, such as `"fuchsia"` |

### Get a hotlist

```text
GET /action/hotlists/{id}
```

The response type is `b.Hotlist`. The recorded response places the hotlist
array at `data[0][18]`:

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[0]` | hotlist_id | `int` | Hotlist ID |
| `[1]` | name | `str` | Hotlist name |
| `[2]` | description | `str \| null` | Description |
| `[6]` | created_at | timestamp | Creation time |
| `[7]` | modified_at | timestamp | Last change |
| `[8]` | admins | `list` | Admin user arrays |

### Batch get hotlists

```text
GET /action/hotlists?id=X&id=Y
```

Pass each ID as an `id` query parameter. The response type is
`b.ListHotlistsResponse`.

### List issue relationships

```text
GET /action/issues/{id}/relationships?relationshipType=1
```

The response type is `b.ListIssueRelationshipsResponse`.
`relationshipType=1` selects blocking and blocked-by relationships. An empty
response is `[["b.ListIssueRelationshipsResponse"]]`.

`TOP[36]` on an issue lists the issues it blocks. Use the relationships
endpoint to find the issues that block it.

### Health check

```text
GET /action/yes
```

This endpoint returns `yes` as `text/plain`, without a JSON prefix or
request body. The recorded checks in {doc}`AUDIT.md <audit>` cover 13
domains.

The client exposes this as `echo()`. It strips whitespace from a successful
response and returns `"no"` for a non-200 response or an HTTP error.

## Response shapes

Here, `data` is the parsed JSON response. Names in uppercase describe values
rather than literal JSON.

### Search response

Type: `b.IssueSearchResponse`.

```text
data[0] = ["b.IssueSearchResponse", ...]
data[0][6] = [ISSUES, PAGE_TOKEN, TOTAL_COUNT]
```

| Path | Value |
|------|-------|
| `[0][6][0]` | Issue arrays |
| `[0][6][1]` | Next page token, or `null` on the last page |
| `[0][6][2]` | Approximate total matching issues |

### Issue detail response

Type: `b.IssueFetchResponse`.

```text
data[0] = ["b.IssueFetchResponse", PAYLOAD]
```

The issue array is usually at `data[0][1][22]`. The parser searches `PAYLOAD`
from the end and selects the first list with an integer at `[1]`.

### Batch response

Type: `b.BatchGetIssuesResponse`.

```text
data[0] = ["b.BatchGetIssuesResponse", null, [[ISSUE_1, ISSUE_2, ...]]]
```

Issue arrays are at `data[0][2][0]`.

### Comments response

Type: `b.ListIssueCommentsResponse`.

```text
data[0] = ["b.ListIssueCommentsResponse", [COMMENTS, PAGE_TOKEN, TOTAL_COUNT]]
```

| Path | Value |
|------|-------|
| `[0][1][0]` | [Comment arrays](#comment-arrays) |
| `[0][1][1]` | Next page token, such as `"start_index:2"`, or `null` |
| `[0][1][2]` | Total text comments |

### Updates response

Type: `b.ListIssueUpdatesResponse`.

```text
data[0] = ["b.ListIssueUpdatesResponse", [UPDATES, PAGE_TOKEN, TOTAL_COUNT]]
```

| Path | Value |
|------|-------|
| `[0][1][0]` | [Update entries](#update-entries) |
| `[0][1][1]` | Next page token, or `null` |
| `[0][1][2]` | Total updates |

## Issue array

`TOP` means one issue array. `details` means `TOP[2]`.
The reference layout has 48 positions. Recorded search responses also include
47-element arrays, so array length alone does not identify an issue.

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[1]` | issue_id | `int` | Issue ID; exposed as `Issue.id` |
| `[2]` | details | `list` | [Issue metadata](#details-array) |
| `[4]` | created_at | timestamp | Creation time |
| `[5]` | modified_at | timestamp | Last change |
| `[6]` | verified_at | timestamp or `null` | Verification time |
| `[9]` | star_count | `int \| null` | The parser maps `null` to 0 |
| `[10]` | unknown | `int` | Recorded value: `3` |
| `[11]` | comment_count | `int` | Includes updates that only change fields |
| `[12]` | revision_token | `str` | [Revision token](#revision-token) |
| `[13]` | owner | user array | Assigned owner |
| `[14]` | custom_field_defs | `list` | Field definitions; values are in `details[14]` |
| `[33]` | custom_field_refs | `list[list[int]]` | Field IDs for the component |
| `[34]` | last_activity_at | timestamp | Last comment or substantive field change, per recorded tests |
| `[35]` | modified_at_mirror | timestamp | Last write; recorded values match or closely follow `TOP[5]` |
| `[36]` | blocking_issue_ids | `list[int]` | Issues this issue blocks |
| `[37]` | relationship_graph | `list` | Recorded shape: `[[this_issue, [[blocked_issue]]]]` |
| `[40]` | links | `list` | Links from the body: `[[[url], null, type_int]]` |
| `[41]` | tracker_id | `int \| null` | Tracker ID |
| `[43]` | body | `list \| null` | Description entry from detail or batch fetches |
| `[46]` | views | `list \| null` | `[24h_views, 7d_views, 30d_views]`; the parser maps missing counts to 0 |
| `[47]` | last_modifier | user array | Last person to change the issue |

The parser reads views at `[46]` and the last modifier at `[47]`.
Recorded search arrays can place the last modifier at `[46]`.
The raw fields above include fields that the `Issue` model does not expose.
See [parser.py](https://github.com/rly0nheart/bugpipe/blob/master/src/bugpipe/api/parser.py) for the fields it extracts.

### Body entry

`TOP[43]` contains the description entry. It is `null` in recorded search
responses. Fetch the issue with detail level `2` to request it.

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[0]` | text | `str` | Description text, which may contain Markdown |
| `[1]` | unknown | `null` | Recorded value: `null` |
| `[2]` | author | user array | Description author |
| `[3]` | timestamp | timestamp | Description timestamp |
| `[4]` | unknown | `list` | Recorded value: `[]` |
| `[5]` | issue_id | `int` | Parent issue |
| `[6]` | sequence | `int` | Recorded value: `1` |

The parser extracts `TOP[43][0]` as `Issue.body`.

### Revision token

Recorded `TOP[12]` values decode twice from base64 to
`{issue_id}-{update_rev}-{comment_rev}`. For example:

```python
import base64

encoded = "TlRFek5USXpORFE0TFRJdE1RPT0="
plain = base64.b64decode(s=base64.b64decode(s=encoded)).decode()
issue_id, update_rev, comment_rev = plain.split("-")
# plain == "513523448-2-1"
```

The recorded observations describe `update_rev` as matching `TOP[11]` and
`comment_rev` as tracking comment sequence numbers. These values can exceed
visible counts when comments have been deleted or restricted.

In those observations, the token stayed the same across repeated fetches,
sessions, and detail/batch requests. No captured request sent it back to the
server. Comparing tokens can detect a revision change. The Python client
does not expose or send this token.

## Details array

The reference layout for `TOP[2]` has 32 positions.

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[0]` | component_id | `int` | Resolve the name with a component request |
| `[1]` | issue_type | `int` | [Issue type](#issue-type) value |
| `[2]` | status | `int` | [Status](#status) value |
| `[3]` | priority | `int` | 1 means P0; 5 means P4 |
| `[4]` | severity | `int \| null` | 1 means S0; 5 means S4 |
| `[5]` | title | `str` | Issue title |
| `[6]` | reporter | user array | Person who filed the issue |
| `[7]` | verifier | user array | Person who verified the fix |
| `[9]` | ccs | `list[user_array]` | CC users |
| `[13]` | hotlist_ids | `list[int]` | Hotlists containing the issue |
| `[14]` | custom_field_values | `list` | [Custom field entries](#custom-fields) |
| `[16]` | found_in | `list[str]` | Affected versions; API field name: `found_in_versions` |
| `[19]` | in_prod | `bool \| null` | `true` means observed in production; the parser preserves only `true`, otherwise `None` |
| `[21]` | duplicate_issue_ids | `list[int]` | Issues marked as duplicates of this issue |
| `[30]` | collaborators | `list[user_array]` | Collaborator users |
| `[31]` | issue_access_level | `list` | Recorded value: `[1]`; meaning unverified |

## Custom fields

Custom field values are stored at `details[14]`. Trackers can define different
field IDs. Each entry has this shape:

```text
[field_id, null, null, null, numeric_value, label_values, null, enum_values, null, display_string, ...]
```

| Index | Field | Type |
|-------|-------|------|
| `[0]` | field_id | `int` |
| `[4]` | numeric_value | `int \| float \| null` |
| `[5]` | label_values | Nested lists of strings |
| `[7]` | enum_values | Nested lists of strings |
| `[9]` | display_string | `str \| null` |

The parser takes the first usable value in this order: number at `[4]`,
labels at `[5]`, enum values at `[7]`, then display text at `[9]`.
It flattens label and enum lists.

### Chromium field IDs

`CUSTOM_FIELD_IDS` maps these 24 IDs for tracker `157`:

| Field ID | Name                    | Type        |
|----------|-------------------------|-------------|
| 1222907  | component_tags          | `list[str]` |
| 1223031  | chromium_labels         | `list[str]` |
| 1223032  | design_doc              | `str`       |
| 1223033  | build_number            | `str`       |
| 1223034  | respin                  | `str`       |
| 1223081  | flaky_test              | `str`       |
| 1223083  | notice                  | `str`       |
| 1223084  | os                      | `list[str]` |
| 1223085  | milestone               | `list[str]` |
| 1223086  | release_block           | `list[str]` |
| 1223087  | merge                   | `list[str]` |
| 1223088  | security_release        | `list[str]` |
| 1223131  | design_summary          | `str`       |
| 1223134  | merge_request           | `list[str]` |
| 1223135  | vrp_reward              | `float`     |
| 1223136  | cve                     | `list[str]` |
| 1225154  | next_action             | `str`       |
| 1225337  | estimated_days          | `float`     |
| 1225362  | backlog_rank            | `float`     |
| 1253656  | component_ancestor_tags | `list[str]` |
| 1300460  | irm_link                | `str`       |
| 1358989  | fixed_by_code_changes   | `list[str]` |
| 1410892  | cwe_id                  | `float`     |
| 1544844  | introduced_in           | `str`       |

The parser stores unknown IDs in `Issue.custom_fields` as `field_{id}`.
It maps `chromium_labels` to `Issue.labels`. Known fields without a dedicated
`Issue` attribute, including `design_doc`, `design_summary`, `respin`, and
`backlog_rank`, remain in `custom_fields` under their mapped names.

## User arrays

User fields include the reporter, owner, verifier, and CC users. A typical
array is:

```json
[null, "user@example.com", 1, ["google_domain"]]
```

The parser returns the first string containing `@`. It returns `None` when
there is no such string. It does not decode the other user fields.

## Timestamps

Timestamps contain Unix seconds and an optional nanosecond value:

```json
[1657579144, 285000000]
```

The parser treats missing nanoseconds as 0 and returns a UTC `datetime`.
For this example:

```python
from datetime import datetime, timezone

seconds, nanos = [1657579144, 285000000]
timestamp = datetime.fromtimestamp(
    timestamp=seconds + nanos / 1e9, tz=timezone.utc
)
```

## Enums

### Status

| API value | Name | Open |
|-----------|------|------|
| 1 | NEW | Yes |
| 2 | ASSIGNED | Yes |
| 3 | ACCEPTED | Yes |
| 4 | FIXED | No |
| 5 | VERIFIED | No |
| 6 | NOT_REPRODUCIBLE | No |
| 7 | INTENDED_BEHAVIOR | No |
| 8 | OBSOLETE | No |
| 9 | INFEASIBLE | No |
| 10 | DUPLICATE | No |

### Priority and severity

Both use values 1 through 5 in the API. The parser subtracts 1 to match the
Python enums.

| API value | Priority | Severity |
|-----------|----------|----------|
| 1 | P0 | S0 |
| 2 | P1 | S1 |
| 3 | P2 | S2 |
| 4 | P3 | S3 |
| 5 | P4 | S4 |

### Issue type

| API value | Name |
|-----------|------|
| 1 | BUG |
| 2 | FEATURE_REQUEST |
| 3 | CUSTOMER_ISSUE |
| 4 | INTERNAL_CLEANUP |
| 5 | PROCESS |
| 6 | VULNERABILITY |

## Update entries

Each update uses this 10-position layout:

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[0]` | author | user array | Person who made the update |
| `[1]` | timestamp | timestamp | Update time |
| `[2]` | comment | `list \| null` | [Comment array](#comment-arrays), if present |
| `[3]` | sequence_number | `int` | Update sequence |
| `[4]` | unknown | Unknown | Not parsed |
| `[5]` | field_changes | `list` | [Field change entries](#field-changes) |
| `[6]` | comment_number | `int` | Raw comment number |
| `[7]` | attachments | `list` | Attachment entries |
| `[8]` | unknown | Unknown | Not parsed |
| `[9]` | issue_id | `int` | Parent issue |

Attachment arrays are at `data[0][1][0][i][7]`. Each starts with:

```text
[attachment_id, mime_type, size_bytes, filename, ...]
```

The parser reads the restriction level at `attachment[9][0][0]`.
The `AttachmentRestriction` enum maps 1 to `NO_RESTRICTION`, 2 to `RESTRICTED`,
and 3 to `RESTRICTED_PLUS`.

## Comment arrays

The parser reads comment fields through index `[18]`. Captured arrays can
omit trailing fields; the parser returns `None` for missing timestamps and
user fields.

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[0]` | body | `str` | Comment text |
| `[2]` | author | user array | Comment author |
| `[3]` | modified_at | timestamp | Last edit time; exposed as `Comment.timestamp` |
| `[4]` | unknown | `list` | Recorded value: `[]` |
| `[5]` | issue_id | `int` | Parent issue |
| `[6]` | sequence_number | `int` | Starts at 0 in updates and 1 in `listComments` |
| `[8]` | unknown | `int` | Recorded values: 1 and 2; meaning unverified |
| `[9]` | unknown | `list` | Recorded value: `[[1]]`; meaning unverified |
| `[14]` | comment_token | `str` | Recorded as a stable token per comment; not parsed |
| `[17]` | last_editor | user array | Last person to edit the comment |
| `[18]` | created_at | timestamp | Original post time |

The parser adds 1 to sequence numbers from `/updates` and preserves those
from `/listComments`. Both produce `Comment.comment_number` values starting
at 1.

Recorded tests found that `[3]` equals `[18]` for unedited comments and is
later after an edit. A self-edit can change `[3]` while leaving the author
and last editor equal.

## Field changes

Changes are stored at `update[5]`. Each entry has this shape:

```text
[FIELD_NAME, null, OLD_VALUE_WRAPPER, NEW_VALUE_WRAPPER]
```

| Index | Field | Meaning |
|-------|-------|---------|
| `[0]` | field_name | Changed field |
| `[2]` | old_value | Previous value in a typed wrapper |
| `[3]` | new_value | New value in a typed wrapper |

An integer wrapper looks like this:

```json
["type.googleapis.com/google.protobuf.Int32Value", [42]]
```

Recorded field names include `component_id`, `type`, `status`, `priority`,
`hotlist_ids`, `ccs`, `found_in_versions`, `is_archived`, `is_deleted`, and
`access_limit`.

The parser extracts only the field name. `FieldChange.old_value` and
`FieldChange.new_value` remain `None`.

## Pagination

Search, comment, and update responses include a next page token and a total
count. Search totals are approximate. A `null` token marks the last page.

| Request | Where to send the next token |
|---------|-----------------------------|
| Search | Request `[6][3]` |
| Comments | Request `[3]` |
| Updates, extended form | Request `[3]` |

Pass tokens back unchanged. In the client, use
`next_page(result=search_result)` for searches. For comments, call
`comments()` with the same issue ID and the result's `next_page_token` as
`page_token`. The `issue_updates()` method sends one request using the short
form; it exposes the returned token but does not accept a page token.

## Component hierarchy

Recorded component lookups place the public trackers under component
`166797`:

```text
Public Trackers (166797)
  ├── Chromium (1362134)
  │     └── Chromium root (1363614)
  │           └── Internals (1456292)
  │                 └── Crypto (1768937)
  └── Fuchsia (1360843)
        └── Hardware Platform (1620976)
              └── Zircon Kernel (1478131)
                    └── VM (1477815)
```

Issues contain a numeric `component_id`. Resolve its name and parent path
with `GET /action/components/{id}`, or fetch several components with
`GET /action/components?id=X&id=Y`.
