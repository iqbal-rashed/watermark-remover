"""Interactive Rich CLI for Watermark Remover."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich import box as rbox

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]Watermark Remover[/bold white]  [dim]CLI v1.0.0[/dim]   [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════╝[/bold cyan]
"""


def _check_and_setup():
    """Run first-time setup if not already complete."""
    from app.setup_manager import is_setup_complete, get_setup_status, run_setup
    if is_setup_complete():
        return

    console.print(BANNER)
    console.print(Panel(
        "[yellow]First-time setup required.[/yellow]\n"
        "Need to download Florence-2 model (~3 GB) and ML dependencies.\n"
        "This only happens once.",
        title="[bold]Setup Required[/bold]", border_style="yellow"
    ))

    status = get_setup_status()
    gpu = status["gpu_available"]

    # Show GPU status
    if gpu:
        console.print(f"  [green]✓[/green] NVIDIA GPU detected — will use GPU acceleration")
    else:
        console.print(f"  [dim]○[/dim] No GPU detected — using CPU mode")

    if not Confirm.ask("\n[bold]Proceed with setup?[/bold]", default=True):
        console.print("[red]Setup cancelled. Exiting.[/red]")
        sys.exit(1)

    console.print()

    steps = {
        "torch": ("PyTorch", 0),
        "transformers": ("Transformers", 0),
        "florence2": ("Florence-2 Model", 0),
    }

    step_progress = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=False,
    ) as progress:
        for key, (label, _) in steps.items():
            task_id = progress.add_task(f"[cyan]{label}[/cyan]", total=100, start=False)
            step_progress[key] = task_id

        current_step = None
        for event in run_setup(gpu=gpu):
            step = event.get("step", "")
            status_msg = event.get("status", "")
            pct = event.get("progress", 0)
            is_error = event.get("error", False)
            done_step = event.get("done_step", False)
            all_done = event.get("all_done", False)

            if step in step_progress:
                task_id = step_progress[step]
                if current_step != step:
                    progress.start_task(task_id)
                    current_step = step
                progress.update(task_id, completed=pct, description=f"[cyan]{steps[step][0]}[/cyan]  [dim]{status_msg}[/dim]")

                if is_error:
                    progress.update(task_id, description=f"[red]{steps[step][0]} — FAILED: {status_msg}[/red]")
                    console.print(f"\n[red]Setup failed at step '{step}': {status_msg}[/red]")
                    sys.exit(1)

                if done_step:
                    skipped = event.get("skipped", False)
                    if skipped:
                        progress.update(task_id, description=f"[dim]{steps[step][0]} (already installed)[/dim]")
                    else:
                        progress.update(task_id, description=f"[green]{steps[step][0]} ✓[/green]")

            if all_done:
                break

    console.print()
    console.print(Panel("[bold green]✓ Setup complete! You can now use the CLI.[/bold green]", border_style="green"))
    console.print()


def _add_packages():
    """Add local packages dir to sys.path for ML imports."""
    try:
        from app.setup_manager import _add_packages_to_path
        _add_packages_to_path()
    except Exception:
        pass


# ─────────────────────────── CLI Commands ───────────────────────────────────

@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli(ctx):
    """[bold cyan]Watermark Remover[/bold cyan] — Remove watermarks from images and videos."""
    if ctx.invoked_subcommand is None:
        console.print(BANNER)
        console.print(ctx.get_help())


