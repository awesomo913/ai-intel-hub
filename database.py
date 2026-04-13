"""SQLite database layer for articles, sources, strategies, and metadata."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .platform_utils import get_data_dir

logger = logging.getLogger(__name__)

DB_FILE = "ai_intel_hub.db"


def get_db_path() -> Path:
    return get_data_dir() / DB_FILE


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                feed_url TEXT NOT NULL,
                category TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                last_fetched TEXT,
                fetch_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                source_id INTEGER REFERENCES sources(id),
                summary TEXT DEFAULT '',
                content_snippet TEXT DEFAULT '',
                category TEXT DEFAULT '',
                relevance_score REAL DEFAULT 0.5,
                published_at TEXT,
                fetched_at TEXT DEFAULT (datetime('now')),
                is_bookmarked INTEGER DEFAULT 0,
                is_read INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#3b82f6'
            );

            CREATE TABLE IF NOT EXISTS article_tags (
                article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (article_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT DEFAULT '',
                trend_basis TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                rating INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                results_count INTEGER DEFAULT 0,
                searched_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_type TEXT NOT NULL,
                format TEXT NOT NULL,
                item_count INTEGER DEFAULT 0,
                exported_at TEXT DEFAULT (datetime('now')),
                file_path TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_id);
            CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
            CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
            CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(relevance_score);
            CREATE INDEX IF NOT EXISTS idx_articles_bookmarked ON articles(is_bookmarked);
            CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_articles_cat_score ON articles(category, relevance_score);
        """)
        conn.commit()

        # Schema migrations for existing databases
        for col_sql in [
            "ALTER TABLE articles ADD COLUMN is_scored INTEGER DEFAULT 0",
            "ALTER TABLE articles ADD COLUMN full_text TEXT DEFAULT ''",
            "ALTER TABLE articles ADD COLUMN has_full_text INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(col_sql)
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

        logger.info("Database initialized at %s", get_db_path())
    finally:
        conn.close()


# --- Article CRUD ---

def insert_article(title: str, url: str, source_id: int, summary: str = "",
                   content_snippet: str = "", category: str = "",
                   relevance_score: float = 0.5, published_at: str = "") -> Optional[int]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles
               (title, url, source_id, summary, content_snippet, category,
                relevance_score, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, url, source_id, summary, content_snippet, category,
             relevance_score, published_at)
        )
        conn.commit()
        return cur.lastrowid if cur.rowcount > 0 else None
    finally:
        conn.close()


def get_articles(limit: int = 100, offset: int = 0, category: str = "",
                 search: str = "", bookmarked_only: bool = False,
                 unread_only: bool = False, source_id: int = 0,
                 min_score: float = 0.0) -> list[dict]:
    conn = get_connection()
    try:
        query = """SELECT a.*, s.name as source_name
                   FROM articles a
                   LEFT JOIN sources s ON a.source_id = s.id
                   WHERE 1=1"""
        params = []
        if category:
            query += " AND a.category = ?"
            params.append(category)
        if search:
            query += " AND (a.title LIKE ? OR a.summary LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if bookmarked_only:
            query += " AND a.is_bookmarked = 1"
        if unread_only:
            query += " AND a.is_read = 0"
        if source_id:
            query += " AND a.source_id = ?"
            params.append(source_id)
        if min_score > 0:
            query += " AND a.relevance_score >= ?"
            params.append(min_score)
        query += " ORDER BY a.published_at DESC, a.fetched_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_article_count(category: str = "", search: str = "",
                      bookmarked_only: bool = False, unread_only: bool = False,
                      source_id: int = 0, min_score: float = 0.0) -> int:
    conn = get_connection()
    try:
        query = "SELECT COUNT(*) FROM articles WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (title LIKE ? OR summary LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if bookmarked_only:
            query += " AND is_bookmarked = 1"
        if unread_only:
            query += " AND is_read = 0"
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if min_score > 0:
            query += " AND relevance_score >= ?"
            params.append(min_score)
        return conn.execute(query, params).fetchone()[0]
    finally:
        conn.close()


def toggle_bookmark(article_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE articles SET is_bookmarked = CASE WHEN is_bookmarked = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (article_id,)
        )
        conn.commit()
    finally:
        conn.close()


