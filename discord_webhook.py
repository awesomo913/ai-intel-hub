"""Discord webhook module - send AI intelligence alerts to Discord channels.
Webhook URL stored securely in OS keychain (Windows Credential Manager,
macOS Keychain, Linux Secret Service)."""

import logging
from datetime import datetime
from typing import Optional

import keyring
import keyring.errors
import requests

from . import database as db

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "AIIntelHub_Discord"
KEYRING_USERNAME = "webhook_url"

# Discord color codes (decimal)
COLOR_GROUNDBREAKER = 0xFF4500   # orange-red
COLOR_HIGH = 0x00B894            # green
COLOR_MEDIUM = 0xFDCB6E          # yellow
COLOR_LOW = 0x636E72             # gray
COLOR_INFO = 0x0984E3            # blue


# --- Secure Credential Storage ---

def save_webhook_url(url: str) -> None:
    """Store Discord webhook URL securely in the OS keychain."""
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, url)
        logger.info("Discord webhook URL stored in OS keychain")
    except Exception as e:
        logger.error("Keychain storage failed: %s", e)


def get_webhook_url() -> Optional[str]:
    """Retrieve Discord webhook URL from the OS keychain."""
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except Exception as e:
        logger.error("Keychain retrieval failed: %s", e)
        return None


def delete_webhook_url() -> None:
    """Remove Discord webhook URL from the OS keychain."""
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception as e:
        logger.debug("Keychain delete: %s", e)


# --- Payload Builders ---

def _score_color(score: float) -> int:
    """Return a Discord color integer based on relevance score."""
    if score >= 0.75:
        return COLOR_HIGH
    if score >= 0.4:
        return COLOR_MEDIUM
    return COLOR_LOW


def build_groundbreaker_payload() -> Optional[dict]:
    """Build a Discord webhook payload highlighting the top groundbreaker article."""
    from .analyzer import get_groundbreaker, get_standouts

    gb = get_groundbreaker()
    if not gb:
        standouts = get_standouts(limit=1)
        if not standouts:
            return None
        gb = standouts[0]

    score = gb.get("relevance_score", 0)
    pct = f"{score:.0%}"
    summary = gb.get("summary", "")[:300]
    category = gb.get("category", "")

    embed = {
        "title": f"🔥 GROUNDBREAKER: {gb['title'][:200]}",
        "url": gb.get("url", ""),
        "description": summary or "No summary available.",
        "color": COLOR_GROUNDBREAKER,
        "fields": [
            {"name": "Category", "value": category or "—", "inline": True},
            {"name": "Score", "value": pct, "inline": True},
        ],
        "footer": {"text": "AI Intel Hub • Groundbreaker Alert"},
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        "username": "AI Intel Hub",
        "content": "🚨 **GROUNDBREAKER detected!** This is a must-read.",
        "embeds": [embed],
    }


def build_standouts_payload(limit: int = 5) -> Optional[dict]:
    """Build a Discord webhook payload with the top standout articles."""
    from .analyzer import get_standouts

    standouts = get_standouts(limit=limit)
    if not standouts:
        return None

    embeds = []
    for i, article in enumerate(standouts, 1):
        score = article.get("relevance_score", 0)
        pct = f"{score:.0%}"
        summary = (article.get("summary", "") or "")[:200]
        embeds.append({
            "title": f"{i}. {article['title'][:200]}",
            "url": article.get("url", ""),
            "description": summary or "No summary available.",
            "color": _score_color(score),
            "fields": [
                {"name": "Category", "value": article.get("category", "—"), "inline": True},
                {"name": "Score", "value": pct, "inline": True},
            ],
        })

    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "username": "AI Intel Hub",
        "content": f"📊 **Top {len(standouts)} AI Standouts for {today}**",
        "embeds": embeds,
    }


def build_digest_payload(max_articles: int = 10) -> dict:
    """Build a compact Discord webhook payload as a daily digest."""
    stats = db.get_stats()
    articles = db.get_articles(limit=max_articles, min_score=0.4)
    today = datetime.now().strftime("%Y-%m-%d")

    lines = []
    for a in articles:
        score_pct = f"{a.get('relevance_score', 0):.0%}"
        cat = a.get("category", "")
        title = a.get("title", "")[:120]
        url = a.get("url", "")
        lines.append(f"• [{title}]({url}) `{cat}` `{score_pct}`")

    description = "\n".join(lines) if lines else "No articles available."

    embed = {
        "title": f"📰 AI Intel Hub Daily Digest — {today}",
        "description": description[:4096],
        "color": COLOR_INFO,
        "fields": [
            {"name": "Total Articles", "value": str(stats.get("total_articles", 0)), "inline": True},
            {"name": "Today", "value": str(stats.get("today_articles", 0)), "inline": True},
            {"name": "Active Sources", "value": str(stats.get("active_sources", 0)), "inline": True},
        ],
        "footer": {"text": "AI Intel Hub"},
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        "username": "AI Intel Hub",
        "embeds": [embed],
    }


# --- Send ---

def send_discord_message(payload: dict, webhook_url: str = "") -> tuple[bool, str]:
    """POST a payload to a Discord webhook URL. Returns (success, message)."""
    url = webhook_url or get_webhook_url()
    if not url:
        return (False, "No Discord webhook URL configured. Set it in the Discord tab.")

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            logger.info("Discord message sent (status %s)", resp.status_code)
            return (True, "Message sent to Discord")
        else:
            msg = f"Discord returned HTTP {resp.status_code}: {resp.text[:100]}"
            logger.warning(msg)
            return (False, msg)
    except requests.exceptions.ConnectionError:
        return (False, "Connection error — check your internet connection.")
    except requests.exceptions.Timeout:
        return (False, "Request timed out. Discord may be slow — try again.")
    except Exception as e:
        logger.error("Discord send failed: %s", e)
        return (False, f"Send failed: {str(e)[:100]}")


def send_groundbreaker_alert(webhook_url: str = "") -> tuple[bool, str]:
    """Send a groundbreaker alert to Discord."""
    payload = build_groundbreaker_payload()
    if payload is None:
        return (False, "No groundbreaker or standout articles available.")
    ok, msg = send_discord_message(payload, webhook_url)
    _log(ok, "groundbreaker", 1, "" if ok else msg)
    return (ok, msg)


def send_standouts_digest(webhook_url: str = "") -> tuple[bool, str]:
    """Send the top standout articles to Discord."""
    payload = build_standouts_payload()
    if payload is None:
        return (False, "No standout articles available.")
    count = len(payload.get("embeds", []))
    ok, msg = send_discord_message(payload, webhook_url)
    _log(ok, "standouts", count, "" if ok else msg)
    return (ok, msg)


def send_daily_digest(webhook_url: str = "") -> tuple[bool, str]:
    """Send the daily digest to Discord."""
    payload = build_digest_payload()
    articles = payload.get("embeds", [{}])[0].get("description", "").count("•")
    ok, msg = send_discord_message(payload, webhook_url)
    _log(ok, "digest", articles, "" if ok else msg)
    return (ok, msg)


def _log(success: bool, message_type: str, article_count: int, error_msg: str) -> None:
    """Log a Discord send attempt to the database."""
    try:
        db.log_discord_send(
            message_type=message_type,
            article_count=article_count,
            success=success,
            error_msg=error_msg,
        )
    except Exception as e:
        logger.debug("Discord history log failed: %s", e)
