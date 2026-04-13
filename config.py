"""Configuration management with auto-save and validation - expanded with 30+ settings."""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .platform_utils import get_config_dir

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"


@dataclass
class AppConfig:
    """Application configuration with defaults - 35+ configurable options."""

    # --- Appearance ---
    theme: str = "dark"
    font_size: int = 13
    window_width: int = 1400
    window_height: int = 900
    sidebar_width: int = 220
    compact_mode: bool = False
    show_article_previews: bool = True
    articles_per_page: int = 30
    highlight_high_relevance: bool = True
    high_relevance_threshold: float = 0.7

    # --- Fetching ---
    auto_refresh_enabled: bool = True
    auto_refresh_minutes: int = 30
    max_articles_per_source: int = 50
    fetch_timeout_seconds: int = 15
    max_concurrent_fetches: int = 6
    max_retries: int = 2
    retry_delay_seconds: int = 2
    fetch_on_startup: bool = True

    # --- Content Filtering ---
    relevance_threshold: float = 0.3
    show_read_articles: bool = True
    default_sort: str = "date"  # date, relevance, source
    categories_of_interest: list = field(default_factory=lambda: [
        "AI Agents", "Vibe Coding", "Local AI", "AI Models",
        "Breakthroughs", "AI Business", "AI Tools", "Open Source AI"
    ])
    blocked_keywords: list = field(default_factory=list)
    min_summary_length: int = 0

    # --- Notifications ---
    notification_on_fetch: bool = True
    notification_on_error: bool = True
    toast_duration_ms: int = 3000

    # --- Automation ---
    auto_score_articles: bool = True
    auto_generate_strategies: bool = False
    auto_cleanup_days: int = 90
    auto_backup_enabled: bool = False
    auto_backup_interval_hours: int = 24

    # --- Performance ---
    perf_logging_enabled: bool = True
    session_tracking_enabled: bool = True
    log_level: str = "INFO"
    db_vacuum_on_startup: bool = False

    # --- Export ---
    export_format: str = "markdown"
    export_include_summary: bool = True
    export_include_scores: bool = True
    export_max_articles: int = 500

    # --- Session Profile ---
    active_profile: str = "Default"

    def validate(self) -> list[str]:
        issues = []
        if self.font_size < 8 or self.font_size > 32:
            issues.append(f"Font size {self.font_size} out of range [8, 32]")
            self.font_size = max(8, min(32, self.font_size))
        if self.auto_refresh_minutes < 5 or self.auto_refresh_minutes > 1440:
            issues.append(f"Refresh interval {self.auto_refresh_minutes} out of range [5, 1440]")
            self.auto_refresh_minutes = max(5, min(1440, self.auto_refresh_minutes))
        if self.max_articles_per_source < 10 or self.max_articles_per_source > 200:
            self.max_articles_per_source = max(10, min(200, self.max_articles_per_source))
        if self.fetch_timeout_seconds < 5 or self.fetch_timeout_seconds > 60:
            self.fetch_timeout_seconds = max(5, min(60, self.fetch_timeout_seconds))
        if self.max_concurrent_fetches < 1 or self.max_concurrent_fetches > 20:
            self.max_concurrent_fetches = max(1, min(20, self.max_concurrent_fetches))
        if self.toast_duration_ms < 1000 or self.toast_duration_ms > 10000:
            self.toast_duration_ms = max(1000, min(10000, self.toast_duration_ms))
        if self.auto_cleanup_days < 7 or self.auto_cleanup_days > 365:
            self.auto_cleanup_days = max(7, min(365, self.auto_cleanup_days))
        if self.articles_per_page < 10 or self.articles_per_page > 100:
            self.articles_per_page = max(10, min(100, self.articles_per_page))
        return issues


def load_config() -> AppConfig:
    config_path = get_config_dir() / CONFIG_FILE
    config = AppConfig()
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            issues = config.validate()
            for issue in issues:
                logger.warning("Config issue: %s", issue)
        except Exception as e:
            logger.error("Failed to load config: %s", e)
    return config


def save_config(config: AppConfig) -> None:
    config_path = get_config_dir() / CONFIG_FILE
    try:
        config_path.write_text(
            json.dumps(asdict(config), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error("Failed to save config: %s", e)
