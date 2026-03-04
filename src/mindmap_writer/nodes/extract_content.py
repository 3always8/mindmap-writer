from __future__ import annotations

from langchain_core.messages import HumanMessage

from langchain_core.runnables import RunnableConfig

from mindmap_writer.config import AppConfig
from mindmap_writer.llm import create_vision_llm
from mindmap_writer.models import ChapterProcessingState
from mindmap_writer.prompts import EXTRACT_CONTENT_PROMPT
from mindmap_writer.utils import build_vision_content, extract_text_from_response, timed_node


@timed_node("extract_content")
def extract_content(state: ChapterProcessingState, config: RunnableConfig) -> dict:
    """Extract L2/L3 content for each heading using Vision LLM."""
    app_config: AppConfig = config["configurable"]["app_config"]
    llm = create_vision_llm(app_config)
    max_pages = app_config.processing.max_pages_per_vision_call

    chapter = state["chapter"]
    page_images = state["chapter_pages"]
    headings = state["chapter_headings"]

    headings_text = "\n".join(f"- {h}" for h in headings)
    prompt = EXTRACT_CONTENT_PROMPT.format(headings=headings_text)

    if len(page_images) <= max_pages:
        # Send all pages in one call
        content = build_vision_content(page_images, start_page=chapter.start_page)
        content.append({"type": "text", "text": prompt})
        response = llm.invoke([HumanMessage(content=content)])
        return {"chapter_markdown": extract_text_from_response(response.content)}

    # Split into chunks for large chapters
    content_sections: list[str] = []
    for chunk_start in range(0, len(page_images), max_pages):
        chunk_end = min(chunk_start + max_pages, len(page_images))
        chunk = page_images[chunk_start:chunk_end]

        content = build_vision_content(
            chunk, start_page=chapter.start_page + chunk_start
        )
        content.append({"type": "text", "text": prompt})
        response = llm.invoke([HumanMessage(content=content)])
        content_sections.append(extract_text_from_response(response.content))

    return {"chapter_markdown": "\n".join(content_sections)}
