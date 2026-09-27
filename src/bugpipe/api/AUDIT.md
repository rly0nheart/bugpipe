# Authenticated API audit

These audits come from browser traffic captured with mitmproxy while signed in to `issuetracker.google.com`. Some endpoints also work without authentication.

“Tested” records the status of the original checks. “Untested” means the
behavior was captured or noted but not verified by those checks.

## Endpoints

| # | Endpoint                                                  | Tested | Result or recorded note                       |
|---|-----------------------------------------------------------|--------|-----------------------------------------------|
| 1 | [List comments](#1-list-comments)                         | Yes    | Returns text comments without authentication  |
| 2 | [User preferences](#2-user-preferences)                   | No     | Captured response: `[["f.mt"]]`; meaning unknown |
| 3 | [Read timestamp](#3-read-timestamp)                       | No     | Captured request and timestamp response       |
| 4 | [Component access policies](#4-component-access-policies) | Yes    | Users and groups listed by role               |
| 5 | [User access](#5-user-access)                             | Yes    | Returns the roles held by the requesting user |
| 6 | [Similar issues](#6-similar-issues)                       | No     | Recorded note: HTTP 401 without Google authentication cookies    |
| 7 | [Health check](#7-health-check)                           | Yes    | HTTP 200 with `yes` on 13 tested domains      |
| 8 | [Update request](#8-update-request)                       | Yes    | Accepts sort order, page size, and page token |
| 9 | [Field changes](#9-field-changes)                         | Yes    | Initial update includes archive, deletion, and access fields |
| 10 | [Protobuf types](#10-protobuf-types)                     | No     | Captured `IssueAccessLimit` and `User` type names |
| 11 | [Issue timestamps](#11-issue-timestamps)                 | Yes    | `[34]` tracks substantive activity; `[35]` tracks the last write |
| 12 | [Private hotlists](#12-private-hotlists)                 | No     | Recorded note: batch requests omit private hotlists; single requests return HTTP 403 |

## 1. List comments

```text
POST /action/issues/{issue_id}/listComments
```

Tested without cookies or authentication tokens.

Request shape:

```text
[ISSUE_ID, SORT_ORDER, PAGE_SIZE, PAGE_TOKEN]
```

| Position | Field | Type | Value |
|----------|-------|------|-------|
| `[0]` | issue_id | `int` | Issue ID |
| `[1]` | sort_order | `str \| null` | `"ASC"` for oldest first; `"DESC"` or `null` for newest first |
| `[2]` | page_size | `int` | Comments per page |
| `[3]` | page_token | `str`, omitted on the first page | Token from the previous response |

Both sort orders passed the recorded checks. The response has this shape:

```text
data[0] = ["b.ListIssueCommentsResponse", [COMMENTS, PAGE_TOKEN, TOTAL_COUNT]]
```

| Path | Type | Value |
|------|------|-------|
| `[0][1][0]` | `list[list]` | Comment arrays |
| `[0][1][1]` | `str \| null` | Next page token, such as `"start_index:2"`, or `null` on the last page |
| `[0][1][2]` | `int` | Total text comments; excludes updates that only change fields |

### Comment fields

Comment fields run through index `[18]`. The shortened example below stops at
`[17]`. The parser accepts missing trailing fields.

| Index | Field | Type | Meaning |
|-------|-------|------|---------|
| `[0]` | body | `str` | Comment text |
| `[2]` | author | user array | Comment author |
| `[3]` | modified_at | timestamp | Last edit time |
| `[4]` | unknown | `list` | Recorded value: `[]` |
| `[5]` | issue_id | `int` | Parent issue |
| `[6]` | sequence_number | `int` | Starts at 1 here and at 0 in `/updates` |
| `[8]` | unknown | `int` | Recorded values: 1 and 2; meaning unverified |
| `[9]` | unknown | `list` | Recorded value: `[[1]]`; meaning unknown |
| `[14]` | comment_token | `str` | Recorded as a stable token per comment; decodes twice from base64 to a 128-bit value in hex |
| `[17]` | last_editor | user array | Last person to edit the comment |
| `[18]` | created_at | timestamp | Original post time |

The recorded check of 491 live comments found that `[18] <= [3]` in every
case. Edited comments had `[18] < [3]`. This also held for self-edits, where
the author remained the last editor.

### Example

Request the first three comments for issue `496840714`, oldest first:

```json
[496840714, "ASC", 3]
```

Shortened response:

```json
[
  [
    "b.ListIssueCommentsResponse",
    [
      [
        [
          "This is an **M147** merge request from crbug/495542144...",
          null,
          [null, "chromium-merge@google.com", 1, ["google_domain"]],
          [1774605025, 724000000],
          [],
          496840714,
          1,
          null,
          2,
          [[1]],
          null,
          null,
          null,
          null,
          "WVRReVltSTBNVEl5...",
          null,
          null,
          [null, "chromium-merge@google.com", 1, ["google_domain"]]
        ],
        [
          "Fixes a major user reported regression...",
          null,
          [null, "user@google.com", 1, ["googlers_unrestricted", "google_domain"]],
          [1774605229, 679000000],
          [],
          496840714,
          2,
          null,
          2,
          [[1]],
          null,
          null,
          null,
          null,
          "WVRReVltSTBNVEl5...",
          null,
          null,
          [null, "user@google.com", 1, ["googlers_unrestricted", "google_domain"]]
        ]
      ],
      "start_index:2",
      7
    ]
  ]
]
```

The sample contains comments 1 and 2. The next page token is
`"start_index:2"`. Its total is 7 text comments; the recorded
`issue.comment_count` was 22 because it included field-only updates.

## 2. User preferences

```text
POST /action/current_user/preferences
```

Untested. The request body was not captured. The captured response was:

```json
[["f.mt"]]
```

Its meaning is unknown.

## 3. Read timestamp

```text
POST /action/issues/read_timestamp
```

Untested. The endpoint name suggests that it marks issues as read. This is an
inference from the name and the captured timestamp response.

Captured request shape, where `ISSUE_IDS` stands for the issue ID values:

```text
[null, null, null, [[ISSUE_IDS], 1, 1]]
```

Captured response shape:

```text
[["b.UpdateIssueReadTimestampResponse", null, [null, null, [SECS, NANOS]]]]
```

## 4. Component access policies

```text
GET /action/access_policies/components%2F{component_id}
```

Tested. The response type is `b.AccessPolicy`. It contains nested user arrays
grouped by role: admin, writer, appender, and reader. Entries include users
and groups such as `"googlers_unrestricted"` and `"public_non_google"`.

## 5. User access

```text
GET /action/user_access?relations=admin,writer,appender,reader&resourceNames=issues/{id}
```

Tested. The response type is `b.UserAccessBatchResponse`.

```json
[
  [
    "b.UserAccessBatchResponse",
    [
      ["b.ResourceRelation", "issues/497175171", 3],
      ["b.ResourceRelation", "issues/497175171", 4]
    ]
  ]
]
```

For the query above, the recorded role values are:

| Value | Role |
|-------|------|
| 1 | Admin |
| 2 | Writer |
| 3 | Appender |
| 4 | Reader |

The response contains only roles held by the requesting user. The example
contains appender and reader roles. A separate check with a public read-only
user returned only `4`, the reader role.

## 6. Similar issues

```text
POST /action/retrieve_similar_issues
```

Untested. Captured request shape:

```text
["b.RetrieveSimilarIssuesRequest", [ISSUE_ID, null, null, 7, null, null, 2]]
```

The recorded note reports HTTP 401 without Google authentication cookies.
The required cookies were not verified.

## 7. Health check

```text
GET /action/yes
```

Tested without authentication. The endpoint returns `yes` as `text/plain`,
with no JSON or anti-XSSI prefix. The client exposes it as `echo()`.

These 13 domains returned HTTP 200 with `yes` in the recorded checks:

| Domain | Result |
|--------|--------|
| `issuetracker.google.com` | 200 `yes` |
| `issues.chromium.org` | 200 `yes` |
| `issues.pigweed.dev` | 200 `yes` |
| `issues.gerritcodereview.com` | 200 `yes` |
| `issues.skia.org` | 200 `yes` |
| `issues.webrtc.org` | 200 `yes` |
| `issues.fuchsia.dev` | 200 `yes` |
| `issues.angleproject.org` | 200 `yes` |
| `issues.webmproject.org` | 200 `yes` |
| `issues.oss-fuzz.com` | 200 `yes` |
| `project-zero.issues.chromium.org` | 200 `yes` |
| `gn.issues.chromium.org` | 200 `yes` |
| `git.issues.gerritcodereview.com` | 200 `yes` |

## 8. Update request

```text
POST /action/issues/{issue_id}/updates
```

Tested. The captured browser request used this form:

```text
[ISSUE_ID, "ASC", 1100, null, 2]
```

| Position | Field | Type | Value |
|----------|-------|------|-------|
| `[0]` | issue_id | `int` | Issue ID |
| `[1]` | sort_order | `str` | `"ASC"` for oldest first or `"DESC"` for newest first |
| `[2]` | page_size | `int` | 1100 in the tested request |
| `[3]` | page_token | `str \| null` | Next page token, or `null` for the first page |
| `[4]` | unknown | `int` | `2` in captured requests; purpose unknown |

## 9. Field changes

Tested. These fields appeared in `update[5]` of the initial update
(sequence 1):

| Field | Wrapper type | Recorded value |
|-------|--------------|----------------|
| `is_archived` | `BoolValue` | Not recorded here |
| `is_deleted` | `BoolValue` | Not recorded here |
| `access_limit` | `IssueAccessLimit` | `[1]`; meaning unverified |

## 10. Protobuf types

Untested. Captured type names include:

- `google.devtools.issuetracker.v1.IssueAccessLimit`
- `google.devtools.issuetracker.v1.User`

## 11. Issue timestamps

Tested. `TOP` means one issue array. Both `TOP[34]` and `TOP[35]` contained
`[seconds, nanoseconds]` timestamps in the recorded checks.

`TOP[35]` tracked the last write. It matched `modified_at` at `TOP[5]` or
differed by a few seconds. It changed with automated hotlist and custom
field updates as well as other writes.

`TOP[34]` tracked the last comment or substantive field change, such as a
status, assignee, or component change. Later automated metadata changes did
not move it. On issues with those automated changes, `TOP[34] <= TOP[35]`.
Issues with no comments still had `TOP[34]`, tied to the last substantive
field change.

## 12. Private hotlists

```text
GET /action/hotlists?id=X&id=Y
GET /action/hotlists/{id}
```

Untested. The recorded note says batch requests return only accessible
hotlists and omit private ones. Single requests for private hotlists return
HTTP 403 according to the same note.
