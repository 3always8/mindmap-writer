from __future__ import annotations

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from mindmap_writer.config import AppConfig
from mindmap_writer.llm import create_text_llm
from mindmap_writer.models import ChapterProcessingState
from mindmap_writer.prompts import REVIEW_STRUCTURE_PROMPT
from mindmap_writer.utils import extract_text_from_response, timed_node, validate_markdown_structure


_MAX_REVIEW_RETRIES = 2


@timed_node("review_structure")
def review_structure(state: ChapterProcessingState, config: RunnableConfig) -> dict:
    """Ask an LLM to read the markdown and fix incorrect tab relationships."""
    app_config: AppConfig = config["configurable"]["app_config"]
    llm = create_text_llm(app_config)

    chapter = state["chapter"]
    content_markdown = state["chapter_markdown"]
    headings = state["chapter_headings"]

    headings_text = "\n".join(f"- {h}" for h in headings) if headings else "(없음)"
    prompt = REVIEW_STRUCTURE_PROMPT.format(
        chapter_title=chapter.title,
        headings=headings_text,
        content=content_markdown,
    )

    for _ in range(_MAX_REVIEW_RETRIES + 1):
        response = llm.invoke([HumanMessage(content=prompt)])
        reviewed = extract_text_from_response(response.content).strip()

        # Remove code fences the LLM might have added
        if reviewed.startswith("```"):
            lines = reviewed.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            reviewed = "\n".join(lines)

        # Only accept the reviewed output if it passes structural validation
        if validate_markdown_structure(reviewed):
            return {"chapter_markdown": reviewed, "chapter_valid": True}

    # All retries exhausted — keep original content unchanged
    return {}
