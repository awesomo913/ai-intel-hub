"""RSS feed parser and web scraper with retry logic."""

import logging
import random
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional
from html import unescape

import feedparser
import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

from . import database as db

logger = logging.getLogger(__name__)

USER_AGENT = "AIIntelHub/1.0 (RSS Reader; +https://github.com/ai-intel-hub)"
REQUEST_TIMEOUT = 15
MAX_WORKERS = 6
MAX_RETRIES = 2
RETRY_DELAY = 2


def _clean_html(html_text: str) -> str:
    """Strip HTML tags and clean up text."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:1000]


def _parse_date(entry) -> str:
    """Extract publication date from feed entry."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                dt = datetime(*parsed[:6])
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            return val[:25]
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fetch_feed(url: str, timeout: int = REQUEST_TIMEOUT,
                max_retries: int = MAX_RETRIES,
                retry_delay: int = RETRY_DELAY) -> Optional[feedparser.FeedParserDict]:
    """Fetch and parse an RSS/Atom feed with retries."""
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                url, timeout=timeout,
                headers={"User-Agent": USER_AGENT}
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            if feed.bozo and not feed.entries:
                logger.warning("Feed parse error for %s: %s", url, feed.bozo_exception)
                return None
            if feed.bozo and feed.entries:
                logger.debug("Feed %s is malformed but parseable: %s", url, feed.bozo_exception)
            return feed
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(retry_delay * (attempt + 1))
            else:
                logger.error("Failed to fetch %s after %d retries: %s", url, max_retries, e)
                return None
    return None


def fetch_source(source: dict, max_articles: int = 50,
                 timeout: int = REQUEST_TIMEOUT, max_retries: int = MAX_RETRIES,
                 retry_delay: int = RETRY_DELAY) -> int:
    """Fetch articles from a single source. Returns count of new articles."""
    feed_url = source.get("feed_url", "")
    if not feed_url:
        return 0

    feed = _fetch_feed(feed_url, timeout=timeout, max_retries=max_retries,
                       retry_delay=retry_delay)
    if not feed:
        db.update_source_fetch(source["id"], success=False)
        return 0

    new_count = 0
    for entry in feed.entries[:max_articles]:
        title = _clean_html(entry.get("title", "")).strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        # Title similarity dedup: skip if too similar to a recent article
        try:
            from .analyzer import is_duplicate_title
            if is_duplicate_title(title):
                logger.debug("Skipping duplicate title: %s", title[:60])
                continue
        except Exception:
            pass

        summary = ""
        if hasattr(entry, "summary"):
            summary = _clean_html(entry.summary)
        elif hasattr(entry, "description"):
            summary = _clean_html(entry.description)

        content_snippet = ""
        if hasattr(entry, "content") and entry.content:
            content_snippet = _clean_html(entry.content[0].get("value", ""))

        published = _parse_date(entry)

        article_id = db.insert_article(
            title=title,
            url=link,
            source_id=source["id"],
            summary=summary or content_snippet[:500],
            content_snippet=content_snippet,
            category=source.get("category", ""),
            published_at=published,
        )
        if article_id:
            new_count += 1

    db.update_source_fetch(source["id"], success=True)
    logger.info("Fetched %d new articles from %s", new_count, source["name"])
    return new_count


def fetch_all_sources(max_articles: int = 50, max_workers: int = MAX_WORKERS,
                      timeout: int = REQUEST_TIMEOUT, max_retries: int = MAX_RETRIES,
                      retry_delay: int = RETRY_DELAY,
                      progress_callback=None) -> dict:
    """Fetch from all active sources in parallel. Returns summary stats."""
    sources = db.get_sources(active_only=True)
    total_new = 0
    total_errors = 0
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for source in sources:
            future = executor.submit(fetch_source, source, max_articles,
                                     timeout=timeout, max_retries=max_retries,
                                     retry_delay=retry_delay)
            futures[future] = source

        completed = 0
        for future in as_completed(futures):
            source = futures[future]
            completed += 1
            try:
                count = future.result()
                total_new += count
                results[source["name"]] = {"new": count, "status": "ok"}
            except Exception as e:
                total_errors += 1
                results[source["name"]] = {"new": 0, "status": f"error: {e}"}
                logger.error("Error fetching %s: %s", source["name"], e)

            if progress_callback:
                progress_callback(completed, len(sources), source["name"])

    return {
        "total_new": total_new,
        "total_sources": len(sources),
        "errors": total_errors,
        "details": results,
    }