@cli.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_path", type=click.Path(path_type=Path))
@click.option("--auto", is_flag=True, help="Auto-detect watermark using Florence-2.")
@click.option("--mask-box", default=None, metavar="X1,Y1,X2,Y2", help="Manual region as 'x1,y1,x2,y2'.")
@click.option("--transparent", is_flag=True, help="Make watermark region transparent (PNG output).")
@click.option("--force-format", type=click.Choice(["PNG", "WEBP", "JPG", "MP4", "AVI"], case_sensitive=False), default=None)
@click.option("--frame-step", type=int, default=1, show_default=True, help="Process every Nth frame (video).")
@click.option("--target-fps", type=float, default=0.0, show_default=True, help="Output FPS (0 = keep original).")
@click.option("--max-bbox-percent", type=float, default=10.0, show_default=True)
def remove(
    input_path: Path,
    output_path: Path,
    auto: bool,
    mask_box: Optional[str],
    transparent: bool,
    force_format: Optional[str],
    frame_step: int,
    target_fps: float,
    max_bbox_percent: float,
):
    """Remove watermarks from IMAGE, VIDEO, or DIRECTORY."""
    _check_and_setup()
    _add_packages()

    from app.core.remover import parse_mask_box
    from app.core.image_video import process_image_or_video

    console.print(BANNER)

    # Show input info
    table = Table(show_header=False, box=rbox.SIMPLE, padding=(0, 1))
    table.add_row("[dim]Input[/dim]", f"[bold]{input_path}[/bold]")
    table.add_row("[dim]Output[/dim]", f"[bold]{output_path}[/bold]")
    table.add_row("[dim]Mode[/dim]", "[cyan]auto-detect[/cyan]" if auto else (f"[yellow]manual {mask_box}[/yellow]" if mask_box else "[red]none (will prompt)[/red]"))
    if transparent:
        table.add_row("[dim]Fill[/dim]", "transparent")
    console.print(Panel(table, title="[bold]Processing[/bold]", border_style="blue"))

    # Resolve mask
    resolved_mask: Optional[tuple] = None
    if mask_box:
        try:
            resolved_mask = parse_mask_box(mask_box)
        except ValueError as e:
            console.print(f"[red]Invalid --mask-box: {e}[/red]")
            sys.exit(1)
    elif not auto:
        # Prompt interactively
        console.print("\n[yellow]No mask specified. Options:[/yellow]")
        console.print("  [cyan]1[/cyan] Auto-detect watermark (requires internet on first use)")
        console.print("  [cyan]2[/cyan] Enter coordinates manually")
        choice = Prompt.ask("Choice", choices=["1", "2"], default="1")
        if choice == "1":
            auto = True
        else:
            coords = Prompt.ask("Enter mask box [dim](x1,y1,x2,y2)[/dim]")
            try:
                resolved_mask = parse_mask_box(coords)
            except ValueError as e:
                console.print(f"[red]Invalid coordinates: {e}[/red]")
                sys.exit(1)

    # Process with progress
    last_pct = [0]
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing...[/cyan]", total=100)

        def progress_cb(pct: int, status: str):
            if pct != last_pct[0]:
                last_pct[0] = pct
                progress.update(task, completed=pct, description=f"[cyan]{status}[/cyan]")

        try:
            result = process_image_or_video(
                input_path,
                output_path,
                mask_box=resolved_mask,
                transparent=transparent,
                force_format=(force_format.upper() if force_format else None),
                frame_step=frame_step,
                target_fps=target_fps,
                max_bbox_percent=max_bbox_percent,
                progress_callback=progress_cb,
            )
            progress.update(task, completed=100, description="[green]Done![/green]")
        except Exception as e:
            progress.stop()
            console.print(f"\n[red]Processing failed:[/red] {e}")
            sys.exit(1)

    # Result summary
    result_path = result if isinstance(result, Path) else Path(str(result))
    size_mb = result_path.stat().st_size / 1048576 if result_path.exists() else 0
    console.print()
    console.print(Panel(
        f"[bold green]✓ Success![/bold green]\n\n"
        f"Output: [cyan]{result_path}[/cyan]\n"
        f"Size:   [dim]{size_mb:.1f} MB[/dim]",
        border_style="green"
    ))


@cli.command()
def setup():
    """Run the first-time setup wizard."""
    from app.setup_manager import get_setup_status, _save_config, _load_config

    status = get_setup_status()
    console.print(BANNER)

    table = Table(title="Setup Status", box=rbox.ROUNDED)
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_row("GPU", "[green]Available[/green]" if status["gpu_available"] else "[dim]Not found (CPU mode)[/dim]")
    table.add_row("PyTorch", "[green]Installed[/green]" if status["torch_installed"] else "[yellow]Not installed[/yellow]")
    table.add_row("Transformers", "[green]Installed[/green]" if status["transformers_installed"] else "[yellow]Not installed[/yellow]")
    table.add_row("Florence-2 Model", "[green]Downloaded[/green]" if status["florence_downloaded"] else "[yellow]Not downloaded[/yellow]")
    table.add_row("Setup Complete", "[green]Yes[/green]" if status["complete"] else "[red]No[/red]")
    console.print(table)

    if not status["complete"]:
        if Confirm.ask("\nRun setup now?", default=True):
            # Reset complete flag so _check_and_setup runs
            cfg = _load_config()
            cfg["complete"] = False
            _save_config(cfg)
            _check_and_setup()
    else:
        console.print("\n[green]Everything is set up![/green]")


@cli.command()
def version():
    """Show version information."""
    try:
        import json
        vf = Path(__file__).parent / "version.json"
        v = json.load(open(vf))["version"]
    except Exception:
        v = "unknown"
    console.print(f"[cyan]Watermark Remover[/cyan] v{v}")


# Alias: `python cli.py input output [options]` as direct shortcut
@click.command("main", hidden=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_path", type=click.Path(path_type=Path))
@click.option("--auto", is_flag=True)
@click.option("--mask-box", default=None)
@click.option("--transparent", is_flag=True)
@click.option("--force-format", type=click.Choice(["PNG", "WEBP", "JPG", "MP4", "AVI"], case_sensitive=False), default=None)
@click.option("--frame-step", type=int, default=1)
@click.option("--target-fps", type=float, default=0.0)
@click.option("--max-bbox-percent", type=float, default=10.0)
@click.pass_context
def _legacy_main(ctx, **kwargs):
    """Legacy single-command mode (deprecated, use 'remove' subcommand)."""
    ctx.invoke(remove, **kwargs)


if __name__ == "__main__":
    # Support both `python cli.py remove ...` and `python cli.py INPUT OUTPUT ...`
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-") and sys.argv[1] not in ("remove", "setup", "version", "--help", "-h"):
        sys.argv.insert(1, "remove")
    cli()
