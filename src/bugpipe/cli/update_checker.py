from __future__ import annotations

import json
import re
import time
import typing as t
from importlib.metadata import version
from pathlib import Path
from tempfile import gettempdir

import httpx
from rich.status import Status

__pkg__ = "bugpipe"
__version__ = version(__pkg__)

CACHE_FILE = Path(gettempdir()) / "bugpipe_update_check.json"
CACHE_TTL = 3600


def query_pypi(package: str, include_prereleases: bool) -> dict:
    """
    Query PyPI for the latest version of a package.

    :param package: The package name to look up on PyPI.
    :param include_prereleases: Whether to consider pre-release versions.
    :return: A dict with ``success`` key, and ``data`` containing
        ``version`` and ``upload_time`` on success.
    """

    try:
        response = httpx.get(f"https://pypi.org/pypi/{package}/json", timeout=3)
    except httpx.HTTPError:
        return {"success": False}
    if response.status_code != 200:
        return {"success": False}
    data = response.json()
    versions = list(data["releases"].keys())
    versions.sort(key=parse_version, reverse=True)

    version = versions[0]
    for tmp_version in versions:
        if include_prereleases or standard_release(tmp_version):
            version = tmp_version
            break

    upload_time = None
    for file_info in data["releases"][version]:
        if file_info["upload_time"]:
            upload_time = file_info["upload_time"]
            break

    return {"success": True, "data": {"upload_time": upload_time, "version": version}}


def cached_query_pypi(package: str, include_prereleases: bool) -> dict:
    """
    Return the PyPI lookup result, reusing a cached one under an hour old.

    :param package: The package name to look up on PyPI.
    :param include_prereleases: Whether to consider pre-release versions.
    :return: The same dict as :func:`query_pypi`.
    """

    key = {"package": package, "include_prereleases": include_prereleases}
    try:
        cached = json.loads(CACHE_FILE.read_text())
        if cached["key"] == key and time.time() - cached["time"] < CACHE_TTL:
            return cached["data"]
    except (OSError, ValueError, KeyError, TypeError):
        pass  # missing or unreadable cache, query PyPI

    data = query_pypi(package=package, include_prereleases=include_prereleases)
    if data.get("success"):
        try:
            CACHE_FILE.write_text(
                json.dumps({"key": key, "time": time.time(), "data": data})
            )
        except OSError:
            pass  # cache is best effort
    return data


def standard_release(version: str) -> bool:
    """
    Check whether a version string represents a standard (non-pre-release) release.

    :param version: The version string to check.
    :return: ``True`` if the version contains only digits and dots.
    """

    return version.replace(".", "").isdigit()


def check(
    package_name: str = "buganize",
    package_version: str = __version__,
    status: Status | None = None,
):
    """Print a notice when PyPI has a newer version.

    :param package_name: Package to check.
    :param package_version: Running version.
    """

    if isinstance(status, Status):
        status.update("[dim]Checking for updates…[/dim]")

    data = cached_query_pypi(
        package=package_name,
        include_prereleases=not standard_release(version=package_version),
    )
    if not data.get("success") or (
        parse_version(string=package_version)
        >= parse_version(string=data["data"]["version"])
    ):
        return

    available = data["data"]["version"]
    message = (
        f"Version {package_version} of {package_name} is outdated. "
        f"Version {available} "
    )
    release_date = data["data"]["upload_time"]
    message += (
        f"was released on {release_date[:10]}." if release_date else "is available."
    )

    from .term import console

    console.log(f"[bold blue]⬆[/bold blue] {message}")


# The following section of code is taken from setuptools pkg_resources.py (PSF
# license). Unfortunately importing pkg_resources to directly use the
# parse_version function results in some undesired side effects.

component_re = re.compile(r"(\d+ | [a-z]+ | \.| -)", re.VERBOSE)
replace = {"pre": "c", "preview": "c", "-": "final-", "rc": "c", "dev": "@"}.get


def _parse_version_parts(version_string: str) -> t.Generator[str]:
    """
    Yield normalized version parts from a version string.

    :param version_string: A version string to split into comparable parts.
    """

    for part in component_re.split(version_string):
        part = replace(part, part)
        if not part or part == ".":
            continue
        if part[:1] in "0123456789":
            yield part.zfill(8)  # pad for numeric comparison
        else:
            yield "*" + part

    yield "*final"  # ensure that alpha/beta/candidate are before final


def parse_version(string: str) -> tuple[str, ...]:
    """
    Convert a version string to a chronologically-sortable key.

    This is a rough cross between distutils' StrictVersion and LooseVersion;
    if you give it versions that would work with StrictVersion, then it behaves
    the same; otherwise it acts like a slightly-smarter LooseVersion. It is
    *possible* to create pathological version coding schemes that will fool
    this parser, but they should be very rare in practice.

    The returned value will be a tuple of strings.  Numeric portions of the
    version are padded to 8 digits so they will compare numerically, but
    without relying on how numbers compare relative to strings.  Dots are
    dropped, but dashes are retained.  Trailing zeros between alpha segments
    or dashes are suppressed, so that e.g. "2.4.0" is considered the same as
    "2.4". Alphanumeric parts are lower-cased.

    The algorithm assumes that strings like "-" and any alpha string that
    alphabetically follows "final"  represents a "patch level".  So, "2.4-1"
    is assumed to be a branch or patch of "2.4", and therefore "2.4.1" is
    considered newer than "2.4-1", which in turn is newer than "2.4".

    Strings like "a", "b", "c", "alpha", "beta", "candidate" and so on (that
    come before "final" alphabetically) are assumed to be pre-release versions,
    so that the version "2.4" is considered newer than "2.4a1".

    Finally, to handle miscellaneous cases, the strings "pre", "preview", and
    "rc" are treated as if they were "c", i.e. as though they were release
    candidates, and therefore are not as new as a version string that does not
    contain them, and "dev" is replaced with an '@' so that it sorts lower than
    any other pre-release tag.

    :param string: The version string to parse.
    :return: A tuple of strings suitable for comparison.
    """

    parts = []
    for part in _parse_version_parts(string.lower()):
        if part.startswith("*"):
            if part < "*final":  # remove '-' before a prerelease tag
                while parts and parts[-1] == "*final-":
                    parts.pop()
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1] == "00000000":
                parts.pop()
        parts.append(part)
    return tuple(parts)
