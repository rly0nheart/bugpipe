# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-09-27

### Added

- _-p/--proxy URL_ routes every request through a proxy. Without it, the
  _HTTP_PROXY_ and _HTTPS_PROXY_ environment variables are honoured. The
  library takes the same value as _Bugpipe(proxy=...)_.
- _-r/--raw_ prints _search_ and _issues_ results as their dataclasses instead
  of a table.
- _trackers_ prints as a table.
- The startup line lists the options you set to something other than their
  default.

### Changed

- Renamed the project to Bugpipe. This will apply everywhere.
- The library is synchronous. Use _with Bugpipe() as client:_ and call methods
  directly; there is no _async_ or _await_.
- _-t/--tracker_ belongs to _search_ and goes after the query:
  _bugpipe search "status:open" -t chromium_. It takes the slugs listed by
  _bugpipe trackers_ (_chromium_, not _Chromium_).
- _-e/--export_ belongs to _search_, _issue_, _issues_, and _comments_, and
  goes after the command.
- _--timeout_ has the short form _-t_.

### Removed

- _--debug_.

### Fixed

- _-t/--tracker_ returned a 400 error for every value. The tracker names the
  flag accepted were not what the tracker expected.


## [2.3.0] - 2026-09-24

### Changed

- _search_ and _issues_ print their results as a table.

## [2.2.0] - 2026-09-22

### Added

- Documentation site on Read the Docs
- Tests for custom field parsing, view counts, and the update checker.

### Changed

- The CLI installs with the library. The _cli_ extra is gone and _rich_ is a
  core dependency.
- _FINDINGS.md_ is now _AUDIT.md_, rewritten with a tested/untested status for
  each recorded endpoint.

## [2.1.1] - 2026-08-05

### Added

- _CONTRIBUTING.md_, covering formatting, docstrings, the API reference, and
  how to pick a version for your own changelog entry.

### Changed

- Tests now run on every pull request, not only on the nightly schedule.
- CI runs Python 3.13 and 3.14, matching the _requires-python_ floor.
- A new push to a pull request cancels the run still going for the old commit.
- Formatted _parser.py_ and _test_parser.py_ with black.

### Removed

- Python 3.11 and 3.12 from the CI matrix.

## [2.1.0] - 2026-08-05
### Added
- an _Attachment_ model for issue update attachments
- _AttachmentRestriction_ values for no restriction, restricted, and restricted+
- regression coverage for deleted and restricted attachments
- support deleted attachments with a nullable file size

## [2.0.0] - 2026-07-26

### Added

- _to_dict()_, _to_json()_, and _to_csv()_ on every model, and on the list a
  read hands back: _issue.to_json("issue.json")_, _issues.to_csv("issues.csv")_.
  Each write returns the path and makes missing parent directories.

### Changed

- Results now print as their dataclasses through the pager, every field the
  tracker sent, rather than as a table of chosen columns. Enums read as their
  names (_FIXED_, _P1_) and timestamps in ISO form.
- _-e/--export_ writes every field, and is handled by the models themselves.

### Removed

- _-f/--fields_ and _-F/--all-fields_: all fields are shown, so there are no
  extra ones to ask for.
- HTML export: _-e/--export_ takes _csv_ and _json_.

## [1.10.0] - 2026-06-16

### Added

- _Comment.created_at_: a comment's original post time.

### Changed

- Require at least Python 3.13 or later
- Comment dates now display in your local timezone and locale.

### Fixed

- _Comment.is_edited_ now detects author self-edits.

### Removed

- GTK GUI
- _--pager_ option: output will be pages by default

## [1.9.0] - 2026-06-01

### Added

- _-p/--pager_: page rendered issues and comments through the system pager
  (e.g. _less -R_). Only engages on a TTY; otherwise it prints a notice and
  shows the output unpaged.
- **GTK4 GUI**: new desktop frontend at _buganize.gui_. Search the Issue
  Tracker from a native window with reorderable columns, per-page navigation,
  per-tracker icons, and right-click export to JSON, CSV, or HTML. Launch with
  _python -m buganize.gui_ or use the _gui.sh_ helper on Nix.
- **Per-tracker icons**: each tracker now ships with its branded SVG, shown
  next to the name in the GUI tracker selector and on the window header.
- **Desktop entry installer**: _python -m buganize.gui --install-desktop_
  drops a _.desktop_ file plus icon symlink into _~/.local/share/_ so the app
  shows up in your launcher.
- **TRACKERS slug field**: each entry now carries an explicit _slug_
  (URL-safe identifier) alongside the display _name_, so e.g.
  _{"id": 157, "slug": "chromium", "name": "Chromium",
  "url": "https://issues.chromium.org"}_.
- **Helper scripts**: _cli.sh_ and _gui.sh_ for one-shot launches inside
  the project's _nix-shell_.
