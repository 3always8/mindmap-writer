from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel


class ChapterInfo(BaseModel):
    """Detected chapter metadata."""

    chapter_number: int
    title: str
    start_page: int  # 0-indexed
    end_page: int  # 0-indexed, inclusive


class ChapterResult(BaseModel):
    """Processed output for a single chapter."""

    chapter_number: int
    title: str
    headings: list[str]
    content_markdown: str
    missing_topics: list[str]
    is_valid: bool
    retry_count: int = 0


class PipelineState(TypedDict):
    """Top-level graph state."""

    pdf_path: str
    page_images: list[str]  # base64-encoded JPEG
    total_pages: int
    chapters: list[ChapterInfo]
    chapter_results: Annotated[list[ChapterResult], operator.add]
    output_dir: str
    current_phase: str
    errors: Annotated[list[str], operator.add]


class ChapterProcessingState(TypedDict):
    """State for per-chapter subgraph (used via Send).

    Field names deliberately avoid overlap with PipelineState
    to prevent LangGraph key conflicts on concurrent writes.
    """

    chapter: ChapterInfo
    chapter_pages: list[str]  # base64 images for this chapter only
    chapter_headings: list[str]
    chapter_markdown: str
    chapter_missing: list[str]
    chapter_valid: bool
    chapter_retry: int
    # Output field — maps back to parent PipelineState.chapter_results
    chapter_results: Annotated[list[ChapterResult], operator.add]
