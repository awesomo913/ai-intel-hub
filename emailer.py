"""Email module - compose and send intelligence reports via SMTP or mailto.
Credentials stored securely via OS keychain (Windows Credential Manager,
macOS Keychain, Linux Secret Service)."""

import json
import logging
import smtplib
import webbrowser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import keyring
import keyring.errors

from . import database as db
from .exporter import articles_to_markdown, articles_to_text
from .strategy import get_strategy_summary
from .platform_utils import get_data_dir

logger = logging.getLogger(__name__)

SMTP_CONFIG_FILE = "email_config.json"
KEYRING_SERVICE = "AIIntelHub_SMTP"


# --- Secure Credential Storage ---

def save_smtp_credential(username: str, password: str) -> None:
    """Store SMTP password securely in the OS keychain."""
    try:
        keyring.set_password(KEYRING_SERVICE, username, password)
        logger.info("SMTP credential stored in OS keychain for %s", username)
    except Exception as e:
        logger.error("Keychain storage failed: %s", e)


def get_smtp_credential(username: str) -> Optional[str]:
    """Retrieve SMTP password from the OS keychain."""
    if not username:
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, username)
    except Exception as e:
        logger.error("Keychain retrieval failed: %s", e)
        return None


def delete_smtp_credential(username: str) -> None:
    """Remove SMTP password from the OS keychain."""
    try:
        keyring.delete_password(KEYRING_SERVICE, username)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception as e:
        logger.debug("Keychain delete: %s", e)


# --- Non-Sensitive Config (JSON) ---

def _get_email_config() -> dict:
    """Load saved email config (no password - that's in the keychain)."""
    path = get_data_dir() / SMTP_CONFIG_FILE
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_email_config(config: dict) -> None:
    """Save email config. Password is routed to OS keychain, not JSON."""
    username = config.get("username", "")
    password = config.pop("password", "")

    # Store password in OS keychain, not on disk
    if username and password:
        save_smtp_credential(username, password)

    # Save only non-sensitive fields to JSON
    path = get_data_dir() / SMTP_CONFIG_FILE
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


# --- Email Body Builders ---

def build_daily_digest(max_articles: int = 20) -> tuple[str, str]:
    """Build a daily digest email. Returns (subject, body_text)."""
    today = datetime.now().strftime("%Y-%m-%d")
    stats = db.get_stats()
    articles = db.get_articles(limit=max_articles, min_score=0.4)

    subject = f"AI Intel Hub Daily Digest - {today}"

    lines = [
        f"AI INTEL HUB - Daily Digest for {today}",
        "=" * 50,
        "",
        f"Total Articles: {stats['total_articles']} | Today: {stats['today_articles']} | "
        f"Sources: {stats['active_sources']}",
        "",
    ]

    # Top 5 standouts
    standouts = db.get_articles(limit=5, min_score=0.6)
    if standouts:
        lines.append("TOP 5 STANDOUTS")
        lines.append("-" * 30)
        for i, a in enumerate(standouts, 1):
            lines.append(f"{i}. [{a.get('category', '')}] {a['title']}")
            lines.append(f"   {a['url']}")
            if a.get('summary'):
                lines.append(f"   {a['summary'][:150]}")
            lines.append("")

    # Category breakdown
    if stats.get("categories"):
        lines.append("CATEGORY BREAKDOWN")
        lines.append("-" * 30)
        for cat, cnt in stats["categories"].items():
            lines.append(f"  {cat}: {cnt}")
        lines.append("")

    # Recent high-value articles
    lines.append("HIGH-VALUE ARTICLES")
    lines.append("-" * 30)
    for a in articles:
        score_pct = f"{a.get('relevance_score', 0):.0%}"
        lines.append(f"[{score_pct}] [{a.get('category', '')}] {a['title']}")
        lines.append(f"  {a['url']}")
        lines.append("")

    body = "\n".join(lines)
    return (subject, body)


