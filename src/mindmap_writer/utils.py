from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable

# Global timing store — collected per run
_timing_records: dict[str, list[float]] = defaultdict(list)


def reset_timing() -> None:
    """Clear all timing records."""
    _timing_records.clear()


def get_timing_records() -> dict[str, list[float]]:
    """Return timing records (node_name -> list of durations in seconds)."""
    return dict(_timing_records)


def timed_node(name: str) -> Callable:
    """Decorator that records wall-clock time for a LangGraph node."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            result = fn(*args, **kwargs)
            elapsed = time.time() - start
            _timing_records[name].append(elapsed)
            return result
        return wrapper
    return decorator


def build_vision_content(page_images: list[str], start_page: int = 0) -> list[dict]:
    """Build a list of content blocks for a vision LLM message."""
    content: list[dict] = []
    for i, img_b64 in enumerate(page_images):
        page_num = start_page + i + 1
        content.append({"type": "text", "text": f"--- Page {page_num} ---"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
        })
    return content


def extract_text_from_response(content: str | list) -> str:
    """Normalize LLM response content to a plain string.

    Gemini may return a list of content blocks instead of a string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)


def parse_json_from_response(text: str | list) -> dict | list:
    """Extract JSON from an LLM response that may contain markdown fences."""
    text = extract_text_from_response(text)
    # Try to find JSON in code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    # Try parsing the whole response
    return json.loads(text.strip())


def sanitize_filename(title: str) -> str:
    """Convert a title to a safe filename component."""
    safe = re.sub(r"[^\w\s\-]", "", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    return safe[:50]


def cap_tab_depth(text: str, max_tabs: int = 4) -> str:
    """Hard-cap the maximum tab indentation level.

    Content exceeding max_tabs is pulled back to max_tabs so it never breaks
    the Obsidian mindmap renderer regardless of what the LLM outputs.
    After merging (which adds 1 extra tab), chapter content at max_tabs
    becomes max_tabs+1 in the merged file — still within a safe render depth.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        if line.strip():
            current_tabs = len(line) - len(line.lstrip("\t"))
            if current_tabs > max_tabs:
                line = "\t" * max_tabs + line.lstrip("\t")
        result.append(line)
    return "\n".join(result)


def validate_markdown_structure(markdown: str) -> bool:
    """Validate that markdown follows bullet+tab indent rules."""
    lines = markdown.strip().split("\n")
    if not lines:
        return False

    prev_depth = 0
    for line in lines:
        if not line.strip():
            continue

        # Count leading tabs
        tabs = len(line) - len(line.lstrip("\t"))
        rest = line.lstrip("\t")

        # Every line must start with "- "
        if not rest.startswith("- "):
            return False

        # Max 5 levels (0–4 tabs); deeper nesting is allowed when content warrants it
        if tabs > 4:
            return False

        # Indentation can only increase by 1 at a time
        if tabs > prev_depth + 1:
            return False

        prev_depth = tabs

    return True
