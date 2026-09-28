import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from bugpipe.cli import update_checker


def test_update_check_caches_pypi_lookup_for_an_hour(tmp_path):
    """Query PyPI once, then serve the notice from the cache file.

    :param tmp_path: Temporary directory holding the cache file.
    """
    messages = []
    console = SimpleNamespace(console=SimpleNamespace(log=messages.append))
    query = Mock(
        return_value={
            "success": True,
            "data": {"version": "2.0.0", "upload_time": "2020-01-01T00:00:00"},
        }
    )
    with (
        patch.object(update_checker, "CACHE_FILE", tmp_path / "cache.json"),
        patch.object(update_checker, "query_pypi", new=query),
        patch.dict(sys.modules, {"bugpipe.cli.output": console}),
    ):
        for _ in range(2):
            update_checker.check(
                package_name="audit-test-package", package_version="1.0.0"
            )

        with patch.object(update_checker, "time", SimpleNamespace(time=lambda: 10**12)):
            update_checker.check(
                package_name="audit-test-package", package_version="1.0.0"
            )

    assert query.call_count == 2  # first call, then again once the cache expired
    assert (tmp_path / "cache.json").exists()
    assert (
        messages
        == [
            (
                "[bold blue]⬆[/bold blue] Version 1.0.0 of audit-test-package is outdated. "
                "Version 2.0.0 was released on 2020-01-01."
            )
        ]
        * 3
    )
