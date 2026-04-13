# AI Intel Hub

AI Industry Intelligence Tracker & Monetization Advisor - a desktop application that continuously tracks AI developments and proposes monetization strategies.

## Features

- **54 curated AI sources** across 10 categories (AI Agents, Vibe Coding, Local AI, AI Models, Breakthroughs, AI Business, AI Tools, Open Source AI, News, Research)
- **Top 5 Standouts + Groundbreaker** detection with composite scoring
- **20 monetization strategy templates** generated from real trend data
- **Bulk URL export** in 7 formats (AI Prompt, plain, markdown, CSV, JSON, numbered, titled)
- **Email integration** (Gmail compose, SMTP, mailto)
- **Deep GitHub scanning** (trending + topics + search across 27 pages)
- **Health monitoring** with bottleneck detection and fix suggestions
- **35+ configurable settings** with 5 session profiles
- **Performance logging** and session tracking
- **Dark/light theme** with polished CustomTkinter UI

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Or double-click `start.bat` on Windows.

## Requirements

- Python 3.10+
- customtkinter, feedparser, beautifulsoup4, requests, Pillow

## Architecture

```
ai_intel_hub/
  config.py            # 35+ settings with JSON persistence
  database.py          # SQLite with WAL mode
  sources.py           # 54 curated RSS feeds
  scraper.py           # RSS + deep GitHub scraping
  analyzer.py          # NLP scoring + standout/groundbreaker detection
  strategy.py          # Monetization strategy engine
  exporter.py          # 7 export formats + bulk URL copy
  emailer.py           # Gmail/SMTP/mailto integration
  perf_logger.py       # Performance tracking
  session_manager.py   # Session profiles + history
  diagnostics.py       # Health scoring + reports
  ui/                  # CustomTkinter views (9 tabs)
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+R | Refresh all feeds |
| Ctrl+D | Dashboard |
| Ctrl+F | Focus search |
| Ctrl+E | Export center |
| Ctrl+M | Email |
| Ctrl+H | Health & Logs |
| F5 | Refresh current view |

## License

MIT
