"""Local FastAPI server — lets Claude sessions and scripts query the intel feed.

Runs on http://localhost:7891 as a daemon thread inside the GUI app.
SQLite WAL mode means 50+ concurrent readers are safe without any locking.

Endpoints
---------
GET  /feed              — paginated article list
GET  /feed/top          — top N by relevance score
GET  /alerts            — articles above the breakthrough threshold
GET  /health            — server + DB status
POST /alerts/dismiss    — mark the current banner as seen
"""

import json
import logging
import threading
from typing import Optional

log = logging.getLogger(__name__)

_server_thread: Optional[threading.Thread] = None
_is_running = False

try:
    from fastapi import FastAPI, Query
    from fastapi.responses import JSONResponse
    import uvicorn
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    log.warning("fastapi/uvicorn not installed — API server disabled. Run: uv pip install fastapi uvicorn")


def _build_app():
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="AI Intel Hub API",
        description="Local read-only feed API for Claude sessions and automation scripts.",
        version="1.0.0",
    )

    @app.get("/health")
    def health():
        from . import database as db
        try:
            count = db.get_article_count()
            return {"status": "ok", "article_count": count}
        except Exception as exc:
            return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)

    @app.get("/feed")
    def feed(
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
        topic: str = Query("", description="Filter by keyword in title/summary"),
        category: str = Query("", description="Filter by category"),
        min_score: float = Query(0.0, ge=0.0, le=1.0),
        bookmarked: bool = Query(False),
    ):
        from . import database as db
        try:
            articles = db.get_articles(
                limit=limit + offset,
                search=topic or None,
                category=category or None,
                min_score=min_score,
                bookmarked_only=bookmarked,
            )
            page = articles[offset : offset + limit]
            return {
                "total": len(articles),
                "offset": offset,
                "limit": limit,
                "items": [_article_to_dict(a) for a in page],
            }
        except Exception as exc:
            log.error("API /feed error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.get("/feed/top")
    def feed_top(
        n: int = Query(10, ge=1, le=50),
        days: int = Query(7, ge=1, le=90),
    ):
        from .analyzer import get_standouts
        try:
            standouts = get_standouts(limit=n, days=days)
            return {"items": standouts}
        except Exception as exc:
            log.error("API /feed/top error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.get("/alerts")
    def alerts(threshold: float = Query(0.85, ge=0.0, le=1.0)):
        from . import database as db
        try:
            articles = db.get_articles(limit=50, min_score=threshold)
            return {
                "threshold": threshold,
                "count": len(articles),
                "items": [_article_to_dict(a) for a in articles],
            }
        except Exception as exc:
            log.error("API /alerts error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.post("/alerts/dismiss")
    def dismiss_alert():
        from .notification_service import mark_banner_seen
        try:
            mark_banner_seen()
            return {"dismissed": True}
        except Exception as exc:
            log.error("API /alerts/dismiss error: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=500)

    return app


def _article_to_dict(row) -> dict:
    """Convert a sqlite3.Row (or dict) to a plain dict safe for JSON."""
    if hasattr(row, "keys"):
        return dict(row)
    return row


def start_server(port: int = 7891, host: str = "127.0.0.1") -> bool:
    """Start the API server in a background daemon thread.

    Returns True if started, False if fastapi/uvicorn is not installed or
    a server is already running.
    """
    global _server_thread, _is_running

    if not _FASTAPI_AVAILABLE:
        log.warning("API server skipped — fastapi/uvicorn not available")
        return False

    if _is_running:
        log.info("API server already running on port %d", port)
        return True

    app = _build_app()

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        loop="asyncio",
        access_log=False,
    )
    server = uvicorn.Server(config)

    def _run():
        global _is_running
        _is_running = True
        log.info("API server starting on http://%s:%d", host, port)
        try:
            server.run()
        except Exception as exc:
            log.error("API server crashed: %s", exc)
        finally:
            _is_running = False

    _server_thread = threading.Thread(target=_run, name="aih-api-server", daemon=True)
    _server_thread.start()
    return True


def stop_server() -> None:
    global _is_running
    _is_running = False
