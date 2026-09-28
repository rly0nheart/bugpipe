<p align="center">
<img alt="logo" src="https://www.gstatic.com/buganizer/img/v0/logo.svg" width="150" height="150">
<br>
<br>
Unofficial Python client for Buganizer; the Google Issue Tracking system.
</p>

## Quick Start

```bash
bugpipe search "status:open"
```

```python
from bugpipe import Bugpipe


with Bugpipe() as client:
    result = client.search(query="status:open priority:p1", page_size=25)
    for issue in result.issues:
        print(f"#{issue.id} [{issue.status.name}] {issue.title}")
```

## Documentation

Refer to [the docs](https://bugpipe.readthedocs.io) for installation, usage and api reference.
