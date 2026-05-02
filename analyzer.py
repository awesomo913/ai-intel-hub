"""Trend detection, keyword extraction, relevance scoring, and categorization."""

import re
import logging
from collections import Counter
from datetime import datetime, timedelta

from . import database as db
from .sources import get_source_weight

logger = logging.getLogger(__name__)

# Keywords mapped to categories and their weight
CATEGORY_KEYWORDS = {
    "AI Agents": [
        "agent", "agentic", "autonomous", "autogpt", "crewai", "langgraph",
        "tool use", "function calling", "multi-agent", "agent framework",
        "agent sdk", "mcp", "model context protocol", "computer use"
    ],
    "Vibe Coding": [
        "vibe coding", "cursor", "copilot", "code generation", "ai coding",
        "ai ide", "windsurf", "cline", "aider", "claude code",
        "code assistant", "ai programmer", "devin", "codegen"
    ],
    "Local AI": [
        "local llm", "ollama", "llama.cpp", "gguf", "ggml", "mlx",
        "on-device", "edge ai", "local model", "private ai", "self-hosted",
        "vllm", "exllama", "quantization", "4-bit", "8-bit"
    ],
    "AI Models": [
        "gpt-4", "gpt-5", "claude", "gemini", "llama", "mistral", "phi",
        "qwen", "deepseek", "foundation model", "language model", "multimodal",
        "vision model", "reasoning model", "o1", "o3"
    ],
    "Breakthroughs": [
        "breakthrough", "state of the art", "sota", "record", "surpass",
        "revolutionary", "first ever", "milestone", "paradigm shift",
        "agi", "artificial general", "scaling law", "emergent"
    ],
    "AI Business": [
        "funding", "acquisition", "startup", "valuation", "revenue",
        "enterprise ai", "ai saas", "monetiz", "market", "competition",
        "business model", "roi", "ai adoption", "ai strategy"
    ],
    "AI Tools": [
        "api", "sdk", "framework", "library", "toolkit", "platform",
        "hugging face", "langchain", "llamaindex", "vector database",
        "rag", "embedding", "fine-tuning", "lora", "prompt engineering"
    ],
    "Open Source AI": [
        "open source", "open-source", "apache 2", "mit license", "weights",
        "open model", "community", "github", "huggingface", "release"
    ],
}

# High-signal keywords that boost relevance
HIGH_SIGNAL_KEYWORDS = [
    "launch", "release", "announce", "new model", "benchmark", "pricing",
    "free tier", "open source", "api", "developer", "integration",
    "competitive advantage", "disrupt", "10x", "game changer",
    "production ready", "enterprise", "scale"
]


def classify_article(title: str, summary: str, source_url: str = "") -> tuple[str, float]:
    """Classify an article into a category and compute relevance score.
    Returns (category, relevance_score)."""
    text = f"{title} {summary}".lower()
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                score += 1
                # Title matches count double
                if kw in title.lower():
                    score += 1
        if score > 0:
            scores[category] = score

    if not scores:
        return ("General AI", 0.3)

    best_category = max(scores, key=scores.get)
    raw_score = scores[best_category]

    # Boost for high-signal keywords
    signal_boost = sum(1 for kw in HIGH_SIGNAL_KEYWORDS if kw in text) * 0.05

    # Normalize to 0-1 range
    relevance = min(1.0, (raw_score / 5.0) + signal_boost)

    # Apply source credibility weight
    weight = get_source_weight(source_url)
    relevance = min(1.0, round(relevance * weight, 2))

    return (best_category, relevance)


