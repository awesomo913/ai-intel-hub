"""Email module - compose and send intelligence reports via SMTP or mailto.
Credentials stored securely via OS keychain (Windows Credential Manager,
macOS Keychain, Linux Secret Service)."""

import json
import logging
import smtplib
import threading
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

# Email-to-SMS gateway templates (no new dependencies — uses existing SMTP)
SMS_GATEWAYS: dict[str, float] = {
    "AT&T":        "{number}@txt.att.net",
    "T-Mobile":    "{number}@tmomail.net",
    "Verizon":     "{number}@vtext.com",
    "Sprint":      "{number}@messaging.sprintpcs.com",
    "US Cellular": "{number}@email.uscc.net",
    "Cricket":     "{number}@sms.cricketwireless.net",
    "Metro PCS":   "{number}@mymetropcs.com",
    "Boost":       "{number}@sms.myboostmobile.com",
}

# Background timer for scheduled email (module-level so it persists)
_schedule_timer: Optional[threading.Timer] = None
_schedule_lock = threading.Lock()


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


def build_html_digest(max_articles: int = 20) -> tuple[str, str]:
    """Build an HTML email digest with color-coded scores and clickable links.
    Returns (subject, html_body)."""
    today = datetime.now().strftime("%Y-%m-%d")
    stats = db.get_stats()
    articles = db.get_articles(limit=max_articles, min_score=0.4)
    standouts = db.get_articles(limit=5, min_score=0.6)

    subject = f"AI Intel Hub Daily Digest - {today}"

    def score_color(score: float) -> str:
        if score >= 0.7:
            return "#00c853"
        if score >= 0.4:
            return "#ffa726"
        return "#9e9e9e"

    rows_html = ""
    for a in articles:
        score = a.get("relevance_score", 0)
        color = score_color(score)
        title = a["title"].replace("<", "&lt;").replace(">", "&gt;")
        url = a["url"]
        cat = a.get("category", "")
        summary = (a.get("summary", "") or "")[:150].replace("<", "&lt;").replace(">", "&gt;")
        rows_html += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #2a2a40;">
            <strong><a href="{url}" style="color:#6c63ff;text-decoration:none;">{title}</a></strong><br>
            <span style="color:#888;font-size:12px;">{cat}</span>
            {f'<br><span style="color:#aaa;font-size:12px;">{summary}</span>' if summary else ''}
          </td>
          <td style="padding:8px;border-bottom:1px solid #2a2a40;text-align:center;white-space:nowrap;">
            <span style="color:{color};font-weight:bold;">{score:.0%}</span>
          </td>
        </tr>"""

    standouts_html = ""
    for i, a in enumerate(standouts, 1):
        title = a["title"].replace("<", "&lt;").replace(">", "&gt;")
        url = a["url"]
        standouts_html += f'<li><a href="{url}" style="color:#fcc419;">{title}</a></li>'

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#e0e0e0;margin:0;padding:20px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:700px;margin:0 auto;">
    <tr><td style="background:#1a1a2e;padding:20px;border-radius:8px 8px 0 0;">
      <h1 style="color:#6c63ff;margin:0;">🧠 AI Intel Hub</h1>
      <p style="color:#888;margin:5px 0 0;">Daily Digest &mdash; {today}</p>
    </td></tr>
    <tr><td style="background:#16213e;padding:16px;">
      <p style="color:#aaa;margin:0;">
        Total: <strong style="color:#e0e0e0;">{stats['total_articles']}</strong> &nbsp;|&nbsp;
        Today: <strong style="color:#00c853;">{stats['today_articles']}</strong> &nbsp;|&nbsp;
        Sources: <strong style="color:#42a5f5;">{stats['active_sources']}</strong>
      </p>
    </td></tr>
    {f'''<tr><td style="background:#16213e;padding:16px 16px 0;">
      <h2 style="color:#fcc419;margin:0 0 8px;">⭐ Top 5 Standouts</h2>
      <ol style="color:#e0e0e0;margin:0;padding-left:20px;">{standouts_html}</ol>
    </td></tr>''' if standouts_html else ''}
    <tr><td style="background:#16213e;padding:16px;">
      <h2 style="color:#e0e0e0;margin:0 0 8px;">📰 High-Value Articles</h2>
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <th style="text-align:left;color:#888;font-size:12px;padding:4px 8px;border-bottom:1px solid #2a2a40;">Article</th>
          <th style="color:#888;font-size:12px;padding:4px 8px;border-bottom:1px solid #2a2a40;width:60px;">Score</th>
        </tr>
        {rows_html}
      </table>
    </td></tr>
    <tr><td style="background:#0d0d1a;padding:12px;border-radius:0 0 8px 8px;text-align:center;">
      <p style="color:#555;font-size:11px;margin:0;">AI Intel Hub &mdash; Sent via SMTP</p>
    </td></tr>
  </table>
</body>
</html>"""

    return (subject, html)


def build_sms_body(max_chars: int = 160) -> str:
    """Build a short SMS body from the current groundbreaker or top standout."""
    from .analyzer import get_standouts, get_groundbreaker
    gb = get_groundbreaker()
    if gb:
        msg = f"AI INTEL: {gb['title'][:80]} {gb['url']}"
    else:
        standouts = get_standouts(limit=1)
        if standouts:
            msg = f"AI: {standouts[0]['title'][:80]} {standouts[0]['url']}"
        else:
            msg = "AI Intel Hub: No high-score items right now."
    return msg[:max_chars]