def build_standouts_email() -> tuple[str, str]:
    """Build email with just top standouts + groundbreaker."""
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"AI Intel - Top Picks & Groundbreaker - {today}"

    from .analyzer import get_standouts, get_groundbreaker
    standouts = get_standouts(limit=5)
    groundbreaker = get_groundbreaker()

    lines = [
        f"AI INTEL HUB - Top Picks for {today}",
        "=" * 50,
        "",
    ]

    if groundbreaker:
        lines.extend([
            "GROUNDBREAKER - CHECK THIS NOW",
            "*" * 40,
            f"  {groundbreaker['title']}",
            f"  Category: {groundbreaker.get('category', '')} | Score: {groundbreaker.get('relevance_score', 0):.0%}",
            f"  {groundbreaker['url']}",
            f"  {groundbreaker.get('summary', '')[:300]}",
            "",
            "*" * 40,
            "",
        ])

    if standouts:
        lines.append("TOP 5 STANDOUTS")
        lines.append("-" * 30)
        for i, a in enumerate(standouts, 1):
            lines.append(f"{i}. {a['title']}")
            lines.append(f"   [{a.get('category', '')}] Score: {a.get('relevance_score', 0):.0%}")
            lines.append(f"   {a['url']}")
            if a.get('summary'):
                lines.append(f"   {a['summary'][:200]}")
            lines.append("")

    body = "\n".join(lines)
    return (subject, body)


def build_strategies_email() -> tuple[str, str]:
    """Build email with monetization strategies."""
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"AI Intel - Monetization Strategies - {today}"
    body = get_strategy_summary()
    return (subject, body)


def build_custom_email(article_ids: list[int] = None, include_strategies: bool = False) -> tuple[str, str]:
    """Build custom email from selected articles."""
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"AI Intel Hub Report - {today}"

    if article_ids:
        conn = db.get_connection()
        try:
            placeholders = ",".join("?" * len(article_ids))
            rows = conn.execute(
                f"SELECT * FROM articles WHERE id IN ({placeholders}) ORDER BY relevance_score DESC",
                article_ids
            ).fetchall()
            articles = [dict(r) for r in rows]
        finally:
            conn.close()
    else:
        articles = db.get_articles(limit=30, min_score=0.4)

    body = articles_to_text(articles)
    if include_strategies:
        body += "\n\n" + "=" * 50 + "\n\n" + get_strategy_summary()

    return (subject, body)


# --- Send Methods ---

def send_via_mailto(to: str, subject: str, body: str) -> bool:
    """Open default email client with pre-filled email via mailto: URL."""
    try:
        # Truncate body for mailto URL limit (~2000 chars)
        truncated = body[:1800]
        if len(body) > 1800:
            truncated += "\n\n[Report truncated - use SMTP for full report]"

        mailto_url = f"mailto:{quote(to)}?subject={quote(subject)}&body={quote(truncated)}"
        webbrowser.open(mailto_url)
        logger.info("Opened mailto for %s", to)
        return True
    except Exception as e:
        logger.error("mailto failed: %s", e)
        return False


def send_via_gmail_web(to: str, subject: str, body: str) -> bool:
    """Open Gmail compose in browser with pre-filled fields."""
    try:
        truncated = body[:1800]
        gmail_url = (
            f"https://mail.google.com/mail/?view=cm"
            f"&to={quote(to)}"
            f"&su={quote(subject)}"
            f"&body={quote(truncated)}"
        )
        webbrowser.open(gmail_url)
        logger.info("Opened Gmail compose for %s", to)
        return True
    except Exception as e:
        logger.error("Gmail web failed: %s", e)
        return False


def send_via_smtp(to: str, subject: str, body: str,
                  smtp_server: str = "", smtp_port: int = 587,
                  username: str = "", password: str = "",
                  from_addr: str = "") -> tuple[bool, str]:
    """Send email via SMTP. Password retrieved from OS keychain."""
    config = _get_email_config()
    smtp_server = smtp_server or config.get("smtp_server", "smtp.gmail.com")
    smtp_port = smtp_port or config.get("smtp_port", 587)
    username = username or config.get("username", "")
    # Retrieve password from OS keychain (not JSON)
    password = password or get_smtp_credential(username) or ""
    from_addr = from_addr or config.get("from_addr", username)

    if not all([smtp_server, username, password, to]):
        return (False, "Missing SMTP configuration. Set up in Settings > Email.")

    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)

        logger.info("Email sent to %s via SMTP", to)
        return (True, f"Email sent to {to}")
    except smtplib.SMTPAuthenticationError:
        return (False, "SMTP authentication failed. Check username/password. For Gmail, use an App Password.")
    except smtplib.SMTPRecipientsRefused:
        return (False, f"Recipient {to} was refused by the server.")
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        return (False, f"Send failed: {str(e)[:100]}")