def score_all_unscored() -> int:
    """Score and categorize all articles that haven't been scored yet."""
    conn = db.get_connection()
    try:
        # Use is_scored flag if column exists, fall back to old heuristic
        try:
            rows = conn.execute(
                """SELECT a.id, a.title, a.summary, s.url as source_url
                   FROM articles a
                   LEFT JOIN sources s ON a.source_id = s.id
                   WHERE a.is_scored = 0"""
            ).fetchall()
        except Exception:
            rows = conn.execute(
                """SELECT a.id, a.title, a.summary, s.url as source_url
                   FROM articles a
                   LEFT JOIN sources s ON a.source_id = s.id
                   WHERE a.category = '' OR a.relevance_score = 0.5"""
            ).fetchall()

        # Load feedback keywords once for all articles
        liked_kws, disliked_kws = db.get_feedback_keywords()

        count = 0
        for row in rows:
            source_url = row["source_url"] or ""
            category, score = classify_article(row["title"], row["summary"], source_url)

            # Apply feedback adjustments
            text = f"{row['title']} {row['summary']}".lower()
            if liked_kws:
                like_hits = sum(1 for kw in liked_kws if kw in text)
                score = min(1.0, score + like_hits * 0.01)
            if disliked_kws:
                dislike_hits = sum(1 for kw in disliked_kws if kw in text)
                score = max(0.0, score - dislike_hits * 0.01)

            try:
                conn.execute(
                    "UPDATE articles SET category = ?, relevance_score = ?, is_scored = 1 WHERE id = ?",
                    (category, round(score, 2), row["id"])
                )
            except Exception:
                conn.execute(
                    "UPDATE articles SET category = ?, relevance_score = ? WHERE id = ?",
                    (category, round(score, 2), row["id"])
                )
            count += 1
        conn.commit()
        logger.info("Scored %d articles", count)
        return count
    finally:
        conn.close()


def get_keyword_velocity(keyword: str, hours_back: int = 24) -> float:
    """Compare keyword frequency in last 24h vs prior 24h window.
    Returns a ratio clamped to [0.5, 2.0]. A keyword that doubled → 2.0x."""
    conn = db.get_connection()
    try:
        now = datetime.now()
        recent_start = (now - timedelta(hours=hours_back)).strftime("%Y-%m-%d %H:%M:%S")
        prior_start = (now - timedelta(hours=hours_back * 2)).strftime("%Y-%m-%d %H:%M:%S")

        recent_count = conn.execute(
            """SELECT COUNT(*) FROM articles
               WHERE (title LIKE ? OR summary LIKE ?)
               AND fetched_at >= ?""",
            (f"%{keyword}%", f"%{keyword}%", recent_start)
        ).fetchone()[0]

        prior_count = conn.execute(
            """SELECT COUNT(*) FROM articles
               WHERE (title LIKE ? OR summary LIKE ?)
               AND fetched_at >= ? AND fetched_at < ?""",
            (f"%{keyword}%", f"%{keyword}%", prior_start, recent_start)
        ).fetchone()[0]

        if prior_count == 0:
            return 1.0 if recent_count == 0 else 2.0
        ratio = recent_count / prior_count
        return max(0.5, min(2.0, ratio))
    finally:
        conn.close()


def titles_are_similar(t1: str, t2: str, threshold: float = 0.6) -> bool:
    """Check if two article titles overlap enough to be considered duplicates."""
    words1 = set(t1.lower().split())
    words2 = set(t2.lower().split())
    overlap = len(words1 & words2) / max(len(words1 | words2), 1)
    return overlap >= threshold


def is_duplicate_title(title: str, hours_back: int = 48) -> bool:
    """Return True if a similar title already exists in the DB within the given window."""
    conn = db.get_connection()
    try:
        cutoff = (datetime.now() - timedelta(hours=hours_back)).strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            "SELECT title FROM articles WHERE fetched_at >= ?", (cutoff,)
        ).fetchall()
        for row in rows:
            if titles_are_similar(title, row["title"]):
                return True
        return False
    finally:
        conn.close()


def get_trending_keywords(days: int = 7, top_n: int = 20) -> list[tuple[str, int]]:
    """Extract trending keywords from recent articles."""
    conn = db.get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT title, summary FROM articles WHERE fetched_at >= ?", (cutoff,)
        ).fetchall()

        word_counts = Counter()
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "it", "that", "this", "was", "are",
            "be", "has", "have", "had", "not", "what", "when", "where", "how",
            "all", "each", "every", "both", "few", "more", "most", "other", "some",
            "such", "no", "nor", "too", "very", "can", "will", "just", "should",
            "now", "its", "new", "also", "than", "into", "about", "up", "out",
            "one", "two", "first", "been", "said", "over", "after", "your", "you",
            "we", "our", "they", "their", "them", "who", "which", "would", "could",
            "do", "does", "did", "may", "might", "here", "there", "then", "so",
            "if", "as", "his", "her", "he", "she", "my", "me", "us", "an",
        }

        for row in rows:
            text = f"{row['title']} {row['summary']}".lower()
            words = re.findall(r'[a-z][a-z-]*[a-z]', text)
            for word in words:
                if word not in stop_words and len(word) >= 2:
                    word_counts[word] += 1

        # Also count bigrams
        for row in rows:
            text = f"{row['title']} {row['summary']}".lower()
            words = re.findall(r'[a-z][a-z-]*[a-z]', text)
            for i in range(len(words) - 1):
                if words[i] not in stop_words and words[i+1] not in stop_words:
                    bigram = f"{words[i]} {words[i+1]}"
                    word_counts[bigram] += 1

        return word_counts.most_common(top_n)
    finally:
        conn.close()


