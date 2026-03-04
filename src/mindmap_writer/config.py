from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ModelConfig(BaseModel):
    provider: str = "google"
    model: str = "gemini-flash-latest"
    temperature: float = 0.1
    max_tokens: int = 8192


class ProcessingConfig(BaseModel):
    chapter_detect_batch_size: int = 10
    max_pages_per_vision_call: int = 15
    max_retries: int = 2
    max_concurrency: int = 3
    image_dpi: int = 150
    image_quality: int = 85


class OutputConfig(BaseModel):
    dir: str = "./output"
    filename_pattern: str = "chapter_{num:02d}_{title}.md"
    create_index: bool = True
    merge_line_threshold: int = 500


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    google_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


class AppConfig(BaseModel):
    settings: Settings
    vision_model: ModelConfig
    text_model: ModelConfig
    processing: ProcessingConfig
    output: OutputConfig


def load_config(config_path: str = "config.yaml") -> AppConfig:
    file_config: dict = {}
    if Path(config_path).exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f) or {}

    return AppConfig(
        settings=Settings(),
        vision_model=ModelConfig(**file_config.get("models", {}).get("vision", {})),
        text_model=ModelConfig(**file_config.get("models", {}).get("text", {})),
        processing=ProcessingConfig(**file_config.get("processing", {})),
        output=OutputConfig(**file_config.get("output", {})),
    )
