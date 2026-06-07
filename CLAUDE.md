# AI Intel Hub

Python desktop app (CustomTkinter) — AI industry intelligence tracker with RSS scraping, trend analysis, and monetization advice.

## Stack
- Python 3.11, CustomTkinter GUI
- feedparser, beautifulsoup4, requests for scraping
- SQLite database (database.py)
- SMTP/mailto email reports (emailer.py)

## Architecture
- `run.py` — entry point
- `scraper.py` — RSS/web scraping with retry logic
- `analyzer.py` — trend detection, keyword extraction, scoring
- `database.py` — SQLite data layer
- `config.py` — dataclass-based config with auto-save
- `strategy.py` — monetization strategy generator
- `ui/` — CustomTkinter GUI components

## Rules
- Use `uv` for package management, never `pip`
- All database changes must go through database.py, never raw SQL in other modules
- Keep GUI logic in ui/ separate from business logic

<!-- claude-backend:generated:start -->
# ai_intel_hub

## Overview

- **Files**: 29 (.py (27), .md (2))
- **Entry points**: `run.py`, `__main__.py`
- **Dependencies**: customtkinter, feedparser, beautifulsoup4, requests, Pillow, keyring
- **Key files**: `README.md`, `CLAUDE.md`, `requirements.txt`, `.gitignore`

## Structure

```
ui/  (11 files)
```

## Conventions

- Use `pathlib.Path` for all path operations
- Type hints are used extensively -- maintain them
- Use `logging.getLogger(__name__)` for all logging

## Modules

- `analyzer.py` -- Trend detection, keyword extraction, relevance scoring, and categorization
- `config.py` -- Configuration management with auto-save and validation - expanded with 30+ settings
- `database.py` -- SQLite database layer for articles, sources, strategies, and metadata
- `diagnostics.py` -- Comprehensive diagnostic report generator with fix suggestions and health scoring
- `emailer.py` -- Email module - compose and send intelligence reports via SMTP or mailto
- `exporter.py` -- Export articles, strategies, and reports in multiple formats
- `full_article_fetcher.py` -- Full article text fetcher — bridges auto_scraper and CDP for enrichment
- `perf_logger.py` -- Performance logger - tracks fetch times, errors, throughput, and bottlenecks
- `platform_utils.py` -- Cross-platform path utilities and system detection
- `run.py` -- Quick launcher - run this file directly: python run.py [entry]
- `scraper.py` -- RSS feed parser and web scraper with retry logic
- `session_manager.py` -- Session manager - tracks app sessions, profiles, and customizable behaviors
- `sources.py` -- Curated catalog of 50+ AI news sources - RSS feeds and scrape targets
- `strategy.py` -- Monetization strategy generator based on detected AI trends
- `ui/app.py` -- Main application window with sidebar navigation, status bar, session tracking, and auto-refresh
- `ui/dashboard.py` -- Dashboard view - stats, TOP 5 STANDOUTS, GROUNDBREAKER, trends, hot topics
- `ui/email_view.py` -- Email view - compose and send intelligence reports via email
- `ui/export_view.py` -- Export center - bulk URL copy, article exports, and file exports
- `ui/feed_view.py` -- Feed view - browse, search, filter, and read articles
- `ui/health_view.py` -- Health & Logs view - performance monitoring, bottleneck detection, session history
- `ui/settings_view.py` -- Expanded settings view - 30+ options, profiles, session customization, data management
- `ui/sources_view.py` -- Source manager view - add, edit, delete, toggle RSS sources
- `ui/strategy_view.py` -- Strategy view - browse, rate, and export monetization strategies
- `ui/theme.py` -- Theme system - dark/light mode colors, fonts, and styling constants
- `ui/widgets.py` -- Reusable styled widgets - cards, tags, search bar, stat cards

<!-- claude-backend:generated:end -->