- Sphinx-style docstrings across the public and internal surface of
  _buganize.api_ and _buganize.gui_.

### Changed

- _TRACKERS_ entries gained a _slug_ key and the existing _name_ key is now
  the human-readable display name. Code passing tracker slugs (e.g.
  _"chromium"_) to _Buganize(trackers=...)_ keeps working, the lookup
  resolves slugs to IDs. Code reading _tracker["name"]_ now receives the
  display name (_"Chromium"_) rather than the slug.
- _shell.nix_ extended with the GTK4 runtime, _gtk4_, _libadwaita_,
  _pygobject3_, _gobject-introspection_, _gdk-pixbuf_, _cairo_,
  _pkg-config_.

## [1.8.0] - 2026-05-15

### Added

- _Issue.last_activity_at_: timestamp of the last substantive update (comment or
  meaningful field change), excluding the automated metadata churn that bumps
  _modified_at_. Available as the _last_activity_ CLI field.
- _Comment.last_editor_ and _Comment.is_edited_: last person to edit a comment,
  and whether it was edited since posting.
- _buganize echo_: standalone command that pings the backend and prints
  _✔ echo: yes_ when reachable and healthy or _✘ echo: no_ when unreachable
  or erroring.

### Changed

- _Buganize.is_healthy()_ replaced by _Buganize.echo()_, which returns the raw
  backend response (_"yes"_ when healthy, _"no"_ when unreachable) instead of a
  bool.
- The implicit pre-flight health check that ran before every command has been
  removed; use _buganize echo_ to check connectivity.
- Minor changes

## [1.7.1] - 2026-04-11

### Added

- Dockerfile

### Changed

- Renamed _output_handler.py_ to _output.py_
- Append _Output_ to all classes of _output.py_ for clarity
- Seaparate installation docs from main README file

## [1.7.0] - 2026-04-01

### Added

- **HTML export**: _buganize search … -e html_ writes a styled HTML table with a row index column

### Changed

- **Feature-gated CLI**: _rich_ is no longer a core dependency. Install the CLI with _pip install buganize[cli]_;

## [1.6.0] - 2026-03-28

### Added

- _Buganize.is_healthy()_: checks if the Buganizer backend is reachable via _/action/yes_
- Health check runs automatically in the CLI before each command
- _CommentsResult_ dataclass with _comments_, _total_count_, _next_page_token_, and _has_more_
- API reference now documents the _/listComments_ endpoint, _/action/yes_ health check, and the extended _/updates_
  request format with sort order

### Changed

- _Buganize.comments()_ now uses the dedicated _/listComments_ endpoint instead of filtering _/updates_
- _Buganize.comments()_ returns _CommentsResult_ instead of _list[Comment]_, with support for sort order ("ASC"/"DESC"),
  page size (max 500), and pagination
- Updated API reference: new endpoints, response shapes, and corrected limitations

### Fixed

- _Buganize.issue()_ now returns the issue body/description by passing _detail_level=2_ to the _getIssue_ endpoint.
  Previously the body was always _None_ because the flag was set to _1_
- Removed deprecation warning from _Buganize.issue()_, as it's now fully functional and the preferred way to fetch a
  single issue

## [1.5.4] - 2026-03-25

### Fixed

- Failing test

### Changed

- Added doc strings to tests
- Added type hints to tests
- Properly handle potentially private issues

## [1.5.3] - 2026-03-12

### Added

- Nix shell support (_shell.nix_)

### Fixed

- Failing tests

## [1.5.2] - 2026-03-09

### Fixed

- Possible logical bug in api/parser.py

## [1.5.1] - 2026-03-08

### Fixed

- Failing tests

## [1.5.0] - 2026-03-03

### Changed

- Rename 'output' module to 'output_handler'
- Replace 't.Optional[X]' / 't.Union[X, Y]' with PEP 604 'X | None' / 'X | Y' syntax across the codebase
- Drop 'from __future__ import annotations' in favour of native union types
- Migrate tests from deprecated 'Buganize.issue()' to 'Buganize.issues()'

### Added

- Scheduled tests CI workflow (runs daily at 12:00 AM CAT)

## [1.4.0] - 2026-02-27

### Changed

- Update checker now uses async 'httpx.AsyncClient' instead of synchronous 'requests.get'

### Removed

- Dropped 'update-checker' external dependency in favour of a built-in async update checker module

## [1.3.0] - 2026-02-25

### Changed

- '-f/--fields', '-e/--export', and '-F/--all-fields' are now global options instead of per-subcommand, and
  '-f'/'-e' are repeatable (e.g. '-f owner -f cve -e csv -e json')

## [1.2.0] - 2026-02-25

### Added

- **Multi-tracker search**: '-t/--tracker' is now repeatable (e.g.
  'buganize -t chromium -t fuchsia search "status:open"')