def mark_read(article_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE articles SET is_read = 1 WHERE id = ?", (article_id,))
        conn.commit()
    finally:
        conn.close()


# --- Source CRUD ---

def insert_source(name: str, url: str, feed_url: str, category: str = "") -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO sources (name, url, feed_url, category) VALUES (?, ?, ?, ?)",
            (name, url, feed_url, category)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_sources(active_only: bool = False) -> list[dict]:
    conn = get_connection()
    try:
        query = "SELECT * FROM sources"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        return [dict(r) for r in conn.execute(query).fetchall()]
    finally:
        conn.close()


def update_source_fetch(source_id: int, success: bool = True) -> None:
    conn = get_connection()
    try:
        if success:
            conn.execute(
                "UPDATE sources SET last_fetched = datetime('now'), fetch_count = fetch_count + 1 WHERE id = ?",
                (source_id,)
            )
        else:
            conn.execute(
                "UPDATE sources SET error_count = error_count + 1 WHERE id = ?",
                (source_id,)
            )
        conn.commit()
    finally:
        conn.close()


def toggle_source(source_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE sources SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (source_id,)
        )
        conn.commit()
    finally:
        conn.close()


def delete_source(source_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM articles WHERE source_id = ?", (source_id,))
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        conn.commit()
    finally:
        conn.close()


# --- Strategy CRUD ---

def insert_strategy(title: str, description: str, category: str = "",
                    trend_basis: str = "") -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO strategies (title, description, category, trend_basis) VALUES (?, ?, ?, ?)",
            (title, description, category, trend_basis)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_strategies(limit: int = 50) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM strategies ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def rate_strategy(strategy_id: int, rating: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE strategies SET rating = ? WHERE id = ?", (rating, strategy_id))
        conn.commit()
    finally:
        conn.close()


# --- Full Text Enrichment ---

def get_articles_without_full_text(limit: int = 20) -> list[dict]:
    """Get recent articles that haven't been enriched with full text."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, url, title FROM articles
               WHERE has_full_text = 0
               ORDER BY fetched_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        # Column doesn't exist yet (pre-migration)
        return []
    finally:
        conn.close()


def update_full_text(article_id: int, full_text: str) -> None:
    """Store fetched full article text."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE articles SET full_text = ?, has_full_text = 1 WHERE id = ?",
            (full_text, article_id)
        )
        conn.commit()
    finally:
        conn.close()


# --- Database Maintenance ---

def vacuum_database() -> None:
    """Run VACUUM to reclaim space and defragment."""
    conn = get_connection()
    try:
        conn.execute("VACUUM")
    finally:
        conn.close()


def reset_source_errors() -> None:
    """Reset error counts for all sources."""
    conn = get_connection()
    try:
        conn.execute("UPDATE sources SET error_count = 0")
        conn.commit()
    finally:
        conn.close()


# --- Stats ---

def get_stats() -> dict:
    conn = get_connection()
    try:
        total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        unread = conn.execute("SELECT COUNT(*) FROM articles WHERE is_read = 0").fetchone()[0]
        bookmarked = conn.execute("SELECT COUNT(*) FROM articles WHERE is_bookmarked = 1").fetchone()[0]
        sources = conn.execute("SELECT COUNT(*) FROM sources WHERE is_active = 1").fetchone()[0]
        strategies = conn.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        today_articles = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE fetched_at >= ?", (today,)
        ).fetchone()[0]

        # Category breakdown
        cats = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM articles GROUP BY category ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        categories = {r["category"]: r["cnt"] for r in cats if r["category"]}

        # Top sources
        top = conn.execute(
            """SELECT s.name, COUNT(a.id) as cnt FROM sources s
               JOIN articles a ON a.source_id = s.id
               GROUP BY s.id ORDER BY cnt DESC LIMIT 10"""
        ).fetchall()
        top_sources = {r["name"]: r["cnt"] for r in top}

        return {
            "total_articles": total_articles,
            "unread": unread,
            "bookmarked": bookmarked,
            "active_sources": sources,
            "strategies": strategies,
            "today_articles": today_articles,
            "categories": categories,
            "top_sources": top_sources,
        }
    finally:
        conn.close()


# --- Search History ---

def log_search(query: str, results_count: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO search_history (query, results_count) VALUES (?, ?)",
            (query, results_count)
        )
        conn.commit()
    finally:
        conn.close()


# --- Export Log ---

def log_export(export_type: str, fmt: str, item_count: int, file_path: str = "") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO exports (export_type, format, item_count, file_path) VALUES (?, ?, ?, ?)",
            (export_type, fmt, item_count, file_path)
        )
        conn.commit()
    finally:
        conn.close()
