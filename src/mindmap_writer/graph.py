from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from mindmap_writer.models import (
    ChapterProcessingState,
    ChapterResult,
    PipelineState,
)
from mindmap_writer.nodes.check_missing import check_missing
from mindmap_writer.nodes.detect_chapters import detect_chapters, load_pdf
from mindmap_writer.nodes.extract_content import extract_content
from mindmap_writer.nodes.extract_headings import extract_headings
from mindmap_writer.nodes.format_markdown import format_and_validate
from mindmap_writer.nodes.review_structure import review_structure
from mindmap_writer.nodes.write_output import write_output


def fan_out_chapters(state: PipelineState, config: RunnableConfig) -> list[Send]:
    """Route each detected chapter to a parallel process_chapter node."""
    chapter_filter: set[int] | None = config.get("configurable", {}).get("chapter_filter")
    sends = []
    for chapter in state["chapters"]:
        if chapter_filter and chapter.chapter_number not in chapter_filter:
            continue
        chapter_pages = state["page_images"][chapter.start_page : chapter.end_page + 1]
        sends.append(
            Send(
                "process_chapter",
                {
                    "chapter": chapter,
                    "chapter_pages": chapter_pages,
                    "chapter_headings": [],
                    "chapter_markdown": "",
                    "chapter_missing": [],
                    "chapter_valid": False,
                    "chapter_retry": 0,
                    "chapter_results": [],
                },
            )
        )
    return sends


def should_retry(state: ChapterProcessingState) -> str:
    """Conditional edge: retry if validation failed and retries remain."""
    if not state["chapter_valid"] and state["chapter_retry"] < 2:
        return "extract_headings"
    return "review_structure"


def collect_result(state: ChapterProcessingState) -> dict:
    """Convert chapter subgraph state into a ChapterResult for the parent."""
    return {
        "chapter_results": [
            ChapterResult(
                chapter_number=state["chapter"].chapter_number,
                title=state["chapter"].title,
                headings=state["chapter_headings"],
                content_markdown=state["chapter_markdown"],
                missing_topics=state["chapter_missing"],
                is_valid=state["chapter_valid"],
                retry_count=state["chapter_retry"],
            )
        ]
    }


def build_chapter_subgraph() -> StateGraph:
    """Build the per-chapter processing subgraph."""
    sg = StateGraph(ChapterProcessingState)

    sg.add_node("extract_headings", extract_headings)
    sg.add_node("extract_content", extract_content)
    sg.add_node("check_missing", check_missing)
    sg.add_node("format_and_validate", format_and_validate)
    sg.add_node("review_structure", review_structure)
    sg.add_node("collect_result", collect_result)

    sg.add_edge(START, "extract_headings")
    sg.add_edge("extract_headings", "extract_content")
    sg.add_edge("extract_content", "check_missing")
    sg.add_edge("check_missing", "format_and_validate")
    sg.add_conditional_edges("format_and_validate", should_retry)
    sg.add_edge("review_structure", "collect_result")
    sg.add_edge("collect_result", END)

    return sg.compile()


def build_graph() -> StateGraph:
    """Build the top-level pipeline graph."""
    graph = StateGraph(PipelineState)

    graph.add_node("load_pdf", load_pdf)
    graph.add_node("detect_chapters", detect_chapters)
    graph.add_node("process_chapter", build_chapter_subgraph())
    graph.add_node("write_output", write_output)

    graph.add_edge(START, "load_pdf")
    graph.add_edge("load_pdf", "detect_chapters")
    graph.add_conditional_edges("detect_chapters", fan_out_chapters, ["process_chapter"])
    graph.add_edge("process_chapter", "write_output")
    graph.add_edge("write_output", END)

    return graph.compile()
