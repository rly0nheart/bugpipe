"""
Console output for the CLI.

Results print as their dataclasses through a pager, so bulk output scrolls
instead of flooding the terminal. Writing them to file is left to the models'
own ``to_json()``/``to_csv()``.
"""

import typing as t
from contextlib import nullcontext
from datetime import datetime

from rich.box import ASCII
from rich.console import Console, Group
from rich.pretty import Pretty
from rich.table import Table

from ..api.models import Comment, Exportable, Issue, Results

__all__ = ["FAIL", "INFO", "OK", "WARN", "export_out", "print_out"]

#: Issue table columns: header -> field name. Int cells are right-aligned.
ISSUE_COLUMNS = {
    "ID": "id",
    "Title": "title",
    "Type": "issue_type",
    "Priority": "priority",
    "Severity": "severity",
    "Status": "status",
    "24h Views": "views_24h",
    "7d Views": "views_7d",
    "30d Views": "views_30d",
    "Created At": "created_at",
    "Modified At": "modified_at",
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


def prettify(output: t.Any) -> Group | None:
    """
    Build a pretty-printed view of a result, one item per block.

    :param output: A single item, or a list of them.
    :return: The renderable, or None when there is nothing to show.
    """

    if not output:
        return None
    items = output if isinstance(output, list) else [output]
    blocks = [block for item in items for block in (Pretty(item), "")]
    return Group(*blocks[:-1], fit=False)


def table(rows: t.Sequence[dict | Exportable] | Exportable) -> Table | None:
    """
    Build a table.

    A sequence gets one row per item; a single item gets one
    row per dataclass field, as field name and value.

    :param rows: The items to show, or one item.
    :return: The table, or None when there is nothing to show.
    """

    is_single_item: bool = isinstance(rows, Exportable)
    if is_single_item:
        dicts = [
            {"field": key, "value": value} for key, value in rows.to_dict().items()
        ]
    elif not rows:
        return None
    else:
        dicts = [
            (
                {header: row.to_dict()[name] for header, name in ISSUE_COLUMNS.items()}
                if isinstance(row, Issue)
                else row.to_dict() if isinstance(row, Exportable) else row
            )
            for row in rows
        ]

    table = Table(
        box=ASCII, highlight=True, expand=not is_single_item, header_style="bold"
    )
    for header, value in dicts[0].items():
        table.add_column(
            str(header).title(),
            justify="right" if isinstance(value, int) else "left",
            overflow="fold",
        )
    for row in dicts:
        table.add_row(
            *("[dim]-[/dim]" if cell is None else str(cell) for cell in row.values())
        )

    return table


def print_out(
    output: list[dict] | Results[Issue] | Results[Comment] | Issue | Comment,
    no_pager: bool = False,
    prettified: bool = False,
):
    """
    Show a result, paging it in a terminal.

    :param output: A single issue or comment, a list of issues or comments,
        or a list of dicts.
    :param no_pager: Print straight to the terminal instead of paging.
    :param prettified: Print results as prettified dataclasses instead of a table.
    """

    if not (
        isinstance(output, (Issue, Comment))
        or isinstance(output, Results)
        and all(isinstance(item, (Issue, Comment)) for item in output)
        or isinstance(output, list)
        and all(isinstance(item, dict) for item in output)
    ):
        raise ValueError(f"Unexpected value type for param `output`: {type(output)}")

    render = prettify(output=output) if prettified else table(rows=output)
    if render is None:
        console.log(f"{WARN} Nothing to print.")
        return

    if not no_pager and not console.is_terminal:
        console.print(f"{WARN} Not a TTY — output won't be paged.")
    with (
        console.pager(styles=True)
        if not no_pager and console.is_terminal
        else nullcontext()
    ):
        console.print(render)


def export_out(output: Exportable | Results[t.Any], formats: list[str]):
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
            console.print(f"{OK} JSON exported to {output.to_json(f'{base}.json')}")
        elif fmt == "csv":
            console.print(f"{OK} CSV exported to {output.to_csv(f'{base}.csv')}")
        else:
            continue