AI_KEYWORDS = [
    "ai", "llm", "gpt", "transformer", "neural", "ml", "machine-learning",
    "deep-learning", "agent", "diffusion", "langchain", "rag", "embedding",
    "fine-tun", "lora", "ollama", "vllm", "gguf", "ggml", "whisper",
    "stable-diffusion", "comfyui", "chatbot", "copilot", "inference",
    "multimodal", "vision", "nlp", "bert", "mistral", "llama", "gemma",
    "claude", "openai", "anthropic", "huggingface", "tokenizer", "mcp",
    "agentic", "crewai", "autogen", "dspy", "cursor", "cline", "aider",
    "code-gen", "codegen", "text-gen", "image-gen", "speech", "tts", "stt",
    "reasoning", "chain-of-thought", "moe", "mixture", "quantiz", "pruning",
]


def _parse_github_page(html: str) -> list[dict]:
    """Parse a GitHub trending/search page and extract repos.

    Uses multiple selector strategies with fallbacks so GitHub
    redesigns don't silently break scraping.
    """
    soup = BeautifulSoup(html, "html.parser")
    repos = []
    seen_urls = set()

    def _add_repo(name, desc, href, stars="0", lang=""):
        text_lower = f"{name} {desc}".lower()
        if not any(kw in text_lower for kw in AI_KEYWORDS):
            return
        url = f"https://github.com{href}" if not href.startswith("http") else href
        if url in seen_urls:
            return
        seen_urls.add(url)
        repos.append({
            "name": name, "description": desc, "url": url,
            "stars": stars, "language": lang,
        })

    # Strategy 1: Current trending page selectors
    for article in soup.select("article.Box-row, article[class*='Box-row']"):
        name_el = article.select_one("h2 a, h1 a")
        desc_el = article.select_one("p")
        if not name_el:
            continue
        name = name_el.get_text(strip=True).replace("\n", "").replace(" ", "")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        href = name_el.get("href", "")
        stars_el = article.select_one("a[href*='/stargazers']")
        stars = stars_el.get_text(strip=True).replace(",", "") if stars_el else "0"
        lang_el = article.select_one("[itemprop='programmingLanguage']")
        lang = lang_el.get_text(strip=True) if lang_el else ""
        _add_repo(name, desc, href, stars, lang)

    # Strategy 2: Search results format
    if not repos:
        for item in soup.select("div.search-title a, div[class*='search'] a[href*='/']"):
            href = item.get("href", "")
            if href.count("/") == 2 and not href.startswith("http"):
                name = item.get_text(strip=True).replace("\n", "").replace(" ", "")
                parent = item.find_parent("div")
                desc = ""
                if parent:
                    desc_el = parent.find_next_sibling("p") or parent.select_one("p")
                    if desc_el:
                        desc = desc_el.get_text(strip=True)
                _add_repo(name, desc, href)

    # Strategy 3: Broad fallback — find all links matching /<owner>/<repo> pattern
    if not repos:
        import re as _re
        repo_pattern = _re.compile(r"^/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not repo_pattern.match(href):
                continue
            # Skip non-repo links
            if any(skip in href for skip in ["/login", "/signup", "/settings",
                   "/explore", "/topics", "/trending", "/features", "/about"]):
                continue
            name = href.lstrip("/")
            desc_el = a.find_next("p")
            desc = desc_el.get_text(strip=True)[:200] if desc_el else ""
            _add_repo(name, desc, href)

    if not repos and len(html) > 1000:
        logger.warning("GitHub page parsed 0 repos — selectors may be outdated (html=%d bytes)", len(html))

    return repos


def _fetch_github_api_fallback(query: str, per_page: int = 15) -> list[dict]:
    """Fallback: use GitHub Search API (no auth needed for basic queries)."""
    try:
        url = "https://api.github.com/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT,
                            headers={"Accept": "application/vnd.github.v3+json",
                                     "User-Agent": USER_AGENT})
        if resp.status_code == 403:
            logger.debug("GitHub API rate limited for query: %s", query)
            return []
        resp.raise_for_status()
        items = resp.json().get("items", [])
        repos = []
        for item in items:
            text = f"{item.get('full_name', '')} {item.get('description', '')}".lower()
            if any(kw in text for kw in AI_KEYWORDS):
                repos.append({
                    "name": item.get("full_name", ""),
                    "description": item.get("description", "") or "",
                    "url": item.get("html_url", ""),
                    "stars": str(item.get("stargazers_count", 0)),
                    "language": item.get("language", "") or "",
                })
        return repos
    except Exception as e:
        logger.debug("GitHub API fallback failed for '%s': %s", query, e)
        return []