def get_category_trends(days: int = 7) -> dict[str, int]:
    """Get article counts per category for recent period."""
    conn = db.get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT category, COUNT(*) as cnt FROM articles
               WHERE fetched_at >= ? AND category != ''
               GROUP BY category ORDER BY cnt DESC""",
            (cutoff,)
        ).fetchall()
        return {r["category"]: r["cnt"] for r in rows}
    finally:
        conn.close()


def get_hot_topics(days: int = 3, min_mentions: int = 2) -> list[dict]:
    """Identify hot topics based on repeated mentions across sources."""
    conn = db.get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT title, summary, category, relevance_score, source_id
               FROM articles WHERE fetched_at >= ?
               ORDER BY relevance_score DESC""",
            (cutoff,)
        ).fetchall()

        # Group by similar titles (simplified dedup)
        topics = {}
        for row in rows:
            # Use first 5 significant words as key
            words = re.findall(r'[a-z]+', row["title"].lower())
            key_words = [w for w in words if len(w) > 3][:5]
            key = " ".join(sorted(key_words))
            if key not in topics:
                topics[key] = {
                    "title": row["title"],
                    "category": row["category"],
                    "mentions": 0,
                    "max_score": row["relevance_score"],
                    "sources": set(),
                }
            topics[key]["mentions"] += 1
            topics[key]["sources"].add(row["source_id"])
            topics[key]["max_score"] = max(topics[key]["max_score"], row["relevance_score"])

        hot = [
            {**v, "sources": len(v["sources"])}
            for v in topics.values()
            if v["mentions"] >= min_mentions
        ]
        hot.sort(key=lambda x: (x["sources"], x["mentions"], x["max_score"]), reverse=True)
        return hot[:15]
    finally:
        conn.close()


# --- Standouts & Groundbreaker ---

# Keywords that signal something is truly groundbreaking
GROUNDBREAKER_SIGNALS = [
    "breakthrough", "first ever", "world's first", "state of the art", "sota",
    "surpass human", "beats gpt", "beats claude", "new paradigm", "agi",
    "revolutioniz", "game chang", "orders of magnitude", "100x", "1000x",
    "open source release", "free for commercial", "zero cost",
    "real-time", "on-device", "runs on phone", "no gpu", "single gpu",
    "replaces", "eliminates the need", "fully autonomous",
    "new architecture", "transformer killer", "post-transformer",
    "raises $", "billion", "unicorn", "ipo", "acquired by",
]

# Boost categories that matter most for a coder/AI business person
STANDOUT_CATEGORY_BOOST = {
    "AI Agents": 1.5,
    "Vibe Coding": 1.4,
    "Local AI": 1.3,
    "Breakthroughs": 1.6,
    "AI Tools": 1.2,
    "Open Source AI": 1.3,
    "AI Business": 1.2,
    "AI Models": 1.1,
}


