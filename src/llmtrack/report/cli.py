"""
Terminal report using Rich library and Click CLI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from llmtrack.tracker import CallEvent

console = Console()


def print_report(events: List[CallEvent], days: int = 7) -> None:
    """Print a rich terminal cost breakdown table."""
    from llmtrack.tracker import _aggregate

    summary = _aggregate(events, days=days)

    if not events:
        console.print(
            Panel(
                f"[yellow]No data found for the last {days} days.[/yellow]\n"
                "Start tracking with: [green]with tracker.feature('my_feature'): ...[/green]",
                title="llmtrack",
                border_style="yellow",
            )
        )
        return

    # Header panel
    console.print(
        Panel(
            f"[bold green]LLM Cost Report[/bold green] — Last {days} days\n"
            f"Total: [bold red]${summary['total_cost_usd']:.4f}[/bold red]  |  "
            f"Total Calls: [bold]{summary['total_calls']:,}[/bold]",
            title="[bold]llmtrack[/bold]",
            border_style="green",
        )
    )

    # Main table
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
    )

    table.add_column("Feature", style="white", no_wrap=True)
    table.add_column("Cost (USD)", justify="right", style="bold yellow")
    table.add_column("% of Total", justify="right", style="cyan")
    table.add_column("Calls", justify="right")
    table.add_column("Avg/Call", justify="right", style="dim")
    table.add_column("Input Tokens", justify="right", style="dim")
    table.add_column("Output Tokens", justify="right", style="dim")

    total_cost = summary["total_cost_usd"]
    sorted_features = sorted(
        summary["features"].items(),
        key=lambda x: x[1]["cost_usd"],
        reverse=True,
    )

    for feature_name, data in sorted_features:
        pct = (data["cost_usd"] / total_cost * 100) if total_cost > 0 else 0
        table.add_row(
            feature_name,
            f"${data['cost_usd']:.4f}",
            f"{pct:.1f}%",
            f"{data['calls']:,}",
            f"${data['avg_cost_per_call']:.6f}",
            f"{data['input_tokens']:,}",
            f"{data['output_tokens']:,}",
        )

    console.print(table)


@click.group()
def main() -> None:
    """llmtrack — LLM cost attribution per feature."""


@main.command()
@click.option("--days", default=7, type=int, help="Number of days to report on")
@click.option("--db", default="llmtrack.db", type=str, help="Path to SQLite database")
@click.option("--html", is_flag=True, help="Generate HTML report instead")
@click.option(
    "--output", default="llmtrack_report.html", type=str, help="HTML output path"
)
def report(days: int, db: str, html: bool, output: str) -> None:
    """Show cost breakdown report."""
    from llmtrack.report.html import generate_html_report
    from llmtrack.storage.sqlite import SQLiteStorage

    storage = SQLiteStorage(db_path=db)
    events = storage.query(days=days)

    if html:
        generate_html_report(events, filepath=output, days=days)
        console.print(f"[green]Report saved to: {output}[/green]")
    else:
        print_report(events, days=days)


@main.command()
@click.option("--db", default="llmtrack.db", type=str, help="Path to SQLite database")
def clear(db: str) -> None:
    """Clear all stored data."""
    from llmtrack.storage.sqlite import SQLiteStorage

    storage = SQLiteStorage(db_path=db)
    storage.clear()
    console.print("[green]Database cleared.[/green]")


if __name__ == "__main__":
    main()