def scrape_github_trending() -> list[dict]:
    """Scrape GitHub trending repos for AI-related projects - basic scan."""
    url = "https://github.com/trending?spoken_language_code=en"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT,
                            headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        repos = _parse_github_page(resp.text)
        if repos:
            return repos
    except Exception as e:
        logger.error("Failed to scrape GitHub trending page: %s", e)

    # HTML parsing got 0 results — try GitHub API fallback
    logger.info("Trying GitHub API fallback for trending repos...")
    repos = _fetch_github_api_fallback("stars:>500 language:python topic:llm", per_page=20)
    repos += _fetch_github_api_fallback("stars:>500 topic:ai-agents", per_page=10)
    # Deduplicate
    seen = set()
    unique = []
    for r in repos:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique


GITHUB_DEEP_WORKERS = 4
GITHUB_JITTER_MIN = 0.3
GITHUB_JITTER_MAX = 1.2


def _fetch_github_page_with_jitter(url: str,
                                   session: requests.Session) -> list[dict]:
    """Fetch a single GitHub page with anti-rate-limit jitter.
    Returns list of parsed repos (may be empty on error)."""
    time.sleep(random.uniform(GITHUB_JITTER_MIN, GITHUB_JITTER_MAX))
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.debug("GitHub %d for %s", resp.status_code, url)
            return []

        # Topic pages have a different structure than trending
        if "/topics/" in url:
            return _parse_topic_page(resp.text)
        return _parse_github_page(resp.text)
    except requests.RequestException as e:
        logger.debug("GitHub fetch error for %s: %s", url, e)
        return []


def _parse_topic_page(html: str) -> list[dict]:
    """Parse a GitHub /topics/ page."""
    soup = BeautifulSoup(html, "html.parser")
    repos = []
    for article in soup.select("article"):
        name_el = article.select_one("h3 a")
        desc_el = article.select_one("p")
        if not name_el:
            continue
        name = name_el.get_text(strip=True).replace("\n", "").replace(" ", "")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        href = name_el.get("href", "")
        if href and href.count("/") >= 2:
            repo_url = f"https://github.com{href}" if not href.startswith("http") else href
            stars_el = (article.select_one("[aria-label*='star']")
                        or article.select_one("span.Counter"))
            stars = stars_el.get_text(strip=True).replace(",", "") if stars_el else "0"
            repos.append({
                "name": name, "description": desc,
                "url": repo_url, "stars": stars, "language": "",
            })
    return repos


def scrape_github_deep() -> list[dict]:
    """Deep GitHub scan — parallel with jitter rate limiting.
    Uses requests.Session for TCP pooling, ThreadPoolExecutor(4 workers),
    and random 0.3-1.2s jitter per request to prevent 403 blocks."""
    all_urls = [
        # 1. Trending pages (7)
        "https://github.com/trending?since=daily&spoken_language_code=en",
        "https://github.com/trending?since=weekly&spoken_language_code=en",
        "https://github.com/trending/python?since=daily",
        "https://github.com/trending/python?since=weekly",
        "https://github.com/trending/typescript?since=daily",
        "https://github.com/trending/rust?since=daily",
        "https://github.com/trending/jupyter-notebook?since=weekly",
        # 2. Topic pages (12)
        "https://github.com/topics/llm",
        "https://github.com/topics/ai-agents",
        "https://github.com/topics/machine-learning",
        "https://github.com/topics/large-language-models",
        "https://github.com/topics/generative-ai",
        "https://github.com/topics/rag",
        "https://github.com/topics/langchain",
        "https://github.com/topics/stable-diffusion",
        "https://github.com/topics/fine-tuning",
        "https://github.com/topics/local-llm",
        "https://github.com/topics/ai-coding",
        "https://github.com/topics/mcp",
    ]

    # 3. Search pages (8)
    search_queries = [
        "llm agent framework", "ai coding assistant",
        "local llm inference", "rag pipeline",
        "mcp server", "ai automation tool",
        "fine-tuning lora", "vibe coding",
    ]
    for q in search_queries:
        all_urls.append(
            f"https://github.com/search?q={q.replace(' ', '+')}&type=repositories&s=stars&o=desc"
        )

    all_repos = {}

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        with ThreadPoolExecutor(max_workers=GITHUB_DEEP_WORKERS) as executor:
            futures = {
                executor.submit(_fetch_github_page_with_jitter, url, session): url
                for url in all_urls
            }

            for future in as_completed(futures):
                url = futures[future]
                try:
                    repos = future.result()
                    for repo in repos:
                        all_repos[repo["url"]] = repo
                except Exception as e:
                    logger.debug("GitHub deep scan error for %s: %s", url, e)

    result = list(all_repos.values())
    logger.info("Deep GitHub scan found %d AI repos from %d pages (parallel)",
                len(result), len(all_urls))
    return result
