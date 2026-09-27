# Contributing to bugpipe

Thanks for wanting to help. This file explains what a good pull request looks
like here, so your work gets merged instead of sitting in review.

Open pull requests against `dev`, not `master`. Release merges into `master`
happen separately.

## Setup

The project uses [uv](https://docs.astral.sh/uv/) and needs Python 3.13 or
later.

```bash
git clone https://github.com/rly0nheart/bugpipe
cd bugpipe
uv sync --group dev
uv run pytest
```

## Tests must pass before you open a pull request

Run the suite and read the output:

```bash
uv run pytest
```

If a test fails, fix it or say why you left it. Do not open a pull request on a
red suite and expect review to sort it out.

Add tests for what you change. New parsing code needs a test that feeds it a
real response shape, not one you invented. If you handle an edge case such as a
deleted or restricted field, cover that case too.

Some tests hit the live tracker, so they can fail for reasons that have nothing
to do with your change. Run them twice before you blame yourself.

## Format with black

```bash
uv run black src tests
```

Check your work with `uv run black --check src tests` before you push. Do not
reformat files you did not otherwise touch, as it buries your change in noise.

## Write docstrings in Sphinx style

Every public function, method, class, and module gets a docstring. Use the
field syntax already in the codebase:

```python
def __parse_timestamp(raw_timestamp: Any) -> datetime | None:
    """
    Parse a [seconds, nanos] timestamp array into a UTC datetime.

    :param raw_timestamp: A list like [1657579144] or [1657579144, 285000000].
    :return: A timezone-aware UTC datetime, or None if unparseable.
    """
```

Say what the thing does and what it hands back. Skip the restatement of the
function name.

Dataclasses document their fields in an `Attributes:` block. Look at `Comment`
or `Attachment` in `models.py` for the shape.

## Follow the style already in the codebase

Read the file you are editing before you add to it. A few conventions worth
knowing:

Type hints go on every parameter and return. Use `X | None`, not
`Optional[X]`.

Module-level `__all__` lists stay alphabetical. If you add a public name, add
it to `__all__` in the module and to `src/bugpipe/__init__.py`.

The tracker's API is reverse engineered, and Google might change it at any
time without telling anyone. Write parsing code that survives that. A field
that goes missing should leave you with an empty value, not an error that takes
down someone's whole query. The existing parser already works this way, so
follow what is there.

Enums that mirror API values define `_missing_` so an unknown number becomes an
`UNKNOWN_N` member instead of an error. Follow that pattern for any new enum
you map from the tracker.

Commit messages use conventional prefixes: `feat:`, `fix:`, `docs:`, `chore:`.

## Update the API reference when you change API-level code

`src/bugpipe/api/README.md` documents the JSON API at
`issuetracker.google.com`. There is no official documentation, so that file is
the only record of what the array positions mean. It has to stay true.

If your change touches the API level, update it in the same pull request. That
means any of:

- A new endpoint, or a change to a request body or URL.
- A new field parsed out of a response.
- A corrected or newly discovered array index.
- A new enum mapped from tracker values.

Document the index path from the response root, the way the existing entries
do, and bump the `Last updated` line at the top. Say where you found the shape
if it took work to find it. The next person will thank you.

## Update the CHANGELOG and the version

Do this yourself. You understand your change better than the maintainer or
anyone else who reads it later, so you are the one who should describe it. It
is your work. Represent it.

The changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Judge the impact of your own change and pick the version accordingly:

Bump the patch number for a bug fix that changes no public names or behaviour.
Bump the minor number for a new model, method, field, or CLI option that leaves
existing code working.

A major bump is different. Renaming or removing a public name, changing what a
method returns, or otherwise breaking code written against the old version
affects everyone using the library. Expect the maintainer and other
contributors to want to talk it through before it lands. Raise it early in the
pull request rather than at the end, and be ready to explain why the break is
worth it.

Add your entry to `CHANGELOG.md` under a new version heading, and set the same
version in `pyproject.toml`. The two must match.

```markdown
## [2.2.0] - 2026-08-12

### Added
- an _Attachment_ model for issue update attachments
```

Group entries under `Added`, `Changed`, `Fixed`, or `Removed`. Write what a
user gets, not what you did to the source. Italicise identifiers with
underscores, as the existing entries do.

If you are unsure between minor and major, say so in the pull request and pick
the larger one.

## On AI-generated code

Use whatever tools you like. AI-written code is welcome here.

What gets rejected is code you have not read and do not understand. You need to
know what you are doing here. The API is undocumented and the parsing is
delicate, so a contributor who cannot say why a line is there, why they picked
a particular index, or what happens when a field comes back empty is not in a
position to change it. Review will ask. Have answers.

So use the tool to help you work, not to work for you. Read your diff line by
line before you push. Run it against the real tracker and see what comes back.
Cut anything you cannot justify.

Your pull request description should say what you changed and why, in your own
words.

## Checklist

- [ ] `uv run pytest` passes.
- [ ] `uv run black --check src tests` passes.
- [ ] New and changed code has Sphinx docstrings.
- [ ] `src/bugpipe/api/README.md` updated, if the change is API level.
- [ ] `CHANGELOG.md` entry added, with a semver version bump.
- [ ] `pyproject.toml` version matches the changelog.
- [ ] You have read your own diff.
