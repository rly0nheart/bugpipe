"""
Console output for the CLI.

Results print as their dataclasses through a pager, so bulk output scrolls
instead of flooding the terminal. Writing them to file is left to the models'
own ``to_json()``/``to_csv()``.
"""

import enum
import typing as t
from contextlib import nullcontext
from datetime import datetime

from rich.box import ASCII
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table
from rich.text import Text

from ..api.models import (
    Comment,
    Exportable,
    Issue,
    IssueType,
    Priority,
    Results,
    Severity,
    Status,
)

__all__ = ["FAIL", "INFO", "OK", "WARN", "export", "print_out"]

#: Style for values the API sent that the enum doesn't define (e.g. ``TYPE_7``).
UNKNOWN_STYLE = "magenta"

#: Priority cell styles. Other known values (P3, P4) are plain yellow.
PRIORITY_STYLES = {
    Priority.P0: "bold red",
    Priority.P1: "red",
    Priority.P2: "bold yellow",
}

#: Severity cell styles. Other known values (S3, S4) are plain yellow.
SEVERITY_STYLES = {
    Severity.S0: "bold red",
    Severity.S1: "red",
    Severity.S2: "bold yellow",
}

#: Issue type cell styles. Other known values (INTERNAL_CLEANUP, PROCESS) are unstyled.
ISSUE_TYPE_STYLES = {
    IssueType.VULNERABILITY: "bold red",
    IssueType.BUG: "red",
    IssueType.CUSTOMER_ISSUE: "bold yellow",
    IssueType.FEATURE_REQUEST: "bold green",
}

#: Status cell styles. Open statuses are blue, fixed ones green. Other closed
#: statuses (NOT_REPRODUCIBLE, INTENDED_BEHAVIOR, OBSOLETE, INFEASIBLE, DUPLICATE)
#: are dim.
STATUS_STYLES = {
    Status.NEW: "bold blue",
    Status.ASSIGNED: "cyan",
    Status.ACCEPTED: "bold cyan",
    Status.FIXED: "green",
    Status.VERIFIED: "bold green",
}

#: Issue table columns: header -> cell builder. Int cells are right-aligned.
ISSUE_COLUMNS: dict[str, t.Callable[[Issue], t.Any]] = {
    "ID": lambda issue: issue.id,
    "Title": lambda issue: issue.title,
    "Type": lambda issue: _style_cell(
        value=issue.issue_type, styles=ISSUE_TYPE_STYLES, default="dim"
    ),
    "Priority": lambda issue: _style_cell(
        value=issue.priority, styles=PRIORITY_STYLES, default="yellow"
    ),
    "Severity": lambda issue: _style_cell(
        value=issue.severity, styles=SEVERITY_STYLES, default="green"
    ),
    "Status": lambda issue: _style_cell(
        value=issue.status, styles=STATUS_STYLES, default="dim"
    ),
    "24h Views": lambda issue: issue.views_24h,
    "7d Views": lambda issue: issue.views_7d,
    "30d Views": lambda issue: issue.views_30d,
    "Created At": lambda issue: issue.created_at,
    "Modified At": lambda issue: issue.modified_at,
}

#: Success marker (green ✔).
OK = "[bold green]✔[/bold green]"

#: Failure/error marker (red ✘).
FAIL = "[bold red]✘[/bold red]"

#: Warning/interrupted marker (yellow ✘).
WARN = "[bold yellow]✘[/bold yellow]"

#: Informational marker (blue *).
INFO = "[bold blue]*[/bold blue]"

console = Console(log_time=False, log_path=False)


def _style_cell(value: enum.Enum | None, styles: dict, default: str = "") -> Text | str:
    """
    Build a table cell for an enum value, styled by its member.

    :param value: The enum value, or None when the issue has none.
    :param styles: Style per known member.
    :param default: Style for known members missing from ``styles``.
    :return: The styled name, or an empty string for None.
    """

    if value is None:
        return ""
    if value.name not in type(value).__members__:
        return Text(value.name, style=UNKNOWN_STYLE)
    return Text(value.name, style=styles.get(value, default))


def _pretty_print(output: t.Any):
    """
    Show a result, paging it.

    :param output: A single item, or a list of them.
    """

    if not output:
        console.log("No results.")
        return

    context = console.pager(styles=True) if console.is_terminal else nullcontext()
    if not console.is_terminal:
        console.print(f"{WARN} Not a TTY — output won't be paged.")

    with context:
        if isinstance(output, list):
            for index, item in enumerate(output):
                if index:
                    console.print()
                console.print(Pretty(item))
        else:
            console.print(Pretty(output))


def _print_table(rows: t.Sequence[dict | Exportable]):
    """
    Print and page rows in a table. Headers come from the first row.

    :param rows: Dicts (headers are the keys), issues (headers from
        ``ISSUE_COLUMNS``), or other exportables (headers from ``to_dict``).
    """

    if not rows:
        return
    dicts = [
        (
            {header: cell(row) for header, cell in ISSUE_COLUMNS.items()}
            if isinstance(row, Issue)
            else row.to_dict() if isinstance(row, Exportable) else row
        )
        for row in rows
    ]

    table = Table(box=ASCII, highlight=True, expand=True, header_style="bold")
    for header, value in dicts[0].items():
        table.add_column(
            str(header).title(),
            justify="right" if isinstance(value, int) else "left",
            overflow="fold",
        )
    for row in dicts:
        table.add_row(
            *(cell if isinstance(cell, Text) else str(cell) for cell in row.values())
        )

    if not console.is_terminal:
        console.print(f"{WARN} Not a TTY — output won't be paged.")
    with console.pager(styles=True) if console.is_terminal else nullcontext():
        console.print(table)


def print_out(
    output: list[dict] | Results[Issue] | Results[Comment] | Issue, as_raw: bool = False
):
    """
    Show a result, paging it. Issues and dicts go in a table; a single issue
    and comments print as their dataclasses.

    :param output: A single issue, a list of issues or comments, or a list of dicts.
    :param as_raw: Print tabular results as dataclasses instead of a table.
    """

    if (
        isinstance(output, Issue)
        or isinstance(output, Results)
        and all(isinstance(item, Comment) for item in output)
    ):
        _pretty_print(output=output)

    elif (
        isinstance(output, Results)
        and all(isinstance(item, Issue) for item in output)
        or isinstance(output, list)
        and all(isinstance(item, dict) for item in output)
    ):
        if as_raw:
            _pretty_print(output=output)
        else:
            _print_table(rows=output)


def export(output: Exportable | Results[t.Any], formats: list[str]):
    """
    Write a result to timestamped files, one per format.

    :param output: A single item, or a list of them.
    :param formats: Format strings, each one of ``"csv"`` or ``"json"``.
    """

    if not output:
        return

    base = f"bugpipe-{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"
    for fmt in formats:
        if fmt == "json":
            console.print(f"\n{OK} JSON exported to {output.to_json(f'{base}.json')}")
        elif fmt == "csv":
            console.print(f"\n{OK} CSV exported to {output.to_csv(f'{base}.csv')}")
        else:
            continue
