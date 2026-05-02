"""Main application window with sidebar navigation, status bar, session tracking, and auto-refresh."""

import logging
import threading
import time
import customtkinter as ctk
from datetime import datetime

from .theme import FONTS, get_theme
from .widgets import ToastNotification
from .dashboard import DashboardView
from .feed_view import FeedView
from .strategy_view import StrategyView
from .export_view import ExportView
from .sources_view import SourcesView
from .settings_view import SettingsView
from .health_view import HealthView
from .email_view import EmailView
from ..config import AppConfig, load_config, save_config
from .. import database as db
from ..sources import get_default_sources
from ..scraper import fetch_all_sources, scrape_github_trending, scrape_github_deep
from ..analyzer import score_all_unscored
from ..session_manager import SessionTracker
from ..perf_logger import log_event

logger = logging.getLogger(__name__)


class AIIntelHub(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self._config = load_config()
        self._theme = get_theme(self._config.theme)
        self._is_fetching = False
        self._is_closing = False
        self._auto_refresh_job = None
        self._session = SessionTracker() if self._config.session_tracking_enabled else None

        # Window setup
        self.title("AI Intel Hub - AI Industry Intelligence")
        self.geometry(f"{self._config.window_width}x{self._config.window_height}")
        self.minsize(900, 600)
        ctk.set_appearance_mode(self._config.theme)
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=self._theme["bg"])

        # Initialize database and sources
        db.init_db()
        self._seed_sources()

        # Layout
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Sidebar
        self._create_sidebar()

        # Content area
        self.content = ctk.CTkFrame(self, fg_color=self._theme["bg"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

        # Status bar
        self._create_status_bar()

        # Create views
        self._views = {}
        self._create_views()

        # Show dashboard
        self._show_view("dashboard")

        # Keyboard shortcuts
        self._bind_shortcuts()

        # Auto-fetch on first launch if DB is empty
        if db.get_article_count() == 0 and self._config.fetch_on_startup:
            self.after(500, self._fetch_all)
        else:
            # Ensure scores are up to date
            self.after(200, lambda: score_all_unscored())

        # Start auto-refresh
        if self._config.auto_refresh_enabled:
            self._schedule_auto_refresh()

        # Graceful shutdown
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _seed_sources(self):
        """Add default sources if none exist."""
        existing = db.get_sources()
        if not existing:
            for name, url, feed_url, category in get_default_sources():
                db.insert_source(name, url, feed_url, category)
            logger.info("Seeded %d default sources", len(get_default_sources()))

    def _create_sidebar(self):
        t = self._theme
        self.sidebar = ctk.CTkFrame(
            self, fg_color=t["sidebar_bg"], width=self._config.sidebar_width,
            corner_radius=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", rowspan=2)
        self.sidebar.grid_propagate(False)

        # App title
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(20, 5))
        ctk.CTkLabel(
            title_frame, text="\U0001F9E0", font=("Segoe UI", 28)
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            title_frame, text="AI Intel Hub", font=FONTS["heading"],
            text_color=t["accent"]
        ).pack(side="left")

        ctk.CTkLabel(
            self.sidebar, text="Intelligence Tracker v2.0",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        ).pack(padx=15, pady=(0, 20))

        # Navigation buttons
        self._nav_buttons = {}
        nav_items = [
            ("dashboard", "\U0001F4CA Dashboard", "Ctrl+D"),
            ("feed", "\U0001F4F0 Articles", "Ctrl+1"),
            ("strategies", "\U0001F4A1 Strategies", "Ctrl+2"),
            ("email", "\U0001F4E7 Email", "Ctrl+M"),
            ("export", "\U0001F4E4 Export", "Ctrl+E"),
            ("sources", "\U0001F310 Sources", "Ctrl+3"),
            ("health", "\U0001F3E5 Health & Logs", "Ctrl+H"),
            ("settings", "\u2699\uFE0F Settings", "Ctrl+4"),
        ]
        for key, label, shortcut in nav_items:
            btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            btn_frame.pack(fill="x", padx=10, pady=1)

            btn = ctk.CTkButton(
                btn_frame, text=f"  {label}", font=FONTS["body"],
                height=38, corner_radius=8,
                fg_color="transparent", hover_color=t["sidebar_active"],
                text_color=t["fg"], anchor="w",
                command=lambda k=key: self._show_view(k)
            )
            btn.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                btn_frame, text=shortcut, font=FONTS["body_sm"],
                text_color=t["fg_muted"], width=50
            ).pack(side="right", padx=(0, 4))

            self._nav_buttons[key] = btn

        # Spacer
        ctk.CTkFrame(self.sidebar, fg_color="transparent", height=15).pack(fill="x")

        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            self.sidebar, text="\U0001F504 Refresh All Feeds",
            font=FONTS["button"], height=40, corner_radius=8,
            fg_color=t["accent"], hover_color=t["accent_hover"],
            command=self._fetch_all
        )
        self.refresh_btn.pack(fill="x", padx=10, pady=5)

        # GitHub buttons
        ctk.CTkButton(
            self.sidebar, text="\U0001F4BB GitHub Quick Scan",
            font=FONTS["button"], height=34, corner_radius=8,
            fg_color=t["bg_card"], hover_color=t["bg_card_hover"],
            text_color=t["fg"],
            command=self._fetch_github
        ).pack(fill="x", padx=10, pady=2)

        ctk.CTkButton(
            self.sidebar, text="\U0001F50D GitHub Deep Scan",
            font=FONTS["button"], height=34, corner_radius=8,
            fg_color=t["bg_card"], hover_color=t["bg_card_hover"],
            text_color="#fcc419",
            command=self._fetch_github_deep
        ).pack(fill="x", padx=10, pady=2)

        self.enrich_btn = ctk.CTkButton(
            self.sidebar, text="\U0001F4D6 Enrich Articles",
            font=FONTS["button"], height=34, corner_radius=8,
            fg_color=t["bg_card"], hover_color=t["bg_card_hover"],
            text_color="#69db7c",
            command=self._enrich_articles
        )
        self.enrich_btn.pack(fill="x", padx=10, pady=2)

        # Bottom info
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=15, pady=15)

        self.last_refresh_label = ctk.CTkLabel(
            bottom, text="Last refresh: Never",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self.last_refresh_label.pack(anchor="w")

        self.session_label = ctk.CTkLabel(
            bottom, text=f"Session: {self._session.session_id[:8] if self._session else 'off'}",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self.session_label.pack(anchor="w")

        ctk.CTkLabel(
            bottom, text=f"Profile: {self._config.active_profile}",
            font=FONTS["body_sm"], text_color=t["accent"]
        ).pack(anchor="w")

    def _create_status_bar(self):
        t = self._theme
        self.status_bar = ctk.CTkFrame(
            self, fg_color=t["bg_secondary"], height=28, corner_radius=0
        )
        self.status_bar.grid(row=1, column=1, sticky="ew")
        self.status_bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar, text="Ready", font=FONTS["body_sm"],
            text_color=t["fg_muted"]
        )
        self.status_label.pack(side="left", padx=12)

        # Live stats labels (right side, built right-to-left)
        self.health_dot = ctk.CTkLabel(
            self.status_bar, text="\u25CF", font=("Segoe UI", 10),
            text_color=t["success"]
        )
        self.health_dot.pack(side="right", padx=(0, 4))

        self.health_label = ctk.CTkLabel(
            self.status_bar, text="Health: --",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self.health_label.pack(side="right", padx=(0, 2))

        # SMS config indicator
        self._sms_status_lbl = ctk.CTkLabel(
            self.status_bar, text="SMS: --",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self._sms_status_lbl.pack(side="right", padx=(0, 8))

        # SMTP config indicator
        self._smtp_status_lbl = ctk.CTkLabel(
            self.status_bar, text="SMTP: --",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self._smtp_status_lbl.pack(side="right", padx=(0, 8))

        # Article count
        self._article_count_lbl = ctk.CTkLabel(
            self.status_bar, text="Articles: 0",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self._article_count_lbl.pack(side="right", padx=(0, 8))

        # Active sources count
        self._sources_count_lbl = ctk.CTkLabel(
            self.status_bar, text="Sources: 0",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self._sources_count_lbl.pack(side="right", padx=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(
            self.status_bar, width=150, height=8,
            progress_color=t["accent"]
        )
        self.progress_bar.pack(side="right", padx=12, pady=8)
        self.progress_bar.set(0)

        # Update health periodically
        self._update_health_indicator()
        self._update_status_bar_stats()

    def _update_health_indicator(self):
        try:
            from ..diagnostics import calculate_health_score
            score, _ = calculate_health_score()
            t = self._theme
            if score >= 80:
                color = t["success"]
                label = f"Health: {score}/100"
            elif score >= 50:
                color = t["warning"]
                label = f"Health: {score}/100"
            else:
                color = t["error"]
                label = f"Health: {score}/100"
            self.health_dot.configure(text_color=color)
            self.health_label.configure(text=label)
        except Exception:
            pass
        # Refresh every 5 minutes
        self.after(300000, self._update_health_indicator)

    def _update_status_bar_stats(self):
        """Update live stats in the status bar (article count, sources, SMTP/SMS config)."""
        try:
            stats = db.get_stats()
            t = self._theme
            self._article_count_lbl.configure(
                text=f"Articles: {stats['total_articles']}"
            )
            self._sources_count_lbl.configure(
                text=f"Sources: {stats['active_sources']}"
            )
            # SMTP config check
            from ..emailer import _get_email_config
            cfg = _get_email_config()
            smtp_ok = bool(cfg.get("username") and cfg.get("smtp_server"))
            self._smtp_status_lbl.configure(
                text=f"SMTP: {'✅' if smtp_ok else '⚠️'}",
                text_color=t["success"] if smtp_ok else t["warning"]
            )
            # SMS config check
            sms_ok = bool(cfg.get("sms_phone") and cfg.get("sms_carrier"))
            self._sms_status_lbl.configure(
                text=f"SMS: {'✅' if sms_ok else '⚠️'}",
                text_color=t["success"] if sms_ok else t["warning"]
            )
        except Exception:
            pass
        # Refresh every 60 seconds
        self.after(60000, self._update_status_bar_stats)

    def _create_views(self):
        t = self._theme

        self._views["dashboard"] = DashboardView(
            self.content, theme=t,
            on_article_click=self._on_article_click
        )
        self._views["feed"] = FeedView(self.content, theme=t)
        self._views["strategies"] = StrategyView(
            self.content, theme=t, show_toast=self._show_toast
        )
        self._views["email"] = EmailView(
            self.content, theme=t, show_toast=self._show_toast
        )
        self._views["export"] = ExportView(
            self.content, theme=t, show_toast=self._show_toast
        )
        self._views["sources"] = SourcesView(
            self.content, theme=t, show_toast=self._show_toast
        )
        self._views["health"] = HealthView(
            self.content, theme=t, show_toast=self._show_toast
        )
        self._views["settings"] = SettingsView(
            self.content, theme=t, config=self._config,
            on_theme_change=self._change_theme,
            show_toast=self._show_toast
        )

    def _show_view(self, name: str):
        # Hide all views
        for view in self._views.values():
            view.grid_forget()

        # Show selected
        view = self._views[name]
        view.grid(row=0, column=0, sticky="nsew")
        view.refresh()

        # Track session
        if self._session:
            self._session.log_view(name)

        # Update nav button styles
        t = self._theme
        for key, btn in self._nav_buttons.items():
            if key == name:
                btn.configure(fg_color=t["sidebar_active"], text_color=t["accent"])
            else:
                btn.configure(fg_color="transparent", text_color=t["fg"])

    def _on_article_click(self, article: dict):
        self._show_view("feed")
        self._views["feed"]._show_detail(article)

    def _fetch_all(self):
        if self._is_fetching:
            return
        self._is_fetching = True
        self._fetch_start_time = time.time()
        self.refresh_btn.configure(state="disabled", text="\u23F3 Fetching...")
        self.status_label.configure(text="Fetching feeds...")
        self.progress_bar.set(0)

        if self._session:
            self._session.log_action("fetch_start")

        def _run():
            try:
                result = fetch_all_sources(
                    max_articles=self._config.max_articles_per_source,
                    max_workers=self._config.max_concurrent_fetches,
                    timeout=self._config.fetch_timeout_seconds,
                    max_retries=self._config.max_retries,
                    retry_delay=self._config.retry_delay_seconds,
                    progress_callback=self._update_progress,
                )
                # Score articles
                if self._config.auto_score_articles:
                    score_all_unscored()

                # Auto-generate strategies
                if self._config.auto_generate_strategies:
                    from ..strategy import generate_strategies_from_trends
                    generate_strategies_from_trends()

                # Log performance
                duration_ms = (time.time() - self._fetch_start_time) * 1000
                if self._session:
                    self._session.log_full_fetch(
                        result.get("total_new", 0),
                        result.get("total_sources", 0),
                        result.get("errors", 0),
                        duration_ms
                    )

                self._safe_after(0, lambda: self._fetch_complete(result))
            except Exception as e:
                logger.error("Fetch error: %s", e)
                self._safe_after(0, lambda: self._fetch_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _update_progress(self, done: int, total: int, source_name: str):
        pct = done / max(total, 1)
        self._safe_after(0, lambda: self.progress_bar.set(pct))
        self._safe_after(0, lambda: self.status_label.configure(
            text=f"Fetching: {source_name} ({done}/{total})"
        ))

    def _fetch_complete(self, result: dict):
        self._is_fetching = False
        self.refresh_btn.configure(state="normal", text="\U0001F504 Refresh All Feeds")
        self.progress_bar.set(1.0)

        total = result.get("total_new", 0)
        errors = result.get("errors", 0)
        self.status_label.configure(
            text=f"Fetched {total} new articles from {result.get('total_sources', 0)} sources"
            + (f" ({errors} errors)" if errors else "")
        )
        now = datetime.now().strftime("%H:%M")
        self.last_refresh_label.configure(text=f"Last refresh: {now}")

        if self._config.notification_on_fetch:
            self._show_toast(f"Fetched {total} new articles!", "success")

        if errors > 0 and self._config.notification_on_error:
            self._show_toast(f"{errors} sources had errors - check Health tab", "warning")

        # Refresh current view
        for view in self._views.values():
            try:
                view.refresh()
            except Exception:
                pass

        # Highlight top standout article
        if total > 0:
            try:
                from ..analyzer import get_standouts
                standouts = get_standouts(limit=1, days=1)
                if standouts:
                    self._show_toast(
                        f"Top: {standouts[0]['title'][:60]}", "info"
                    )
            except Exception:
                pass

        # Update health
        self._update_health_indicator()

    def _fetch_error(self, error: str):
        self._is_fetching = False
        self.refresh_btn.configure(state="normal", text="\U0001F504 Refresh All Feeds")
        self.status_label.configure(text=f"Fetch error: {error}")
        if self._config.notification_on_error:
            self._show_toast(f"Fetch error: {error[:50]}", "error")

    def _get_github_source_id(self) -> int:
        """Get or create the GitHub source entry."""
        sources = db.get_sources()
        gh_source = next((s for s in sources if "GitHub" in s.get("name", "")), None)
        if gh_source:
            return gh_source["id"]
        return db.insert_source("GitHub Trending", "https://github.com/trending", "", "AI Tools")

    def _fetch_github(self):
        self.status_label.configure(text="Scraping GitHub trending...")
        if self._session:
            self._session.log_action("github_fetch")

        def _run():
            try:
                gh_id = self._get_github_source_id()
                repos = scrape_github_trending()
                for repo in repos:
                    db.insert_article(
                        title=f"[GitHub] {repo['name']}",
                        url=repo["url"],
                        source_id=gh_id,
                        summary=repo.get("description", ""),
                        category="AI Tools",
                        relevance_score=0.6,
                    )
                self._safe_after(0, lambda: self._github_complete(len(repos)))
            except Exception as e:
                logger.error("GitHub fetch error: %s", e)
                self._safe_after(0, lambda: self.status_label.configure(
                    text=f"GitHub error: {e}"))
                self._safe_after(0, lambda: self._show_toast(
                    f"GitHub fetch failed: {str(e)[:50]}", "error"))

        threading.Thread(target=_run, daemon=True).start()

    def _fetch_github_deep(self):
        """Deep GitHub scan - trending + topics + search."""
        self.status_label.configure(text="Deep scanning GitHub (this takes ~30s)...")
        if self._session:
            self._session.log_action("github_deep_fetch")

        def _run():
            try:
                gh_id = self._get_github_source_id()
                repos = scrape_github_deep()
                inserted = 0
                for repo in repos:
                    result = db.insert_article(
                        title=f"[GitHub] {repo['name']}",
                        url=repo["url"],
                        source_id=gh_id,
                        summary=repo.get("description", ""),
                        content_snippet=f"Stars: {repo.get('stars', '?')} | Language: {repo.get('language', '?')}",
                        category="AI Tools",
                        relevance_score=0.6,
                    )
                    if result:
                        inserted += 1

                if self._config.auto_score_articles:
                    score_all_unscored()

                self._safe_after(0, lambda: self._github_complete(inserted))
            except Exception as e:
                logger.error("GitHub deep fetch error: %s", e)
                self._safe_after(0, lambda: self.status_label.configure(
                    text=f"GitHub deep scan error: {e}"))
                self._safe_after(0, lambda: self._show_toast(
                    f"GitHub deep scan failed: {str(e)[:50]}", "error"))

        threading.Thread(target=_run, daemon=True).start()

    def _github_complete(self, count: int):
        self.status_label.configure(text=f"Found {count} AI repos on GitHub trending")
        if self._config.notification_on_fetch:
            self._show_toast(f"Found {count} trending AI repos!", "success")
        for view in self._views.values():
            try:
                view.refresh()
            except Exception:
                pass

    def _enrich_articles(self):
        """Fetch full article text for recent articles using auto_scraper."""
        if self._is_fetching:
            return
        self._is_fetching = True
        self.enrich_btn.configure(state="disabled", text="\u23F3 Enriching...")
        self.status_label.configure(text="Enriching articles with full text...")
        self.progress_bar.set(0)

        def _run():
            try:
                from ..full_article_fetcher import enrich_articles_batch
                articles = db.get_articles_without_full_text(limit=20)
                if not articles:
                    self._safe_after(0, lambda: self._enrich_complete(0, 0))
                    return

                def _progress(done, total, url):
                    pct = done / max(total, 1)
                    self._safe_after(0, lambda: self.progress_bar.set(pct))
                    self._safe_after(0, lambda: self.status_label.configure(
                        text=f"Enriching: {done}/{total}"
                    ))

                stats = enrich_articles_batch(articles, delay=1.0, progress_callback=_progress)
                self._safe_after(0, lambda: self._enrich_complete(
                    stats.get("enriched", 0), stats.get("failed", 0)
                ))
            except ImportError:
                self._safe_after(0, lambda: self._show_toast(
                    "auto_scraper not available - check installation", "error"))
                self._safe_after(0, lambda: self._enrich_complete(0, 0))
            except Exception as e:
                logger.error("Enrich error: %s", e)
                self._safe_after(0, lambda: self._show_toast(
                    f"Enrich failed: {str(e)[:50]}", "error"))
                self._safe_after(0, lambda: self._enrich_complete(0, 0))

        threading.Thread(target=_run, daemon=True).start()

    def _enrich_complete(self, enriched: int, failed: int):
        self._is_fetching = False
        self.enrich_btn.configure(state="normal", text="\U0001F4D6 Enrich Articles")
        self.progress_bar.set(1.0)
        msg = f"Enriched {enriched} articles"
        if failed:
            msg += f" ({failed} failed)"
        self.status_label.configure(text=msg)
        if enriched > 0:
            self._show_toast(msg, "success")
        for view in self._views.values():
            try:
                view.refresh()
            except Exception:
                pass

    def _show_toast(self, message: str, msg_type: str = "info"):
        ToastNotification(self, message, msg_type, duration=self._config.toast_duration_ms)

    def _change_theme(self, mode: str):
        self._config.theme = mode
        save_config(self._config)
        ctk.set_appearance_mode(mode)
        self._show_toast(f"Theme changed to {mode}. Restart for full effect.", "info")

    def _schedule_auto_refresh(self):
        interval_ms = self._config.auto_refresh_minutes * 60 * 1000
        self._auto_refresh_job = self.after(interval_ms, self._auto_refresh_tick)

    def _auto_refresh_tick(self):
        if self._config.auto_refresh_enabled:
            self._fetch_all()
            self._schedule_auto_refresh()

    def _bind_shortcuts(self):
        self.bind("<Control-r>", lambda e: self._fetch_all())
        self.bind("<Control-d>", lambda e: self._show_view("dashboard"))
        self.bind("<Control-e>", lambda e: self._show_view("export"))
        self.bind("<Control-f>", lambda e: self._focus_search())
        self.bind("<Control-h>", lambda e: self._show_view("health"))
        self.bind("<Control-m>", lambda e: self._show_view("email"))
        self.bind("<Control-t>", lambda e: self._send_sms_shortcut())
        self.bind("<Control-p>", lambda e: self._preview_selected())
        self.bind("<Control-Key-1>", lambda e: self._show_view("feed"))
        self.bind("<Control-Key-2>", lambda e: self._show_view("strategies"))
        self.bind("<Control-Key-3>", lambda e: self._show_view("sources"))
        self.bind("<Control-Key-4>", lambda e: self._show_view("settings"))
        self.bind("<Escape>", lambda e: self._escape_action())
        self.bind("<F5>", lambda e: self._refresh_current())

    def _focus_search(self):
        self._show_view("feed")
        self._views["feed"].search_bar.entry.focus_set()

    def _send_sms_shortcut(self):
        """Ctrl+T: switch to email view and trigger SMS send."""
        self._show_view("email")
        self._views["email"].send_sms_alert()

    def _preview_selected(self):
        """Ctrl+P: switch to feed view to see article preview."""
        self._show_view("feed")

    def _escape_action(self):
        """Escape: clear search or return to feed."""
        feed = self._views.get("feed")
        if feed and hasattr(feed, "clear_search"):
            feed.clear_search()

    def _refresh_current(self):
        for view in self._views.values():
            if view.winfo_ismapped():
                view.refresh()
                break

    def _safe_after(self, ms, callback):
        """Schedule a callback only if the window is still alive."""
        if not self._is_closing:
            try:
                self.after(ms, callback)
            except Exception:
                pass

    def _on_close(self):
        self._is_closing = True
        # Save window geometry
        geo = self.geometry()
        try:
            size = geo.split("+")[0]
            w, h = size.split("x")
            self._config.window_width = int(w)
            self._config.window_height = int(h)
        except Exception:
            pass
        save_config(self._config)

        # Save session
        if self._session:
            self._session.save()

        if self._auto_refresh_job:
            self.after_cancel(self._auto_refresh_job)

        self.destroy()
