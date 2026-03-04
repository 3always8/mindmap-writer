from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="mindmap-writer",
    help="Convert PDF study materials to Obsidian mindmap markdown files.",
)
console = Console()


@app.command()
def convert(
    pdf: Path = typer.Argument(..., help="Path to the input PDF file", exists=True),
    output: Path = typer.Option("./output", "--output", "-o", help="Output directory"),
    config_path: Path = typer.Option(
        "config.yaml", "--config", "-c", help="Config file path"
    ),
    chapters: str = typer.Option(
        None, "--chapters", help="Process only these chapters (e.g., '1,3,5')"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Detect chapters only, don't extract"
    ),
) -> None:
    """Convert a PDF to mindmap markdown files."""
    from mindmap_writer.config import load_config
    from mindmap_writer.graph import build_graph

    cfg = load_config(str(config_path))

    from mindmap_writer.utils import reset_timing
    reset_timing()

    graph = build_graph()

    # Create per-PDF subfolder: output/MA_Final/, output/Intermediate_Accounting_Final/
    pdf_stem = pdf.stem.replace(" ", "_")
    output_subdir = output / pdf_stem

    initial_state = {
        "pdf_path": str(pdf),
        "page_images": [],
        "total_pages": 0,
        "chapters": [],
        "chapter_results": [],
        "output_dir": str(output_subdir),
        "current_phase": "starting",
        "errors": [],
    }

    chapter_filter = None
    if chapters:
        chapter_filter = {int(c.strip()) for c in chapters.split(",")}

    run_config = {
        "configurable": {"app_config": cfg, "chapter_filter": chapter_filter},
        "max_concurrency": cfg.processing.max_concurrency,
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing PDF...", total=None)

        if dry_run:
            # Only run load_pdf and detect_chapters
            from mindmap_writer.nodes.detect_chapters import detect_chapters, load_pdf

            progress.update(task, description="Loading PDF...")
            loaded = load_pdf(initial_state, {"configurable": {"app_config": cfg}})
            initial_state.update(loaded)

            progress.update(task, description="Detecting chapters...")
            detected = detect_chapters(
                initial_state, {"configurable": {"app_config": cfg}}
            )
            initial_state.update(detected)

            progress.stop()
            console.print("\n[bold]Detected chapters:[/]")
            for ch in initial_state["chapters"]:
                console.print(
                    f"  Chapter {ch.chapter_number}: {ch.title} "
                    f"(pages {ch.start_page + 1}-{ch.end_page + 1})"
                )
            return

        # Full pipeline
        for event in graph.stream(initial_state, config=run_config):
            for node_name, state_update in event.items():
                if isinstance(state_update, dict):
                    phase = state_update.get("current_phase", "")
                    if phase:
                        progress.update(
                            task, description=f"[bold blue]{phase}[/bold blue]"
                        )
                    # Show chapter detection results
                    chapters_detected = state_update.get("chapters")
                    if chapters_detected:
                        progress.stop()
                        console.print(f"\n[bold]Detected {len(chapters_detected)} chapters[/]")
                        for ch in chapters_detected:
                            console.print(
                                f"  Chapter {ch.chapter_number}: {ch.title} "
                                f"(pages {ch.start_page + 1}-{ch.end_page + 1})"
                            )
                        console.print()
                        progress.start()

    # Print timing report
    from mindmap_writer.utils import get_timing_records
    timing = get_timing_records()
    if timing:
        console.print("\n[bold]Timing Report:[/]")
        total = 0.0
        for node_name, durations in sorted(timing.items()):
            avg = sum(durations) / len(durations)
            total_node = sum(durations)
            total += total_node
            if len(durations) > 1:
                console.print(
                    f"  {node_name}: {avg:.1f}s avg × {len(durations)} calls = {total_node:.1f}s"
                )
            else:
                console.print(f"  {node_name}: {total_node:.1f}s")
        console.print(f"  [bold]Total (sequential sum): {total:.1f}s[/]")

    console.print(f"\n[bold green]Done![/] Output written to [bold]{output_subdir}/[/]")


@app.command()
def list_chapters(
    pdf: Path = typer.Argument(..., help="Path to the input PDF file", exists=True),
    config_path: Path = typer.Option(
        "config.yaml", "--config", "-c", help="Config file path"
    ),
) -> None:
    """Detect and list chapters in a PDF without processing."""
    from mindmap_writer.config import load_config
    from mindmap_writer.nodes.detect_chapters import detect_chapters, load_pdf

    cfg = load_config(str(config_path))
    run_config = {"configurable": {"app_config": cfg}}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading PDF...", total=None)

        state = {
            "pdf_path": str(pdf),
            "page_images": [],
            "total_pages": 0,
            "chapters": [],
            "chapter_results": [],
            "output_dir": "",
            "current_phase": "",
            "errors": [],
        }

        loaded = load_pdf(state, run_config)
        state.update(loaded)

        progress.update(task, description="Detecting chapters...")
        detected = detect_chapters(state, run_config)
        state.update(detected)

    console.print(f"\n[bold]PDF: {pdf.name}[/] ({state['total_pages']} pages)")
    console.print(f"[bold]Detected {len(state['chapters'])} chapters:[/]\n")

    for ch in state["chapters"]:
        pages = ch.end_page - ch.start_page + 1
        console.print(
            f"  [bold cyan]Chapter {ch.chapter_number}[/]: {ch.title} "
            f"({pages} pages, p.{ch.start_page + 1}-{ch.end_page + 1})"
        )


if __name__ == "__main__":
    app()
