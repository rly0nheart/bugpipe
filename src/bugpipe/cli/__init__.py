import argparse
import logging
import sys
from datetime import datetime

import httpx
from rich.logging import RichHandler
from rich.status import Status

from ..api.client import TRACKERS, Bugpipe
from . import metadata, update_checker
from .commands import parse_args
from .output import FAIL, INFO, WARN, console, print_out


def create_client(args: argparse.Namespace, status: Status):
    """
    Create a client and dispatch to the chosen subcommand.

    :param args: Parsed arguments with ``.func`` set to the subcommand handler.
    :param status: Rich status spinner for progress updates.
    """

    with Bugpipe(
        trackers=getattr(args, "tracker", None),
        timeout=args.timeout,
        proxy=args.proxy,
    ) as client:
        args.func(client=client, args=args, status=status)


def format_option(value) -> str:
    """
    Render an option value for the startup line: lists in brackets, strings
    quoted so Rich's URL highlighting stops at the value.

    :param value: The option value.
    :return: Markup text.
    """

    if isinstance(value, list):
        return f"[[italic]{', '.join(map(str, value))}[/italic]]"
    if isinstance(value, str):
        return f"'[italic]{value}[/italic]'"
    return f"[italic]{value}[/italic]"


def start():
    """
    CLI entry point.
    """

    args = parse_args()

    if args.command == "trackers":
        print_out(output=TRACKERS, prettified=args.raw, no_pager=args.no_pager)
        console.print(f"\n{len(TRACKERS)} trackers available")
        return

    logging.basicConfig(
        level=logging.WARNING,
        handlers=[RichHandler(markup=True, show_level=True)],
    )

    start_time = datetime.now().astimezone()
    try:
        overrides: str = ", ".join(
            f"{name}={format_option(value)}" for name, value in args.overrides.items()
        )
        overrides_text: str = f" ({overrides})" if overrides else ""
        console.log(
            f"{INFO} Started bugpipe CLI {metadata.version[:3]}{overrides_text} "
            f"at {datetime.now().astimezone().strftime('%x %X')}"
        )
        with console.status("[dim]Initialising…[/dim]") as status:
            update_checker.check(status=status)
            create_client(args=args, status=status)
    except KeyboardInterrupt:
        console.log(f"{WARN} User interrupted ([bold yellow]CTRL+C[/bold yellow])")
        sys.exit(0)
    except httpx.ConnectError as err:
        console.log(f"{FAIL} {err}")
    except httpx.ConnectTimeout:
        console.log(f"{WARN} Connection timed out")
    finally:
        elapsed = (datetime.now().astimezone() - start_time).total_seconds()
        console.log(f"{INFO} Finished in {elapsed:.1f} seconds")
