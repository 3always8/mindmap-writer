# mindmap-writer

Convert PDF study materials into Obsidian-ready mindmap markdown files using Vision LLM + LangGraph.

## Overview

mindmap-writer processes a PDF (e.g., a textbook or lecture notes), automatically detects chapters, extracts structured content using a vision model, and writes one `.md` file per chapter in Obsidian-compatible bullet/indented format — plus an `index.md` linking them all.

**Pipeline:**

```
PDF → load pages → detect chapters → [parallel per-chapter processing] → write .md files
                                         ↓
                               extract headings
                                         ↓
                               extract content
                                         ↓
                               check missing topics
                                         ↓
                               format & validate (retry up to 2×)
```

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Google AI API key (Gemini) and/or Anthropic API key

## Setup

```bash
# Clone and install
git clone https://github.com/your-username/mindmap-writer.git
cd mindmap-writer
uv sync

# Copy and fill in API keys
cp .env.example .env
```

Edit `.env`:

```
GOOGLE_API_KEY=AI...
ANTHROPIC_API_KEY=sk-ant-...   # optional, not used by default config
```

## Usage

### Convert a PDF

```bash
uv run mindmap-writer convert path/to/your.pdf
```

Output is written to `./output/<pdf-filename>/`, one `.md` file per detected chapter plus an `index.md`.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output`, `-o` | `./output` | Base output directory |
| `--config`, `-c` | `config.yaml` | Config file path |
| `--chapters` | all | Process only specific chapters, e.g. `--chapters 1,3,5` |
| `--dry-run` | false | Detect chapters only, skip extraction |

**Examples:**

```bash
# Custom output directory
uv run mindmap-writer convert lecture.pdf --output ~/obsidian/vault/notes

# Process only chapters 2 and 4
uv run mindmap-writer convert textbook.pdf --chapters 2,4

# Preview detected chapters without processing
uv run mindmap-writer convert textbook.pdf --dry-run
```

### List chapters without processing

```bash
uv run mindmap-writer list-chapters path/to/your.pdf
```

Prints each detected chapter number, title, and page range.

## Input

- **File type:** PDF (`.pdf`)
- **Best results with:** textbooks, lecture slides, structured study materials with chapter headings
- The vision model reads pages as images, so scanned PDFs work too

## Output

Given input `MA Final.pdf`, output is written to `./output/MA_Final/`:

```
output/
└── MA_Final/
    ├── index.md                                        ← Obsidian links to all chapters
    ├── chapter_03_Cost_Reporting.md
    ├── chapter_04_Standard_Costing.md
    └── ...
```

Each chapter file is a nested bullet-point mindmap in Obsidian markdown:

```markdown
- Chapter 3. Cost Reporting
  - A. Variable vs Absorption Costing
    - Variable costing
      - Product cost: Variable DM, DL, Variable OH
      - Period cost: Fixed OH, S&A
    ...
```

`index.md` contains Obsidian wikilinks to each chapter file:

```markdown
- Mindmap Index
	- [[chapter_03_Cost_Reporting|Chapter 3: Cost Reporting]]
	- [[chapter_04_Standard_Costing|Chapter 4: Standard Costing]]
```

## Configuration

Edit `config.yaml` to change models or processing parameters:

```yaml
models:
  vision:
    provider: "google"
    model: "gemini-flash-latest"   # vision model for page reading
    temperature: 0.1
  text:
    provider: "google"
    model: "gemini-flash-latest"   # text model for formatting

processing:
  chapter_detect_batch_size: 10    # pages per batch for chapter detection
  max_pages_per_vision_call: 15    # pages sent to vision model at once
  max_retries: 2                   # retry count if validation fails
  max_concurrency: 3               # parallel chapter processing
  image_dpi: 150                   # PDF-to-image resolution
  image_quality: 85                # JPEG quality for page images

output:
  dir: "./output"
  create_index: true               # generate index.md
```

## License

MIT
