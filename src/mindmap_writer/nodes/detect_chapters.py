from __future__ import annotations

from langchain_core.messages import HumanMessage

from langchain_core.runnables import RunnableConfig

from mindmap_writer.config import AppConfig
from mindmap_writer.llm import create_vision_llm
from mindmap_writer.models import ChapterInfo, PipelineState
from mindmap_writer.pdf import load_pdf_as_images
from mindmap_writer.prompts import DETECT_CHAPTERS_PROMPT
from mindmap_writer.utils import build_vision_content, parse_json_from_response, timed_node


@timed_node("load_pdf")
def load_pdf(state: PipelineState, config: RunnableConfig) -> dict:
    """Load PDF and convert pages to base64 images."""
    app_config: AppConfig = config["configurable"]["app_config"]
    page_images = load_pdf_as_images(
        state["pdf_path"],
        dpi=app_config.processing.image_dpi,
        quality=app_config.processing.image_quality,
    )
    return {
        "page_images": page_images,
        "total_pages": len(page_images),
        "current_phase": "pdf_loaded",
    }


@timed_node("detect_chapters")
def detect_chapters(state: PipelineState, config: RunnableConfig) -> dict:
    """Send page images in batches to Vision LLM to identify chapter boundaries."""
    app_config: AppConfig = config["configurable"]["app_config"]
    llm = create_vision_llm(app_config)
    page_images = state["page_images"]
    batch_size = app_config.processing.chapter_detect_batch_size

    all_boundaries: list[dict] = []

    for batch_start in range(0, len(page_images), batch_size):
        batch_end = min(batch_start + batch_size, len(page_images))
        batch = page_images[batch_start:batch_end]

        content = build_vision_content(batch, start_page=batch_start)
        content.append({"type": "text", "text": DETECT_CHAPTERS_PROMPT})

        response = llm.invoke([HumanMessage(content=content)])
        boundaries = parse_json_from_response(response.content)
        if isinstance(boundaries, list):
            all_boundaries.extend(boundaries)

    # Sort by page number and build ChapterInfo list
    all_boundaries.sort(key=lambda b: b["page"])

    raw_chapters: list[ChapterInfo] = []
    for i, boundary in enumerate(all_boundaries):
        start_page = boundary["page"] - 1  # convert to 0-indexed
        if i + 1 < len(all_boundaries):
            end_page = all_boundaries[i + 1]["page"] - 2  # page before next chapter
        else:
            end_page = len(page_images) - 1

        raw_chapters.append(
            ChapterInfo(
                chapter_number=boundary.get("chapter_number", i + 1),
                title=boundary["title"],
                start_page=start_page,
                end_page=end_page,
            )
        )

    # Merge consecutive chapters with same number and title
    chapters: list[ChapterInfo] = []
    for ch in raw_chapters:
        if (
            chapters
            and chapters[-1].chapter_number == ch.chapter_number
            and chapters[-1].title == ch.title
        ):
            # Extend previous chapter's page range
            chapters[-1] = ChapterInfo(
                chapter_number=chapters[-1].chapter_number,
                title=chapters[-1].title,
                start_page=chapters[-1].start_page,
                end_page=ch.end_page,
            )
        else:
            chapters.append(ch)

    # Handle chapter number resets caused by a new major section (대단원).
    # When the chapter number decreases (e.g., Ch5 → Ch1 again), shift all
    # subsequent chapters so numbers remain globally unique.
    renumbered: list[ChapterInfo] = []
    offset = 0
    prev_num = 0
    for ch in chapters:
        if ch.chapter_number <= prev_num and prev_num > 0:
            offset += prev_num
        prev_num = ch.chapter_number
        renumbered.append(
            ChapterInfo(
                chapter_number=ch.chapter_number + offset,
                title=ch.title,
                start_page=ch.start_page,
                end_page=ch.end_page,
            )
        )

    return {"chapters": renumbered, "current_phase": "chapters_detected"}
