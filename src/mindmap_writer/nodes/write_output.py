from __future__ import annotations

from pathlib import Path

from langchain_core.runnables import RunnableConfig

from mindmap_writer.config import AppConfig
from mindmap_writer.models import ChapterResult, PipelineState
from mindmap_writer.utils import sanitize_filename

FRONTMATTER = "---\nmindmap-plugin: markdown\n---\n\n"


def write_output(state: PipelineState, config: RunnableConfig) -> dict:
    """Write individual .md files per chapter, an index.md, and merged files."""
    output_dir = Path(state["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg: AppConfig = config.get("configurable", {}).get("app_config")
    threshold = cfg.output.merge_line_threshold if cfg else 500

    results = sorted(state["chapter_results"], key=lambda r: r.chapter_number)

    filenames: list[tuple[int, str, str]] = []
    for result in results:
        safe_title = sanitize_filename(result.title)
        filename = f"chapter_{result.chapter_number:02d}_{safe_title}.md"
        filepath = output_dir / filename
        filepath.write_text(FRONTMATTER + result.content_markdown, encoding="utf-8")
        filenames.append((result.chapter_number, result.title, filename))

    # Write index.md with Obsidian wikilinks
    index_lines = ["- Mindmap Index"]
    for num, title, fname in filenames:
        link_name = fname[:-3]  # remove .md extension
        index_lines.append(f"\t- [[{link_name}|Chapter {num}: {title}]]")

    index_path = output_dir / "index.md"
    index_path.write_text(FRONTMATTER + "\n".join(index_lines), encoding="utf-8")

    # Write merged files (uses result.content_markdown directly to avoid duplicate frontmatter)
    _write_merged(output_dir, results, threshold)

    return {"current_phase": "complete"}


def _write_merged(output_dir: Path, results: list[ChapterResult], threshold: int) -> None:
    """Merge chapters into one or more combined files split by line count.

    Uses result.content_markdown (without frontmatter) and adds one frontmatter
    at the top of each merged file.

    Naming:
      - Single group  → {stem}.md              (e.g. MA_Final.md)
      - Multiple groups → {stem}_{first}_to_{last}.md  (e.g. MA_Final_1_to_4.md)
    """
    if not results:
        return

    pdf_stem = output_dir.name  # e.g. "MA_Final"

    # Greedily pack chapters into groups within the line threshold
    groups: list[list[tuple[int, str]]] = []
    current_group: list[tuple[int, str]] = []
    current_lines = 0

    for result in results:
        content = result.content_markdown
        line_count = content.count("\n") + 1
        if current_group and current_lines + line_count > threshold:
            groups.append(current_group)
            current_group = [(result.chapter_number, content)]
            current_lines = line_count
        else:
            current_group.append((result.chapter_number, content))
            current_lines += line_count

    if current_group:
        groups.append(current_group)

    # Only write merged files for groups that stay within the threshold.
    # Groups that exceed it (e.g. a single chapter larger than the threshold)
    # are left as individual chapter files only.
    writable = [
        g for g in groups
        if sum(content.count("\n") + 1 for _, content in g) < threshold
    ]

    # Write each writable group
    for group in writable:
        first_ch = group[0][0]
        last_ch = group[-1][0]

        if len(writable) == 1:
            out_filename = f"{pdf_stem}.md"
            root_label = f"- {pdf_stem}"
        else:
            out_filename = f"{pdf_stem}_{first_ch}_to_{last_ch}.md"
            root_label = f"- {pdf_stem} Ch.{first_ch}-{last_ch}"

        # Indent every content line by one tab and strip blank lines,
        # then wrap under a single root node so mindmap has exactly one root.
        indented_parts = []
        for _, content in group:
            indented = "\n".join(
                "\t" + line for line in content.split("\n") if line
            )
            indented_parts.append(indented)

        body = root_label + "\n" + "\n".join(indented_parts)

        (output_dir / out_filename).write_text(FRONTMATTER + body, encoding="utf-8")
