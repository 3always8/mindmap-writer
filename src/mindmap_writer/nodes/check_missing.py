from __future__ import annotations

from langchain_core.messages import HumanMessage

from langchain_core.runnables import RunnableConfig

from mindmap_writer.config import AppConfig
from mindmap_writer.llm import create_vision_llm
from mindmap_writer.models import ChapterProcessingState
from mindmap_writer.prompts import CHECK_MISSING_PROMPT, SUPPLEMENT_PROMPT
from mindmap_writer.utils import build_vision_content, extract_text_from_response, parse_json_from_response, timed_node


@timed_node("check_missing")
def check_missing(state: ChapterProcessingState, config: RunnableConfig) -> dict:
    """Compare extracted markdown against original pages, supplement if needed."""
    app_config: AppConfig = config["configurable"]["app_config"]
    llm = create_vision_llm(app_config)

    chapter = state["chapter"]
    page_images = state["chapter_pages"]
    content_markdown = state["chapter_markdown"]
    headings = state["chapter_headings"]

    headings_text = "\n".join(f"- {h}" for h in headings)
    prompt = CHECK_MISSING_PROMPT.format(
        current_markdown=content_markdown,
        headings=headings_text,
    )

    content = build_vision_content(page_images, start_page=chapter.start_page)
    content.append({"type": "text", "text": prompt})

    response = llm.invoke([HumanMessage(content=content)])

    try:
        result = parse_json_from_response(response.content)
        missing_topics = result.get("missing_topics", [])
    except (ValueError, KeyError):
        missing_topics = []

    if not missing_topics:
        return {"chapter_missing": []}

    # Supplement missing content
    missing_text = "\n".join(f"- {t}" for t in missing_topics)
    supplement_prompt = SUPPLEMENT_PROMPT.format(
        missing_topics=missing_text,
        current_markdown=content_markdown,
    )

    supplement_content = build_vision_content(page_images, start_page=chapter.start_page)
    supplement_content.append({"type": "text", "text": supplement_prompt})

    supplement_response = llm.invoke([HumanMessage(content=supplement_content)])

    # Append supplementary content
    supplement_text = extract_text_from_response(supplement_response.content)
    updated_markdown = content_markdown.rstrip() + "\n" + supplement_text.strip()

    return {
        "chapter_markdown": updated_markdown,
        "chapter_missing": missing_topics,
    }