def send_sms(phone_number: str, carrier: str) -> tuple[bool, str]:
    """Send a short SMS alert via email-to-SMS gateway using existing SMTP config."""
    gateway_template = SMS_GATEWAYS.get(carrier)
    if not gateway_template:
        return (False, f"Unknown carrier: {carrier}")
    clean_number = (phone_number.replace("-", "").replace(" ", "")
                    .replace("(", "").replace(")", ""))
    sms_email = gateway_template.format(number=clean_number)
    return send_via_smtp(to=sms_email, subject="", body=build_sms_body(), method="sms")


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
                  from_addr: str = "", cc: str = "",
                  method: str = "smtp") -> tuple[bool, str]:
    """Send email via SMTP. Password retrieved from OS keychain.
    Supports multiple comma-separated recipients and an optional CC field."""
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
        if cc:
            msg["CC"] = cc
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Build recipient list from To + CC
        all_recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        if cc:
            all_recipients += [addr.strip() for addr in cc.split(",") if addr.strip()]

        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(from_addr, all_recipients, msg.as_string())

        logger.info("Email sent via SMTP (method=%s)", method)
        db.log_email_send(to, subject, method, success=True)
        return (True, f"Email sent to {to}")
    except smtplib.SMTPAuthenticationError:
        db.log_email_send(to, subject, method, success=False)
        return (False, "SMTP authentication failed. Check username/password. For Gmail, use an App Password.")
    except smtplib.SMTPRecipientsRefused:
        db.log_email_send(to, subject, method, success=False)
        return (False, f"Recipient {to} was refused by the server.")
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        db.log_email_send(to, subject, method, success=False)
        return (False, f"Send failed: {str(e)[:100]}")


def send_via_smtp_html(to: str, subject: str, html_body: str,
                       cc: str = "") -> tuple[bool, str]:
    """Send an HTML email with a plain-text fallback via SMTP."""
    config = _get_email_config()
    smtp_server = config.get("smtp_server", "smtp.gmail.com")
    smtp_port = config.get("smtp_port", 587)
    username = config.get("username", "")
    password = get_smtp_credential(username) or ""
    from_addr = config.get("from_addr", username)

    if not all([smtp_server, username, password, to]):
        return (False, "Missing SMTP configuration. Set up in Settings > Email.")

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = from_addr
        msg["To"] = to
        if cc:
            msg["CC"] = cc
        msg["Subject"] = subject

        # Plain text fallback using BeautifulSoup for reliable HTML stripping
        from bs4 import BeautifulSoup
        plain = BeautifulSoup(html_body, "html.parser").get_text(separator="\n", strip=True)
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        all_recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        if cc:
            all_recipients += [addr.strip() for addr in cc.split(",") if addr.strip()]

        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(from_addr, all_recipients, msg.as_string())

        logger.info("HTML email sent via SMTP")
        db.log_email_send(to, subject, "smtp_html", success=True)
        return (True, f"HTML email sent to {to}")
    except smtplib.SMTPAuthenticationError:
        db.log_email_send(to, subject, "smtp_html", success=False)
        return (False, "SMTP authentication failed.")
    except Exception as e:
        logger.error("HTML SMTP send failed: %s", e)
        db.log_email_send(to, subject, "smtp_html", success=False)
        return (False, f"Send failed: {str(e)[:100]}")


# --- Scheduled Email ---

def _schedule_interval_seconds(schedule: str) -> Optional[int]:
    """Convert schedule string to interval in seconds. Returns None if off."""
    mapping = {
        "Daily 8am": 86400,
        "Daily 6pm": 86400,
        "Every 6 hours": 21600,
    }
    return mapping.get(schedule)


def start_scheduled_email(schedule: str) -> None:
    """Start a background threading.Timer to send scheduled emails.
    Re-entrant: safe to call multiple times (cancels previous timer)."""
    global _schedule_timer

    interval = _schedule_interval_seconds(schedule)
    if not interval:
        return

    config = _get_email_config()
    last_sent_iso = config.get("last_email_sent", "")
    now = datetime.now()

    def _send_and_reschedule():
        global _schedule_timer
        cfg = _get_email_config()
        to = cfg.get("default_to", "")
        if to:
            subject, body = build_daily_digest()
            send_via_smtp(to=to, subject=subject, body=body, method="scheduled")
        # Update last sent timestamp
        cfg["last_email_sent"] = datetime.now().isoformat()
        save_email_config(dict(cfg))
        # Reschedule
        start_scheduled_email(schedule)

    # If we missed a send, fire immediately
    should_send_now = False
    if last_sent_iso:
        try:
            last_sent = datetime.fromisoformat(last_sent_iso)
            if (now - last_sent).total_seconds() >= interval:
                should_send_now = True
        except Exception:
            pass

    with _schedule_lock:
        if _schedule_timer is not None:
            try:
                _schedule_timer.cancel()
            except Exception:
                pass

        if should_send_now:
            _schedule_timer = threading.Timer(0, _send_and_reschedule)
        else:
            _schedule_timer = threading.Timer(interval, _send_and_reschedule)

        _schedule_timer.daemon = True
        _schedule_timer.start()
    logger.info("Scheduled email started: %s (interval=%ds)", schedule, interval)
