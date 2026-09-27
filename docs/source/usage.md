# Usage

## Library usage

```python
from bugpipe import Bugpipe
```

### Search issues

```python
# Search across all public trackers (default)
with Bugpipe() as client:
    result = client.search("status:open component:Blink", page_size=10)

    print(f"{result.total_count} total matches")
    for issue in result.issues:
        print(f"#{issue.id} [{issue.status.name}] {issue.title}")

    # Pagination
    if result.has_more:
        page2 = client.next_page(result)
        for issue in page2.issues:
            print(f"#{issue.id} [{issue.status.name}] {issue.title}")
```

```python
# Search only within the Chromium tracker
with Bugpipe(trackers=["chromium"]) as client:
    result = client.search("status:open component:Blink")
```

```python
# Search across Chromium and Fuchsia trackers
with Bugpipe(trackers=["chromium", "fuchsia"]) as client:
    result = client.search("status:open")
```

### Get a single issue

```python
with Bugpipe() as client:
    issue = client.issue(40060244)

    print(issue.title)
    print(issue.url)  # https://issuetracker.google.com/issues/40060244
    print(issue.body)  # Description
    print(issue.status.name)  # e.g. "FIXED"
    print(issue.priority.name)  # e.g. "P2"
    print(issue.severity.name)  # e.g. "S2" (may differ from priority)
    print(issue.os)  # e.g. ["Linux", "Mac", "Windows"]
    print(issue.cve)  # e.g. ["CVE-2024-1234"]
    print(issue.found_in)  # e.g. ["CP21.260116.011.A1"]
    print(issue.in_prod)  # True or None
    print(issue.collaborators)  # e.g. ["user@example.com"]
    print(issue.duplicate_issue_ids)  # e.g. [12345, 67890]
    print(issue.blocking_issue_ids)  # e.g. [11111]
    print(issue.views_24h, issue.views_7d, issue.views_30d)  # e.g. 5, 20, 100
```

### Batch get issues

```python
with Bugpipe() as client:
    issues = client.issues([40060244, 485912774, 486077869])

    for issue in issues:
        print(f"#{issue.id} - {issue.title}")
```

### Get comments

```python
with Bugpipe() as client:
    result = client.comments(486077869)

    for comment in result.comments:
        print(f"#{comment.comment_number} by {comment.author}")
        print(comment.body)
```

### Get full updates

Updates include both comments and field changes (status changes, priority changes, etc.):

```python
with Bugpipe() as client:
    result = client.issue_updates(486077869)

    print(f"{result.total_count} total updates")

    # Just the comments, in chronological order
    for comment in result.comments:
        print(f"#{comment.comment_number}: {comment.body[:80]}")

    # All updates (newest first), including field changes
    for update in result.updates:
        if update.field_changes:
            changed = ", ".join(fc.field for fc in update.field_changes)
            print(f"  Fields changed: {changed}")
        if update.comment:
            print(f"  Comment: {update.comment.body[:80]}")
```

### Export results

Every issue and comment writes itself out, and so does the list a read hands back:

```python
with Bugpipe() as client:
    issues = client.issues([40060244, 485912774, 486077869])

    issues.to_csv("issues.csv")  # one row per issue
    issues.to_json("issues.json")  # one array
    issues[0].to_json("issue.json")  # one object
    issues[0].to_dict()  # the fields as a plain dict

    result = client.search("status:open", page_size=25)
    result.issues.to_csv("open.csv")
```

Missing parent directories are made, and each call returns the path it wrote.
Enums are written as their names (e.g. `FIXED`, `P1`) and timestamps in ISO form.

## CLI usage

Run with `python -m bugpipe <command>` or just `bugpipe <command>`.

### Search

```bash
# Search across all public trackers (default)
bugpipe search "status:open"

# Combined filters
bugpipe search "status:open component:Blink"

# Results per page (choices: 25, 50, 100, 250)
bugpipe search "type:bug" -n 100

# Fetch a total of 200 results, paginating as needed
bugpipe search "status:open" -l 200
```

### Tracker selection

By default, bugpipe searches across all public trackers on issuetracker.google.com. Use `-t/--tracker` to narrow to
one or more specific trackers (repeat `-t` for multiple):

```bash
# Search only Chromium issues
bugpipe search "status:open" -t chromium

# Search only Fuchsia issues
bugpipe search "status:open" -t fuchsia

# Search across Chromium and Fuchsia
bugpipe search "status:open" -t chromium -t fuchsia

# Search ANGLE and Skia issues
bugpipe search "status:open" -t angle -t skia
```

To list all available trackers and their IDs:

```bash
bugpipe trackers
```

### Issue

```bash
bugpipe issue 486077869
```

### Issues (batch)

```bash
bugpipe issues 40060244 485912774 486077869
```

### Comments

```bash
bugpipe comments 486077869
```

### Export

The `search`, `issue`, `issues`, and `comments` commands support `-e/--export` (repeatable) for exporting to CSV or JSON files. Every field the tracker sent is
written, not a chosen few. Exported files are named with a timestamp (e.g. `bugpipe-20260223_012345.csv`):

```bash
bugpipe search "status:open" -n 50 -e csv
bugpipe issue 486077869 -e json

# Multiple formats in one command
bugpipe search "status:open" -e csv -e json
```

### Timeout

Use `--timeout` to set the HTTP request timeout in seconds (default: 30):

```bash
bugpipe --timeout 60 search "status:open"
```
