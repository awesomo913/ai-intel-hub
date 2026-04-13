"""Full article text fetcher — bridges auto_scraper and CDP for enrichment.

Three-tier strategy:
1. HTTP fetch via auto_scraper (fast, works for most URLs)
2. CDP fetch via cdp_client (for JS-heavy pages returning empty via HTTP)
3. Ollama analysis (optional, for AI-powered extraction)
"""

import logging
import sys
import time
from pathlib import Path

from . import database as db

logger = logging.getLogger(__name__)

# Add parent directory to import auto_scraper and cdp_client
_AI_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))


def _http_fetch(url: str, timeout: int = 15) -> dict:
    """Tier 1: Use auto_scraper's Fetcher + Parser for HTTP fetch."""
    try:
        from auto_scraper.scraper import Fetcher, Parser
        fetcher = Fetcher(delay=0.5, max_retries=1, timeout=timeout)
        parser = Parser()
        resp = fetcher.get(url)
        page = parser.parse(resp.text, url)
        return {
            "text": page.text.strip(),
            "title": page.title,
            "meta": page.meta,
            "error": None,
        }
    except ImportError:
        return {"text": "", "title": "", "meta": {}, "error": "auto_scraper not available"}
    except Exception as e:
        return {"text": "", "title": "", "meta": {}, "error": str(e)}


def _cdp_fetch(url: str) -> dict:
    """Tier 2: Use CDP to extract text from a browser tab (JS-heavy pages)."""
    try:
        cdp_path = _AI_ROOT / "claude interaction tool"
        if str(cdp_path) not in sys.path:
            sys.path.insert(0, str(cdp_path))

        from cdp_client import discover_cdp_targets, CDPConnection

        # Check if any CDP port is available
        for port in [9222, 9223, 9224, 9225]:
            try:
                targets = discover_cdp_targets(port=port)
                if not targets:
                    continue

                # Find a tab with matching URL or navigate
                conn = None
                for t in targets:
                    if t.ws_url:
                        conn = CDPConnection(t.ws_url)
                        if conn.connect():
                            # Navigate to the article URL
                            conn.evaluate_js(f"window.location.href = '{url}'")
                            time.sleep(3)  # Wait for page load
                            # Extract text
                            text = conn.evaluate_js(
                                "document.querySelector('main, article, .content, .post-body, body')"
                                "?.innerText || document.body.innerText || ''"
                            )
                            title = conn.evaluate_js("document.title || ''")
                            conn.close()
                            if text and len(str(text)) > 100:
                                return {
                                    "text": str(text).strip()[:10000],
                                    "title": str(title),
                                    "meta": {},
                                    "error": None,
                                }
                            break
                if conn:
                    conn.close()
            except Exception:
                continue

        return {"text": "", "title": "", "meta": {}, "error": "CDP not available or page empty"}
    except ImportError:
        return {"text": "", "title": "", "meta": {}, "error": "cdp_client not available"}
    except Exception as e:
        return {"text": "", "title": "", "meta": {}, "error": str(e)}


def fetch_full_article(url: str, timeout: int = 15, use_cdp_fallback: bool = True) -> dict:
    """Fetch full article text with tiered fallback.

    Returns dict with keys: text, title, meta, error
    """
    # Tier 1: HTTP fetch (fast, no browser needed)
    result = _http_fetch(url, timeout=timeout)
    if result["text"] and len(result["text"]) > 100:
        return result

    # Tier 2: CDP fallback for JS-heavy pages
    if use_cdp_fallback:
        logger.debug("HTTP fetch got short text for %s, trying CDP...", url)
        cdp_result = _cdp_fetch(url)
        if cdp_result["text"] and len(cdp_result["text"]) > 100:
            return cdp_result

    # Return whatever we got (may be short or error)
    if result["text"]:
        return result
    return {"text": "", "title": "", "meta": {},
            "error": result.get("error") or "Could not extract meaningful text"}


def enrich_articles_batch(articles: list[dict], delay: float = 1.0,
                          progress_callback=None) -> dict:
    """Fetch full text for a batch of articles and store in DB.

    Args:
        articles: List of dicts with 'id' and 'url' keys
        delay: Seconds between requests
        progress_callback: func(done, total, url)

    Returns:
        {"enriched": N, "failed": M, "skipped": K}
    """
    enriched = 0
    failed = 0
    skipped = 0
    total = len(articles)

    for i, article in enumerate(articles):
        url = article.get("url", "")
        article_id = article.get("id")
        if not url or not article_id:
            skipped += 1
            continue

        try:
            result = fetch_full_article(url, use_cdp_fallback=False)  # Skip CDP for batch
            if result["text"] and len(result["text"]) > 50:
                db.update_full_text(article_id, result["text"][:10000])
                enriched += 1
            else:
                failed += 1
        except Exception as e:
            logger.debug("Failed to enrich %s: %s", url, e)
            failed += 1

        if progress_callback:
            progress_callback(i + 1, total, url)

        if i < total - 1:
            time.sleep(delay)

    logger.info("Enrichment complete: %d enriched, %d failed, %d skipped",
                enriched, failed, skipped)
    return {"enriched": enriched, "failed": failed, "skipped": skipped}
