import logging
import sys
from datetime import datetime

import httpx
from rich.logging import RichHandler

from ..api.client import TRACKERS
from . import update_checker
from .cmd import dispatch_client, parse_args
from .term import FAIL, INFO, WARN, console, print_out


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
        print_out(output=TRACKERS, as_raw=args.raw)
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
            f"{INFO} Started bugpipe CLI {update_checker.__version__[:3]}{overrides_text} "
            f"at {datetime.now().astimezone().strftime('%x %X')}"
        )
        with console.status("[dim]Initialising…[/dim]") as status:
            update_checker.check(status=status)
            dispatch_client(args=args, status=status)
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
