"""Comprehensive diagnostic report generator with fix suggestions and health scoring."""

import logging
import platform
import sys
from datetime import datetime
from pathlib import Path

from .platform_utils import detect_platform, get_app_dir, get_data_dir, get_export_dir, get_desktop_path
from . import database as db
from .perf_logger import get_performance_summary, get_bottleneck_report

logger = logging.getLogger(__name__)


def _check_dependency(name: str) -> tuple[str, str]:
    """Check if a package is installed and return (version, status)."""
    try:
        mod = __import__(name)
        ver = getattr(mod, "__version__", "unknown")
        return (ver, "OK")
    except ImportError:
        return ("NOT INSTALLED", "MISSING")


def _get_db_health() -> dict:
    """Run database integrity checks."""
    conn = db.get_connection()
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        freelist = conn.execute("PRAGMA freelist_count").fetchone()[0]
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        db_size_kb = (page_count * page_size) / 1024

        # Check for orphaned data
        orphan_articles = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE source_id NOT IN (SELECT id FROM sources) AND source_id != 0"
        ).fetchone()[0]

        return {
            "integrity": integrity,
            "size_kb": round(db_size_kb, 1),
            "pages": page_count,
            "freelist_pages": freelist,
            "journal_mode": journal,
            "orphaned_articles": orphan_articles,
            "fragmentation_pct": round(freelist / max(page_count, 1) * 100, 1),
        }
    except Exception as e:
        return {"integrity": f"ERROR: {e}"}
    finally:
        conn.close()


def _get_source_health() -> list[dict]:
    """Check health of each source."""
    sources = db.get_sources()
    results = []
    for s in sources:
        total = s.get("fetch_count", 0) + s.get("error_count", 0)
        error_rate = s.get("error_count", 0) / max(total, 1) * 100

        if s.get("error_count", 0) >= total and total > 0:
            status = "BROKEN"
        elif error_rate > 50:
            status = "UNRELIABLE"
        elif not s.get("is_active"):
            status = "DISABLED"
        elif not s.get("last_fetched"):
            status = "NEVER_FETCHED"
        else:
            status = "HEALTHY"

        results.append({
            "name": s["name"],
            "status": status,
            "fetches": s.get("fetch_count", 0),
            "errors": s.get("error_count", 0),
            "error_rate": round(error_rate, 1),
            "last_fetched": s.get("last_fetched", "Never"),
            "active": bool(s.get("is_active")),
        })
    return results


def calculate_health_score() -> tuple[int, list[str]]:
    """Calculate overall app health score (0-100) with reasons."""
    score = 100
    reasons = []

    # Database health
    db_health = _get_db_health()
    if db_health.get("integrity") != "ok":
        score -= 30
        reasons.append("Database integrity check failed")
    if db_health.get("fragmentation_pct", 0) > 20:
        score -= 5
        reasons.append(f"Database fragmented ({db_health['fragmentation_pct']}%)")
    if db_health.get("orphaned_articles", 0) > 0:
        score -= 5
        reasons.append(f"{db_health['orphaned_articles']} orphaned articles in database")

    # Source health
    source_health = _get_source_health()
    broken = sum(1 for s in source_health if s["status"] == "BROKEN")
    unreliable = sum(1 for s in source_health if s["status"] == "UNRELIABLE")
    if broken > 5:
        score -= 20
        reasons.append(f"{broken} sources are completely broken")
    elif broken > 0:
        score -= broken * 3
        reasons.append(f"{broken} broken source(s)")
    if unreliable > 3:
        score -= 10
        reasons.append(f"{unreliable} unreliable sources")

    # Performance
    perf = get_performance_summary(hours=24)
    if perf.get("status") != "no_data":
        if perf.get("error_rate", 0) > 30:
            score -= 15
            reasons.append(f"High error rate: {perf['error_rate']}%")
        elif perf.get("error_rate", 0) > 10:
            score -= 5
            reasons.append(f"Moderate error rate: {perf['error_rate']}%")

    # Disk space
    info = detect_platform()
    if info.available_disk_gb < 1:
        score -= 20
        reasons.append(f"Critical: only {info.available_disk_gb} GB disk space free")
    elif info.available_disk_gb < 5:
        score -= 5
        reasons.append(f"Low disk space: {info.available_disk_gb} GB free")

    # Content freshness
    stats = db.get_stats()
    if stats["total_articles"] == 0:
        score -= 10
        reasons.append("No articles in database")
    if stats["active_sources"] < 5:
        score -= 10
        reasons.append(f"Only {stats['active_sources']} active sources")

    if not reasons:
        reasons.append("All systems healthy!")

    return (max(0, min(100, score)), reasons)


