from __future__ import annotations

from langchain_core.messages import HumanMessage

from langchain_core.runnables import RunnableConfig

from mindmap_writer.config import AppConfig
from mindmap_writer.llm import create_text_llm
from mindmap_writer.models import ChapterProcessingState
from mindmap_writer.prompts import FORMAT_MARKDOWN_PROMPT
from mindmap_writer.utils import extract_text_from_response, timed_node, validate_markdown_structure


@timed_node("format_and_validate")
def format_and_validate(state: ChapterProcessingState, config: RunnableConfig) -> dict:
    """Format extracted content into bullet+tab markdown and validate structure."""
    app_config: AppConfig = config["configurable"]["app_config"]
    llm = create_text_llm(app_config)

    chapter = state["chapter"]
    headings = state["chapter_headings"]
    content_markdown = state["chapter_markdown"]

    headings_text = "\n".join(f"- {h}" for h in headings)
    prompt = FORMAT_MARKDOWN_PROMPT.format(
        chapter_title=chapter.title,
        headings=headings_text,
        raw_content=content_markdown,
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    formatted = extract_text_from_response(response.content).strip()

    # Remove any markdown code fences the LLM might have added
    if formatted.startswith("```"):
        lines = formatted.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        formatted = "\n".join(lines)

    is_valid = validate_markdown_structure(formatted)

    return {
        "chapter_markdown": formatted,
        "chapter_valid": is_valid,
        "chapter_retry": state["chapter_retry"] + 1,
    }
