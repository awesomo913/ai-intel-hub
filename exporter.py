"""Export articles, strategies, and reports in multiple formats."""

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import database as db
from .platform_utils import get_export_dir
from .strategy import get_strategy_summary

logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception as e:
        logger.error("Clipboard copy failed: %s", e)
        return False


# --- Article Exports ---

def articles_to_markdown(articles: list[dict], title: str = "AI Intel Hub Report") -> str:
    """Convert articles to markdown format."""
    lines = [f"# {title}", f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
             f"*Total articles: {len(articles)}*\n"]

    current_cat = ""
    for a in articles:
        cat = a.get("category", "Uncategorized")
        if cat != current_cat:
            lines.append(f"\n## {cat}\n")
            current_cat = cat

        bookmark = " [Bookmarked]" if a.get("is_bookmarked") else ""
        score = f" (relevance: {a.get('relevance_score', 0):.0%})" if a.get("relevance_score") else ""
        lines.append(f"### [{a['title']}]({a['url']}){bookmark}{score}")
        if a.get("source_name"):
            lines.append(f"**Source:** {a['source_name']} | **Published:** {a.get('published_at', 'N/A')}")
        if a.get("summary"):
            lines.append(f"\n{a['summary'][:300]}\n")
        lines.append("---")

    return "\n".join(lines)


def articles_to_csv(articles: list[dict]) -> str:
    """Convert articles to CSV format."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "title", "url", "source_name", "category", "relevance_score",
        "published_at", "summary", "is_bookmarked", "is_read"
    ], extrasaction="ignore")
    writer.writeheader()
    for a in articles:
        writer.writerow(a)
    return output.getvalue()


def articles_to_json(articles: list[dict]) -> str:
    """Convert articles to JSON format."""
    clean = []
    for a in articles:
        item = {k: v for k, v in a.items() if v is not None}
        clean.append(item)
    return json.dumps({"articles": clean, "count": len(clean),
                        "exported": datetime.now().isoformat()}, indent=2)


def articles_to_text(articles: list[dict]) -> str:
    """Convert articles to plain text."""
    lines = [f"AI Intel Hub Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"Total: {len(articles)} articles", "=" * 60, ""]

    for a in articles:
        lines.append(f"[{a.get('category', '')}] {a['title']}")
        lines.append(f"  URL: {a['url']}")
        lines.append(f"  Source: {a.get('source_name', 'N/A')} | Score: {a.get('relevance_score', 0):.0%}")
        if a.get("summary"):
            lines.append(f"  {a['summary'][:200]}")
        lines.append("")

    return "\n".join(lines)


# --- File Export ---

def export_articles(articles: list[dict], fmt: str = "markdown",
                    dest_dir: Optional[Path] = None) -> Path:
    """Export articles to a file. Returns the file path."""
    if dest_dir is None:
        dest_dir = get_export_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()
    converters = {
        "markdown": (articles_to_markdown, f"ai_intel_report_{ts}.md"),
        "csv": (articles_to_csv, f"ai_intel_articles_{ts}.csv"),
        "json": (articles_to_json, f"ai_intel_articles_{ts}.json"),
        "text": (articles_to_text, f"ai_intel_report_{ts}.txt"),
    }

    converter, filename = converters.get(fmt, converters["markdown"])
    content = converter(articles)
    file_path = dest_dir / filename
    file_path.write_text(content, encoding="utf-8")

    db.log_export("articles", fmt, len(articles), str(file_path))
    logger.info("Exported %d articles to %s", len(articles), file_path)
    return file_path


def export_strategies(dest_dir: Optional[Path] = None) -> Path:
    """Export strategies to markdown file."""
    if dest_dir is None:
        dest_dir = get_export_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    content = get_strategy_summary()
    file_path = dest_dir / f"ai_intel_strategies_{_timestamp()}.md"
    file_path.write_text(content, encoding="utf-8")

    strategies = db.get_strategies()
    db.log_export("strategies", "markdown", len(strategies), str(file_path))
    return file_path


def articles_urls_only(articles: list[dict], fmt: str = "plain") -> str:
    """Export just URLs for bulk AI feeding. Formats: plain, markdown, numbered, csv, json."""
    if fmt == "plain":
        return "\n".join(a["url"] for a in articles if a.get("url"))
    elif fmt == "markdown":
        lines = []
        for a in articles:
            lines.append(f"- [{a['title'][:80]}]({a['url']})")
        return "\n".join(lines)
    elif fmt == "numbered":
        lines = []
        for i, a in enumerate(articles, 1):
            lines.append(f"{i}. {a['url']}")
        return "\n".join(lines)
    elif fmt == "titled":
        lines = []
        for a in articles:
            lines.append(f"{a['title']}")
            lines.append(f"  {a['url']}")
            lines.append("")
        return "\n".join(lines)
    elif fmt == "csv":
        lines = ["title,url,category,score"]
        for a in articles:
            t = a.get("title", "").replace('"', "'")
            lines.append(f'"{t}","{a["url"]}","{a.get("category", "")}","{a.get("relevance_score", 0)}"')
        return "\n".join(lines)
    elif fmt == "json":
        data = [{"title": a.get("title", ""), "url": a["url"],
                 "category": a.get("category", ""), "score": a.get("relevance_score", 0)}
                for a in articles if a.get("url")]
        return json.dumps(data, indent=2)
    elif fmt == "ai_prompt":
        lines = [
            "Here are URLs to AI industry articles. Please read and analyze them for key trends, "
            "breakthroughs, and actionable insights:\n"
        ]
        for i, a in enumerate(articles, 1):
            lines.append(f"{i}. [{a.get('category', '')}] {a.get('title', '')}")
            lines.append(f"   {a['url']}")
        lines.append(f"\nTotal: {len(articles)} articles. Summarize the top themes and opportunities.")
        return "\n".join(lines)
    else:
        return "\n".join(a["url"] for a in articles if a.get("url"))


def get_urls_by_category(category: str = "", min_score: float = 0.0,
                         limit: int = 500, bookmarked_only: bool = False) -> list[dict]:
    """Get articles filtered by category for bulk URL export."""
    return db.get_articles(
        limit=limit, category=category,
        min_score=min_score, bookmarked_only=bookmarked_only
    )


def export_full_report(dest_dir: Optional[Path] = None) -> Path:
    """Export comprehensive report with articles + strategies."""
    if dest_dir is None:
        dest_dir = get_export_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    articles = db.get_articles(limit=200)
    stats = db.get_stats()

    lines = [
        "# AI Intel Hub - Full Intelligence Report",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        "## Dashboard Summary\n",
        f"- **Total Articles:** {stats['total_articles']}",
        f"- **Unread:** {stats['unread']}",
        f"- **Bookmarked:** {stats['bookmarked']}",
        f"- **Active Sources:** {stats['active_sources']}",
        f"- **Strategies:** {stats['strategies']}",
        f"- **Today's Articles:** {stats['today_articles']}\n",
    ]

    if stats.get("categories"):
        lines.append("## Category Breakdown\n")
        for cat, cnt in stats["categories"].items():
            lines.append(f"- {cat}: {cnt}")
        lines.append("")

    lines.append(articles_to_markdown(articles, "Articles"))
    lines.append("\n---\n")
    lines.append(get_strategy_summary())

    content = "\n".join(lines)
    file_path = dest_dir / f"ai_intel_full_report_{_timestamp()}.md"
    file_path.write_text(content, encoding="utf-8")
    db.log_export("full_report", "markdown", len(articles), str(file_path))
    return file_path