def generate_diagnostic_report() -> Path:
    """Generate a comprehensive diagnostic report and save to Desktop."""
    info = detect_platform()
    stats = db.get_stats()
    db_path = db.get_db_path()
    db_health = _get_db_health()
    source_health = _get_source_health()
    health_score, health_reasons = calculate_health_score()
    perf = get_performance_summary(hours=24)
    bottlenecks = get_bottleneck_report()

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    lines = [
        "=" * 70,
        "  AI INTEL HUB - COMPREHENSIVE DIAGNOSTIC REPORT",
        "=" * 70,
        f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Health Score: {health_score}/100",
        "=" * 70,
        "",

        "1. HEALTH SCORE",
        f"   Overall: {health_score}/100 {'[GOOD]' if health_score >= 80 else '[WARNING]' if health_score >= 50 else '[CRITICAL]'}",
        "   Breakdown:",
    ]
    for reason in health_reasons:
        lines.append(f"   - {reason}")

    lines.extend([
        "",
        "2. SYSTEM INFO",
        f"   OS: {info.os_name} {info.os_version}",
        f"   Architecture: {info.architecture} ({info.machine})",
        f"   Python: {info.python_version}",
        f"   Platform: {sys.platform}",
        f"   Available Disk: {info.available_disk_gb} GB",
        "",
        "3. APP STATE",
        f"   App Directory: {get_app_dir()}",
        f"   Data Directory: {get_data_dir()}",
        f"   Database: {db_path}",
        f"   Database Size: {db_health.get('size_kb', 'unknown')} KB",
        "",
        "4. DATABASE HEALTH",
        f"   Integrity: {db_health.get('integrity', 'unknown')}",
        f"   Journal Mode: {db_health.get('journal_mode', 'unknown')}",
        f"   Fragmentation: {db_health.get('fragmentation_pct', 0)}%",
        f"   Orphaned Articles: {db_health.get('orphaned_articles', 0)}",
        "",
        "5. DATABASE STATS",
        f"   Total Articles: {stats['total_articles']}",
        f"   Unread: {stats['unread']}",
        f"   Bookmarked: {stats['bookmarked']}",
        f"   Active Sources: {stats['active_sources']}",
        f"   Strategies: {stats['strategies']}",
        f"   Today's Articles: {stats['today_articles']}",
        "",
        "6. CATEGORIES",
    ])
    for cat, cnt in stats.get("categories", {}).items():
        lines.append(f"   {cat}: {cnt}")

    lines.extend(["", "7. SOURCE HEALTH"])
    for s in sorted(source_health, key=lambda x: x["status"]):
        status_icon = {"HEALTHY": "+", "DISABLED": "~", "NEVER_FETCHED": "?",
                       "UNRELIABLE": "!", "BROKEN": "X"}.get(s["status"], "?")
        lines.append(
            f"   [{status_icon}] {s['name']:<30} status={s['status']:<15} "
            f"fetches={s['fetches']} errors={s['errors']} err_rate={s['error_rate']}%"
        )

    lines.extend(["", "8. PERFORMANCE (last 24h)"])
    if perf.get("status") != "no_data":
        lines.extend([
            f"   Total Fetches: {perf.get('total_fetches', 0)}",
            f"   Total Errors: {perf.get('total_errors', 0)}",
            f"   Error Rate: {perf.get('error_rate', 0)}%",
            f"   Articles Fetched: {perf.get('total_articles_fetched', 0)}",
            f"   Avg Fetch Time: {perf.get('avg_fetch_time_ms', 0):.0f}ms",
            f"   Avg Full Refresh: {perf.get('avg_full_fetch_ms', 0)/1000:.1f}s",
        ])
        if perf.get("slowest_sources"):
            lines.append("   Slowest Sources:")
            for name, ms in perf["slowest_sources"][:5]:
                lines.append(f"     - {name}: {ms/1000:.1f}s avg")
    else:
        lines.append("   No performance data yet.")

    lines.extend(["", "9. BOTTLENECKS & FIX SUGGESTIONS"])
    for issue in bottlenecks:
        sev = issue["severity"].upper()
        lines.append(f"   [{sev}] {issue['issue']}")
        lines.append(f"         FIX: {issue['fix']}")

    lines.extend(["", "10. INSTALLED PACKAGES"])
    for pkg in ["customtkinter", "feedparser", "bs4", "requests", "PIL"]:
        display = pkg.replace("bs4", "beautifulsoup4").replace("PIL", "Pillow")
        ver, status = _check_dependency(pkg)
        lines.append(f"   {display}: {ver} [{status}]")

    lines.extend(["", "11. TOP SOURCES BY ARTICLES"])
    for src, cnt in stats.get("top_sources", {}).items():
        lines.append(f"   {src}: {cnt} articles")

    lines.extend(["", "=" * 70, "  END OF REPORT", "=" * 70])

    content = "\n".join(lines)
    desktop = get_desktop_path()
    report_path = desktop / f"ai_intel_hub_diagnostic_{ts}.txt"
    report_path.write_text(content, encoding="utf-8")
    logger.info("Diagnostic report saved to %s", report_path)
    return report_path
