"""Performance logger - tracks fetch times, errors, throughput, and bottlenecks.
Writes structured logs to a rotating log file for analysis."""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .platform_utils import get_data_dir

logger = logging.getLogger(__name__)

LOG_FILE = "performance.jsonl"
MAX_LOG_SIZE_MB = 10


def _log_path() -> Path:
    return get_data_dir() / LOG_FILE


def log_event(event_type: str, source: str = "", duration_ms: float = 0,
              success: bool = True, details: dict = None, articles_count: int = 0,
              error_msg: str = "") -> None:
    """Log a structured performance event."""
    entry = {
        "ts": datetime.now().isoformat(),
        "event": event_type,
        "source": source,
        "duration_ms": round(duration_ms, 1),
        "success": success,
        "articles": articles_count,
        "error": error_msg,
    }
    if details:
        entry["details"] = details
    try:
        path = _log_path()
        # Rotate if too large
        if path.exists() and path.stat().st_size > MAX_LOG_SIZE_MB * 1024 * 1024:
            archive = path.with_suffix(f".{datetime.now().strftime('%Y%m%d')}.jsonl")
            path.rename(archive)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.debug("Perf log write error: %s", e)


def get_recent_events(hours: int = 24, event_type: str = "",
                      limit: int = 500) -> list[dict]:
    """Read recent performance events."""
    path = _log_path()
    if not path.exists():
        return []
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    events = []
    try:
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("ts", "") >= cutoff:
                    if not event_type or entry.get("event") == event_type:
                        events.append(entry)
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return events[-limit:]


def get_performance_summary(hours: int = 24) -> dict:
    """Analyze recent performance data and return summary stats."""
    events = get_recent_events(hours=hours)
    if not events:
        return {"status": "no_data", "message": "No performance data yet. Run a fetch first."}

    fetches = [e for e in events if e["event"] == "source_fetch"]
    errors = [e for e in events if not e.get("success", True)]
    sessions = [e for e in events if e["event"] == "session_start"]
    full_fetches = [e for e in events if e["event"] == "full_fetch"]

    # Source performance
    source_stats = {}
    for f in fetches:
        name = f.get("source", "unknown")
        if name not in source_stats:
            source_stats[name] = {"total": 0, "errors": 0, "total_ms": 0, "articles": 0}
        source_stats[name]["total"] += 1
        source_stats[name]["total_ms"] += f.get("duration_ms", 0)
        source_stats[name]["articles"] += f.get("articles", 0)
        if not f.get("success", True):
            source_stats[name]["errors"] += 1

    # Slowest sources
    slowest = sorted(
        [(name, s["total_ms"] / max(s["total"], 1)) for name, s in source_stats.items()],
        key=lambda x: x[1], reverse=True
    )[:10]

    # Most erroring sources
    error_sources = sorted(
        [(name, s["errors"]) for name, s in source_stats.items() if s["errors"] > 0],
        key=lambda x: x[1], reverse=True
    )

    # Throughput
    total_articles = sum(f.get("articles", 0) for f in fetches)
    total_duration = sum(f.get("duration_ms", 0) for f in full_fetches) or 1

    return {
        "status": "ok",
        "period_hours": hours,
        "total_events": len(events),
        "total_fetches": len(fetches),
        "total_errors": len(errors),
        "error_rate": round(len(errors) / max(len(fetches), 1) * 100, 1),
        "total_articles_fetched": total_articles,
        "avg_fetch_time_ms": round(sum(f.get("duration_ms", 0) for f in fetches) / max(len(fetches), 1), 1),
        "slowest_sources": slowest,
        "error_sources": error_sources,
        "full_fetch_count": len(full_fetches),
        "avg_full_fetch_ms": round(total_duration / max(len(full_fetches), 1), 1),
        "sessions": len(sessions),
        "source_stats": source_stats,
    }


def get_bottleneck_report() -> list[dict]:
    """Identify what's slowing down or breaking the app."""
    summary = get_performance_summary(hours=72)
    if summary.get("status") == "no_data":
        return [{"severity": "info", "issue": "No data yet", "fix": "Run your first fetch to start collecting performance data."}]

    issues = []

    # Check error rate
    if summary["error_rate"] > 30:
        issues.append({
            "severity": "critical",
            "issue": f"High error rate: {summary['error_rate']}% of fetches are failing",
            "fix": "Go to Sources tab and disable or replace the broken feeds. Check your internet connection.",
        })
    elif summary["error_rate"] > 10:
        issues.append({
            "severity": "warning",
            "issue": f"Moderate error rate: {summary['error_rate']}% of fetches failing",
            "fix": "Some sources may have changed their URLs. Check the error sources list below.",
        })

    # Flag broken sources
    for name, err_count in summary.get("error_sources", []):
        stats = summary["source_stats"].get(name, {})
        total = stats.get("total", 1)
        if err_count >= total:
            issues.append({
                "severity": "critical",
                "issue": f"Source '{name}' is completely broken ({err_count}/{total} failures)",
                "fix": f"Disable or delete '{name}' in Sources tab. The RSS feed URL may have changed or been removed.",
            })
        elif err_count > total * 0.5:
            issues.append({
                "severity": "warning",
                "issue": f"Source '{name}' is unreliable ({err_count}/{total} failures)",
                "fix": f"Check if '{name}' feed URL is still valid. Consider reducing fetch frequency.",
            })

    # Flag slow sources
    for name, avg_ms in summary.get("slowest_sources", [])[:5]:
        if avg_ms > 10000:
            issues.append({
                "severity": "warning",
                "issue": f"Source '{name}' is very slow (avg {avg_ms/1000:.1f}s per fetch)",
                "fix": "This source takes a long time to respond. Consider disabling it if fetch times are too long.",
            })

    # Check fetch throughput
    if summary["avg_full_fetch_ms"] > 120000:
        issues.append({
            "severity": "warning",
            "issue": f"Full refresh takes {summary['avg_full_fetch_ms']/1000:.0f}s on average",
            "fix": "Disable some slower sources or increase the thread count for faster parallel fetching.",
        })

    # Check article intake
    if summary["total_articles_fetched"] == 0 and summary["total_fetches"] > 0:
        issues.append({
            "severity": "critical",
            "issue": "No new articles are being fetched despite running refreshes",
            "fix": "All articles may already be in the database, or all sources are broken. Try adding new sources.",
        })

    # Disk space
    from .platform_utils import detect_platform
    info = detect_platform()
    if info.available_disk_gb < 1.0:
        issues.append({
            "severity": "critical",
            "issue": f"Very low disk space: {info.available_disk_gb} GB free",
            "fix": "Free up disk space. The database and logs may fail to write.",
        })
    elif info.available_disk_gb < 5.0:
        issues.append({
            "severity": "warning",
            "issue": f"Low disk space: {info.available_disk_gb} GB free",
            "fix": "Consider freeing up disk space soon.",
        })

    if not issues:
        issues.append({
            "severity": "good",
            "issue": "Everything is running smoothly!",
            "fix": f"Fetched {summary['total_articles_fetched']} articles with {summary['error_rate']}% error rate over the past 72 hours.",
        })

    return issues
