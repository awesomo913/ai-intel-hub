"""Notification service — Windows toast + terminal banner for breakthrough alerts."""

import json
import logging
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_ALERT_FILE = Path.home() / ".claude" / "tmp" / "alerts" / "latest.json"
_BANNER_LOCK = threading.Lock()


def _ensure_alert_dir() -> None:
    _ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)


def send_windows_toast(title: str, message: str, duration: int = 10) -> None:
    """Fire a Windows 11 toast notification via PowerShell.

    Uses PowerShell's Windows.UI.Notifications runtime API — no extra packages
    required. Falls back silently if PowerShell is unavailable.
    """
    ps_script = f"""
$appId = 'AI Intel Hub'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$template.SelectSingleNode('//text[@id=1]').InnerText = '{title.replace("'", "`'")}'
$template.SelectSingleNode('//text[@id=2]').InnerText = '{message[:120].replace("'", "`'")}'
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
"""
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        log.info("Toast sent: %s", title)
    except OSError as exc:
        log.warning("Could not send Windows toast: %s", exc)


def write_terminal_banner(
    title: str,
    message: str,
    score: float = 0.0,
    url: str = "",
    source: str = "",
) -> None:
    """Write a breakthrough alert to the shared JSON file.

    The PowerShell profile hook reads this file and prints a banner after
    each command completes if a new alert has arrived.
    """
    _ensure_alert_dir()
    alert = {
        "title": title,
        "message": message[:200],
        "score": round(score, 3),
        "url": url,
        "source": source,
        "ts": datetime.now(timezone.utc).isoformat(),
        "seen": False,
    }
    with _BANNER_LOCK:
        try:
            _ALERT_FILE.write_text(
                json.dumps(alert, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log.info("Banner written: %s (score=%.2f)", title[:60], score)
        except OSError as exc:
            log.error("Could not write terminal banner: %s", exc)


def notify_breakthrough(
    title: str,
    message: str,
    score: float = 0.0,
    url: str = "",
    source: str = "",
) -> None:
    """Fire BOTH a Windows toast and a terminal banner simultaneously."""
    threading.Thread(
        target=send_windows_toast,
        args=(f"AI Intel Hub — {source or 'Breakthrough'}", title),
        daemon=True,
    ).start()
    write_terminal_banner(title, message, score, url, source)


def check_and_notify(articles: list[dict], threshold: float = 0.85) -> int:
    """Scan a list of articles and notify on any that exceed the threshold.

    Returns the number of breakthrough alerts fired.
    """
    fired = 0
    for art in articles:
        score = art.get("relevance_score", 0.0)
        if score >= threshold:
            notify_breakthrough(
                title=art.get("title", "")[:80],
                message=art.get("summary", "")[:150],
                score=score,
                url=art.get("url", ""),
                source=art.get("source_name", ""),
            )
            fired += 1
    return fired


def mark_banner_seen() -> None:
    """Mark the current banner alert as seen (called by the GUI on open)."""
    if not _ALERT_FILE.exists():
        return
    with _BANNER_LOCK:
        try:
            data = json.loads(_ALERT_FILE.read_text(encoding="utf-8"))
            data["seen"] = True
            _ALERT_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            log.warning("Could not mark banner seen: %s", exc)


def get_powershell_hook_snippet() -> str:
    """Return the PowerShell snippet to paste into $PROFILE for terminal banners."""
    alert_path = str(_ALERT_FILE).replace("\\", "\\\\")
    return f"""
# ── AI Intel Hub terminal banner ────────────────────────────────────────────
function _aih_check_banner {{
    $f = '{alert_path}'
    if (-not (Test-Path $f)) {{ return }}
    try {{
        $a = Get-Content $f -Raw | ConvertFrom-Json
        if (-not $a.seen) {{
            Write-Host ""
            Write-Host "  ★ AI INTEL HUB ALERT ★" -ForegroundColor Cyan
            Write-Host "  $($a.title)" -ForegroundColor Yellow
            if ($a.message) {{ Write-Host "  $($a.message)" -ForegroundColor White }}
            if ($a.url)     {{ Write-Host "  $($a.url)"     -ForegroundColor DarkGray }}
            Write-Host ""
            $a.seen = $true
            $a | ConvertTo-Json | Set-Content $f -Encoding utf8
        }}
    }} catch {{ Write-Warning "AI Intel Hub banner error: $_" }}
}}
# Register to fire after every prompt
$function:Prompt = {{
    _aih_check_banner
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}}
# ────────────────────────────────────────────────────────────────────────────
"""
