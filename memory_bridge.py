"""Claude memory bridge — surface intel items that match active project context.

Reads ~/.claude/projects/.../memory/*.md files, extracts keywords from them,
then queries the local SQLite feed for matching articles. This is how the hub
"knows" what's relevant to whatever you're working on right now.

Also writes new breakthroughs back as memory hints so future Claude sessions
can pick them up without you having to paste them in.
"""

import logging
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_MEMORY_ROOT = Path.home() / ".claude" / "projects"
_MEMORY_HINT_FILE = Path.home() / ".claude" / "tmp" / "intel_hints.md"

_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "were", "be", "been", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "this", "that", "these", "those", "from", "by", "as", "if",
    "not", "so", "we", "you", "it", "its", "also", "when", "how", "use",
    "using", "used", "can", "all", "any", "each", "more", "no", "new",
})


def _extract_keywords(text: str, max_kw: int = 30) -> list[str]:
    """Pull meaningful words (length ≥ 4, non-stop-word) from markdown text."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{3,}", text.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for w in words:
        if w not in _STOP_WORDS and w not in seen:
            seen.add(w)
            keywords.append(w)
        if len(keywords) >= max_kw:
            break
    return keywords


def get_active_project_contexts() -> list[str]:
    """Collect keyword strings from all Claude memory files.

    Each entry in the returned list is a space-joined set of keywords
    from one memory file. The caller can use these as search terms.
    """
    if not _MEMORY_ROOT.exists():
        return []

    contexts: list[str] = []
    for md_file in _MEMORY_ROOT.rglob("memory/*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            kws = _extract_keywords(text)
            if kws:
                contexts.append(" ".join(kws[:15]))
        except OSError as exc:
            log.warning("Could not read memory file %s: %s", md_file, exc)

    log.debug("Extracted %d context blocks from memory files", len(contexts))
    return contexts


def surface_relevant_intel(
    contexts: Optional[list[str]] = None,
    limit: int = 10,
    min_score: float = 0.4,
) -> list[dict]:
    """Return articles from the DB that match the current memory context.

    Args:
        contexts: keyword strings from get_active_project_contexts().
                  If None, fetches them fresh.
        limit: max articles to return.
        min_score: minimum relevance score.

    Returns:
        List of article dicts, sorted by relevance descending.
    """
    from . import database as db

    if contexts is None:
        contexts = get_active_project_contexts()

    if not contexts:
        return db.get_articles(limit=limit, min_score=min_score) or []

    combined_terms = " ".join(contexts)
    all_words = _extract_keywords(combined_terms, max_kw=20)

    results: dict[int, dict] = {}
    for word in all_words[:8]:
        try:
            matches = db.get_articles(limit=50, search=word, min_score=min_score)
            for art in (matches or []):
                art_id = art.get("id") if hasattr(art, "get") else art["id"]
                if art_id not in results:
                    results[art_id] = dict(art)
        except Exception as exc:
            log.warning("DB search failed for term '%s': %s", word, exc)

    sorted_results = sorted(
        results.values(),
        key=lambda a: a.get("relevance_score", 0.0),
        reverse=True,
    )
    return sorted_results[:limit]


def write_intel_hint(
    title: str,
    url: str,
    summary: str,
    score: float,
) -> None:
    """Append a high-scoring article to the intel hints file.

    Future Claude sessions will see this file in memory and can reference it
    without the user having to paste anything in.
    """
    _MEMORY_HINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    from datetime import date
    line = (
        f"\n## {date.today()} | Score {score:.2f} | {title}\n"
        f"- URL: {url}\n"
        f"- {summary[:200]}\n"
    )
    try:
        with _MEMORY_HINT_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
        log.debug("Intel hint written: %s", title[:50])
    except OSError as exc:
        log.warning("Could not write intel hint: %s", exc)


def flush_hints_to_standout_memory(top_n: int = 5) -> int:
    """Pull top articles and write them as hints (called on fetch complete).

    Returns count of hints written.
    """
    from .analyzer import get_standouts
    try:
        standouts = get_standouts(limit=top_n, days=1)
    except Exception as exc:
        log.warning("Could not get standouts for memory flush: %s", exc)
        return 0

    written = 0
    for art in standouts:
        write_intel_hint(
            title=art.get("title", ""),
            url=art.get("url", ""),
            summary=art.get("summary", ""),
            score=art.get("relevance_score", 0.0),
        )
        written += 1
    return written
