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