def _compute_standout_score(article: dict) -> float:
    """Compute a composite standout score for ranking the best articles."""
    base = article.get("relevance_score", 0.3)
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()

    # Groundbreaker signal boost
    signal_hits = sum(1 for s in GROUNDBREAKER_SIGNALS if s in text)
    signal_boost = min(0.4, signal_hits * 0.08)

    # Category importance boost
    cat = article.get("category", "")
    cat_mult = STANDOUT_CATEGORY_BOOST.get(cat, 1.0)

    # Recency boost (articles from today score higher)
    recency = 0.0
    pub = article.get("published_at", "")
    if pub:
        today = datetime.now().strftime("%Y-%m-%d")
        if pub.startswith(today):
            recency = 0.15
        elif pub >= (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"):
            recency = 0.08

    # Summary quality boost (longer = more substance)
    summary_len = len(article.get("summary", ""))
    substance = min(0.1, summary_len / 2000)

    # Title engagement signals
    title = article.get("title", "").lower()
    engagement = 0.0
    if any(w in title for w in ["how to", "guide", "tutorial", "build", "create"]):
        engagement = 0.05  # Actionable content
    if any(w in title for w in ["launch", "release", "announce", "introduce", "unveil"]):
        engagement = 0.08  # News-breaking

    score = (base * cat_mult) + signal_boost + recency + substance + engagement
    return min(1.0, round(score, 3))


def get_standouts(limit: int = 5, days: int = 3) -> list[dict]:
    """Get the top standout articles - the ones you absolutely need to read.
    Uses composite scoring: relevance + groundbreaker signals + category boost + recency."""
    conn = db.get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT a.*, s.name as source_name FROM articles a
               LEFT JOIN sources s ON a.source_id = s.id
               WHERE a.fetched_at >= ? AND a.relevance_score >= 0.3
               ORDER BY a.relevance_score DESC
               LIMIT 200""",
            (cutoff,)
        ).fetchall()

        articles = [dict(r) for r in rows]
        for a in articles:
            a["standout_score"] = _compute_standout_score(a)

        articles.sort(key=lambda x: x["standout_score"], reverse=True)

        # Deduplicate by similar titles
        seen_keys = set()
        unique = []
        for a in articles:
            words = re.findall(r'[a-z]+', a["title"].lower())
            key = " ".join(sorted(w for w in words if len(w) > 3)[:4])
            if key not in seen_keys:
                seen_keys.add(key)
                unique.append(a)
                if len(unique) >= limit:
                    break

        return unique
    finally:
        conn.close()


def get_groundbreaker(days: int = 7) -> dict | None:
    """Find THE single most groundbreaking article - the one thing you must check.
    Hardened criteria:
    - Must be published within last 12 hours (freshness gate)
    - Score >= 0.75 (quality gate)
    - Not already flagged as groundbreaker in last 6 hours (novelty gate)
    Falls back gracefully if no article meets all gates."""
    conn = db.get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        fresh_cutoff = (datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            """SELECT a.*, s.name as source_name FROM articles a
               LEFT JOIN sources s ON a.source_id = s.id
               WHERE a.fetched_at >= ?
               ORDER BY a.relevance_score DESC
               LIMIT 500""",
            (cutoff,)
        ).fetchall()

        if not rows:
            return None

        best = None
        best_score = 0.0

        for row in rows:
            a = dict(row)
            text = f"{a.get('title', '')} {a.get('summary', '')}".lower()

            # Count groundbreaker signal hits
            hits = sum(1 for s in GROUNDBREAKER_SIGNALS if s in text)

            # Must have at least 2 signals to be a real groundbreaker
            if hits < 2:
                continue

            score = _compute_standout_score(a) + (hits * 0.05)

            # Strong preference for breakthroughs category
            if a.get("category") == "Breakthroughs":
                score += 0.2

            if score > best_score:
                best_score = score
                best = a
                best["groundbreaker_score"] = round(score, 3)
                best["signal_hits"] = hits

        # Apply hardened gates if a strong candidate was found
        if best:
            article_id = best.get("id")
            fetched_at = best.get("fetched_at", "")
            passes_freshness = fetched_at >= fresh_cutoff if fetched_at else False
            passes_quality = best_score >= 0.75
            passes_novelty = not db.any_groundbreaker_recent(hours=6)

            if passes_freshness and passes_quality and passes_novelty:
                if article_id:
                    db.log_groundbreaker(article_id)
                return best

        # Fallback: look for any article with freshness + signals (no strict quality gate)
        for row in rows[:50]:
            a = dict(row)
            fetched_at = a.get("fetched_at", "")
            if fetched_at < cutoff:
                continue
            text = f"{a.get('title', '')} {a.get('summary', '')}".lower()
            hits = sum(1 for s in GROUNDBREAKER_SIGNALS if s in text)
            if hits >= 1:
                a["groundbreaker_score"] = _compute_standout_score(a)
                a["signal_hits"] = hits
                return a

        # Last resort: just the highest relevance article
        a = dict(rows[0])
        a["groundbreaker_score"] = a.get("relevance_score", 0.5)
        a["signal_hits"] = 0
        return a
    finally:
        conn.close()
