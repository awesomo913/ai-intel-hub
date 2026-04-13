"""Session manager - tracks app sessions, profiles, and customizable behaviors."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .platform_utils import get_data_dir
from .perf_logger import log_event

logger = logging.getLogger(__name__)

SESSIONS_FILE = "sessions.json"
PROFILES_FILE = "profiles.json"

# --- Session Tracking ---

class SessionTracker:
    """Track current app session - start time, actions, duration."""

    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()
        self.actions = []
        self.fetch_count = 0
        self.articles_fetched = 0
        self.errors = []
        self.views_visited = set()

        log_event("session_start", details={"session_id": self.session_id})

    def log_action(self, action: str, details: str = ""):
        entry = {
            "time": datetime.now().isoformat(),
            "elapsed_s": round(time.time() - self.start_time, 1),
            "action": action,
            "details": details,
        }
        self.actions.append(entry)

    def log_view(self, view_name: str):
        self.views_visited.add(view_name)
        self.log_action("view_switch", view_name)

    def log_fetch(self, source: str, articles: int, duration_ms: float, success: bool, error: str = ""):
        self.fetch_count += 1
        self.articles_fetched += articles
        if not success:
            self.errors.append({"source": source, "error": error})
        log_event("source_fetch", source=source, duration_ms=duration_ms,
                  success=success, articles_count=articles, error_msg=error)

    def log_full_fetch(self, total_new: int, total_sources: int, errors: int, duration_ms: float):
        log_event("full_fetch", duration_ms=duration_ms, success=errors == 0,
                  articles_count=total_new,
                  details={"sources": total_sources, "errors": errors})

    def get_summary(self) -> dict:
        duration = time.time() - self.start_time
        return {
            "session_id": self.session_id,
            "started": datetime.fromtimestamp(self.start_time).isoformat(),
            "duration_minutes": round(duration / 60, 1),
            "actions_count": len(self.actions),
            "fetch_count": self.fetch_count,
            "articles_fetched": self.articles_fetched,
            "errors_count": len(self.errors),
            "views_visited": list(self.views_visited),
        }

    def save(self):
        """Save session summary to history file."""
        path = get_data_dir() / SESSIONS_FILE
        history = []
        if path.exists():
            try:
                history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        history.append(self.get_summary())
        # Keep last 100 sessions
        history = history[-100:]
        try:
            path.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save session: %s", e)

        log_event("session_end", duration_ms=(time.time() - self.start_time) * 1000,
                  details=self.get_summary())


def get_session_history(limit: int = 20) -> list[dict]:
    """Get recent session history."""
    path = get_data_dir() / SESSIONS_FILE
    if not path.exists():
        return []
    try:
        history = json.loads(path.read_text(encoding="utf-8"))
        return history[-limit:]
    except Exception:
        return []


# --- Session Profiles ---

DEFAULT_PROFILES = {
    "Default": {
        "description": "Balanced settings for general use",
        "auto_refresh_enabled": True,
        "auto_refresh_minutes": 30,
        "max_articles_per_source": 50,
        "categories_of_interest": [
            "AI Agents", "Vibe Coding", "Local AI", "AI Models",
            "Breakthroughs", "AI Business", "AI Tools", "Open Source AI"
        ],
        "relevance_threshold": 0.3,
        "fetch_timeout_seconds": 15,
        "max_concurrent_fetches": 6,
        "show_read_articles": True,
        "notification_on_fetch": True,
        "auto_score_articles": True,
        "auto_generate_strategies": False,
    },
    "Speed Reader": {
        "description": "High volume - fetch everything quickly",
        "auto_refresh_enabled": True,
        "auto_refresh_minutes": 10,
        "max_articles_per_source": 100,
        "categories_of_interest": [
            "AI Agents", "Vibe Coding", "Local AI", "AI Models",
            "Breakthroughs", "AI Business", "AI Tools", "Open Source AI"
        ],
        "relevance_threshold": 0.0,
        "fetch_timeout_seconds": 10,
        "max_concurrent_fetches": 10,
        "show_read_articles": False,
        "notification_on_fetch": False,
        "auto_score_articles": True,
        "auto_generate_strategies": False,
    },
    "Deep Diver": {
        "description": "Focus on high-quality research and breakthroughs",
        "auto_refresh_enabled": True,
        "auto_refresh_minutes": 60,
        "max_articles_per_source": 30,
        "categories_of_interest": [
            "AI Research", "Breakthroughs", "AI Models", "Open Source AI"
        ],
        "relevance_threshold": 0.5,
        "fetch_timeout_seconds": 20,
        "max_concurrent_fetches": 4,
        "show_read_articles": True,
        "notification_on_fetch": True,
        "auto_score_articles": True,
        "auto_generate_strategies": True,
    },
    "Business Focus": {
        "description": "Track monetization opportunities and business moves",
        "auto_refresh_enabled": True,
        "auto_refresh_minutes": 30,
        "max_articles_per_source": 50,
        "categories_of_interest": [
            "AI Business", "AI Agents", "Vibe Coding", "AI Tools"
        ],
        "relevance_threshold": 0.4,
        "fetch_timeout_seconds": 15,
        "max_concurrent_fetches": 6,
        "show_read_articles": True,
        "notification_on_fetch": True,
        "auto_score_articles": True,
        "auto_generate_strategies": True,
    },
    "Coder Mode": {
        "description": "Focus on coding tools, agents, and developer news",
        "auto_refresh_enabled": True,
        "auto_refresh_minutes": 15,
        "max_articles_per_source": 50,
        "categories_of_interest": [
            "Vibe Coding", "AI Agents", "AI Tools", "Open Source AI", "Local AI"
        ],
        "relevance_threshold": 0.3,
        "fetch_timeout_seconds": 15,
        "max_concurrent_fetches": 6,
        "show_read_articles": True,
        "notification_on_fetch": True,
        "auto_score_articles": True,
        "auto_generate_strategies": False,
    },
}


def get_profiles() -> dict:
    """Load saved profiles, merge with defaults."""
    path = get_data_dir() / PROFILES_FILE
    profiles = dict(DEFAULT_PROFILES)
    if path.exists():
        try:
            custom = json.loads(path.read_text(encoding="utf-8"))
            profiles.update(custom)
        except Exception:
            pass
    return profiles


def save_profile(name: str, settings: dict) -> None:
    """Save a custom profile."""
    path = get_data_dir() / PROFILES_FILE
    profiles = {}
    if path.exists():
        try:
            profiles = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    profiles[name] = settings
    path.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


def delete_profile(name: str) -> bool:
    """Delete a custom profile (can't delete defaults)."""
    if name in DEFAULT_PROFILES:
        return False
    path = get_data_dir() / PROFILES_FILE
    if not path.exists():
        return False
    try:
        profiles = json.loads(path.read_text(encoding="utf-8"))
        if name in profiles:
            del profiles[name]
            path.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
            return True
    except Exception:
        pass
    return False


def apply_profile(profile_name: str, config) -> None:
    """Apply a profile's settings to the app config."""
    profiles = get_profiles()
    if profile_name not in profiles:
        return
    profile = profiles[profile_name]
    for key, value in profile.items():
        if key == "description":
            continue
        if hasattr(config, key):
            setattr(config, key, value)