- 'Buganize(trackers=["chromium", "fuchsia"])' library API for multi-tracker queries
- **Issue body/description**: 'Issue.body' field parsed from 'TOP[43][0]' in batch/detail responses

### Changed

- 'Buganize(tracker=...)' renamed to 'Buganize(trackers=...)': now accepts a list
- 'currentTrackerId' query parameter commented out on single-issue and updates endpoints (issue ID alone resolves
  correctly)

### Deprecated

- 'Buganize.issue()': does not return the issue body. Use 'Buganize.issues([id])[0]' instead

## [1.3.0] - 2026-02-25

### Changed

- '-f/--fields', '-e/--export', and '-F/--all-fields' are now global options instead of per-subcommand, and
  '-f'/'-e' are repeatable (e.g. '-f owner -f cve -e csv -e json')

## [1.1.2] - 2026-02-24

### Changed

- CI workflow now uses 'gh' CLI for GitHub releases instead of 'softprops/action-gh-release'
- CI checks PyPI for existing versions instead of git tags
- CI consolidated from 3 jobs to a single job

## [1.1.1] - 2026-02-24

### Fixed

- Fix USAGE.md link in README pointing to itself instead of USAGE.md
- Update API docs and project README

## [1.1.0] - 2026-02-24

### Added

- **Severity field**: issues now expose 'severity' (S0–S4), parsed independently from priority
- **Duplicate tracking**: 'duplicate_issue_ids' shows which issues have been marked as duplicates
- **Blocking issues**: 'blocking_issue_ids' sourced from the correct API field
- **Collaborators**: list of collaborator emails on an issue
- **Found-in versions**: 'found_in' shows which builds/versions a bug was discovered in
- **In-production flag**: 'in_prod' indicates whether a bug has been seen in production
- **View counts**: 'views_24h', 'views_7d', 'views_30d' for gauging issue activity
- 14 extra field columns available in CLI output ('severity', 'collaborators', 'found_in', 'in_prod', 'duplicates',
  '24h_views', '7d_views', '30d_views', and more)
- 'buganize trackers' CLI command to list all available trackers and their IDs
- 'USAGE.md': dedicated usage documentation for both the library and CLI
- API reference now documents 14 public trackers and 6 additional endpoints (components, trackers, hotlists,
  relationships)

### Changed

- Severity is shown by default in single-issue detail view
- CLI '--tracker' argument now shows available tracker names in help output
- 'Buganize(tracker_id=...)' renamed to 'Buganize(tracker=...)': accepts both names ('"chromium"') and numeric IDs (
  '"157"')

### Fixed

- 'details[21]' was incorrectly mapped to blocking issues, it is actually duplicate issue IDs
- Blocking issue IDs are now correctly sourced from the top-level array ('TOP[36]')
- View counts corrected from '[1d, 7d, total]' to '[24h, 7d, 30d]'

## [1.0.1] - 2026-02-23

### Changed

- Update API docs, and README.md at root

## [1.0.0] - 2026-02-23

### Changed

- Rebrand from "Chromium Issue Tracker" to "Google Issue Tracker", the client now queries all public trackers by
  default
- Drop 'pandas' dependency, all output uses Rich tables and stdlib 'csv'/'json' for export
- Drop HTML export format, '--export' now accepts 'csv' and 'json' only

### Added

- '-t'/'--tracker' flag to scope queries to a specific tracker by name ('chromium', 'fuchsia') or numeric ID.
  Without it, queries search across all public trackers on the Google Issue Tracker
- 'API.md': reverse-engineered documentation of the issuetracker.google.com API

## [0.2.3] - 2026-02-22

### Changed

- Update package details

### Added

- 'buganise' command to the CLI

## [0.2.2] - 2026-02-22

### Changed

- Moved from 'buganise' to 'buganize', running pip install on either one will install 'buganize' as a library and both
  'buganise' and 'buganize' as cli commands.

### Added

- Randomised user agent on each request

## [0.2.1] - 2026-02-21

### Changed

- Remove img/ dir

## [0.2.0] - 2026-02-21

### Added

- Update checker. Runs once a day

## [0.1.0] - 2026-02-21

### Added

- Async Python client ('Buganize') for the Chromium Issue Tracker
- 'search()' for querying issues with pagination support via 'next_page()'
- 'issue()' for fetching a single issue by ID
- 'issues()' for fetching multiple issues in a single request
- 'issue_updates()' for fetching comments and field changes on an issue
- 'comments()' convenience method for fetching comments in chronological order
- CLI with 'buganize' command (search, issue, issues, comments)
- Export to CSV, JSON, and HTML via '-e'/'--export'
- Extra fields display with '-f'/'--fields' and '-F'/'--all-fields'
- Jupyter notebook examples for search, issues, comments, and export
