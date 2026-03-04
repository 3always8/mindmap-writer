from __future__ import annotations

from langchain_core.messages import HumanMessage

from langchain_core.runnables import RunnableConfig

from mindmap_writer.config import AppConfig
from mindmap_writer.llm import create_vision_llm
from mindmap_writer.models import ChapterProcessingState
from mindmap_writer.prompts import EXTRACT_HEADINGS_PROMPT
from mindmap_writer.utils import build_vision_content, parse_json_from_response, timed_node


@timed_node("extract_headings")
def extract_headings(state: ChapterProcessingState, config: RunnableConfig) -> dict:
    """Extract Level 1 headings from chapter pages using Vision LLM."""
    app_config: AppConfig = config["configurable"]["app_config"]
    llm = create_vision_llm(app_config)

    chapter = state["chapter"]
    page_images = state["chapter_pages"]

    content = build_vision_content(page_images, start_page=chapter.start_page)
    content.append({"type": "text", "text": EXTRACT_HEADINGS_PROMPT})

    response = llm.invoke([HumanMessage(content=content)])
    headings = parse_json_from_response(response.content)

    if not isinstance(headings, list):
        headings = []

    return {"chapter_headings": headings}
