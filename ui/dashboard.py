"""Dashboard view - stats, TOP 5 STANDOUTS, GROUNDBREAKER, trends, hot topics."""

import webbrowser
import customtkinter as ctk
from .theme import FONTS, get_category_color, CATEGORY_COLORS, blend_color
from .widgets import StatCard
from .. import database as db
from ..analyzer import (get_trending_keywords, get_category_trends,
                        get_hot_topics, get_standouts, get_groundbreaker)


class DashboardView(ctk.CTkScrollableFrame):
    """Main dashboard with standouts, groundbreaker, stats, and trends.
    Refactored to Builder Pattern."""

    def __init__(self, master, theme: dict, on_article_click=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._init_state(theme, on_article_click)
        self._build_ui()

    def _init_state(self, theme: dict, on_article_click):
        self._theme = theme
        self._on_article_click = on_article_click
        self._stat_cards = {}

    def _build_ui(self):
        self._build_header()
        self._build_stat_cards()
        self._build_groundbreaker_section()
        self._build_standouts_section()
        self._build_trends_section()
        self._build_hot_topics_section()
        self._build_keywords_section()
        self._build_recent_section()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="Dashboard", font=FONTS["heading_lg"],
                     text_color=self._theme["fg"]).pack(side="left")

    def _build_stat_cards(self):
        t = self._theme
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=20, pady=10)

        stat_defs = [
            ("total", "Total Articles", "0", t["accent"]),
            ("unread", "Unread", "0", t["info"]),
            ("today", "Today", "0", t["success"]),
            ("bookmarked", "Bookmarked", "0", t["warning"]),
            ("sources", "Active Sources", "0", "#cc5de8"),
            ("strategies", "Strategies", "0", "#20c997"),
        ]
        for i, (key, label, val, color) in enumerate(stat_defs):
            card = StatCard(self.stats_frame, label=label, value=val, color=color,
                            fg_color=t["bg_card"])
            card.grid(row=0, column=i, padx=6, pady=6, sticky="nsew")
            self._stat_cards[key] = card
            self.stats_frame.columnconfigure(i, weight=1)

    def _build_groundbreaker_section(self):
        t = self._theme
        ctk.CTkLabel(self, text="\U0001F4A5 GROUNDBREAKER - Check This Now",
                     font=("Segoe UI", 18, "bold"), text_color="#ff922b", anchor="w"
                     ).pack(fill="x", padx=20, pady=(20, 8))
        self.groundbreaker_frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12,
                                                 border_width=2, border_color="#ff922b")
        self.groundbreaker_frame.pack(fill="x", padx=20, pady=(0, 15))

    def _build_standouts_section(self):
        ctk.CTkLabel(self, text="\U0001F31F Top 5 Standouts - Must Read",
                     font=("Segoe UI", 18, "bold"), text_color="#fcc419", anchor="w"
                     ).pack(fill="x", padx=20, pady=(10, 8))
        self.standouts_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.standouts_frame.pack(fill="x", padx=20, pady=(0, 15))

    def _build_trends_section(self):
        t = self._theme
        ctk.CTkLabel(self, text="Category Trends (7 days)", font=FONTS["heading"],
                     text_color=t["fg"], anchor="w").pack(fill="x", padx=20, pady=(15, 8))
        self.trends_frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        self.trends_frame.pack(fill="x", padx=20, pady=(0, 10))

    def _build_hot_topics_section(self):
        t = self._theme
        ctk.CTkLabel(self, text="Hot Topics", font=FONTS["heading"],
                     text_color=t["fg"], anchor="w").pack(fill="x", padx=20, pady=(10, 8))
        self.hot_frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        self.hot_frame.pack(fill="x", padx=20, pady=(0, 10))

    def _build_keywords_section(self):
        t = self._theme
        ctk.CTkLabel(self, text="Trending Keywords", font=FONTS["heading"],
                     text_color=t["fg"], anchor="w").pack(fill="x", padx=20, pady=(10, 8))
        self.keywords_frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        self.keywords_frame.pack(fill="x", padx=20, pady=(0, 10))

    def _build_recent_section(self):
        t = self._theme
        ctk.CTkLabel(self, text="Recent Articles", font=FONTS["heading"],
                     text_color=t["fg"], anchor="w").pack(fill="x", padx=20, pady=(10, 8))
        self.recent_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.recent_frame.pack(fill="x", padx=20, pady=(0, 20))

    def refresh(self):
        stats = db.get_stats()
        self._stat_cards["total"].update_value(str(stats["total_articles"]))
        self._stat_cards["unread"].update_value(str(stats["unread"]))
        self._stat_cards["today"].update_value(str(stats["today_articles"]))
        self._stat_cards["bookmarked"].update_value(str(stats["bookmarked"]))
        self._stat_cards["sources"].update_value(str(stats["active_sources"]))
        self._stat_cards["strategies"].update_value(str(stats["strategies"]))

        self._refresh_groundbreaker()
        self._refresh_standouts()
        self._refresh_trends()
        self._refresh_hot_topics()
        self._refresh_keywords()
        self._refresh_recent()

    # --- GROUNDBREAKER ---

    def _refresh_groundbreaker(self):
        for w in self.groundbreaker_frame.winfo_children():
            w.destroy()
        t = self._theme

        gb = get_groundbreaker(days=7)
        if not gb:
            ctk.CTkLabel(
                self.groundbreaker_frame, text="No groundbreaker detected yet - fetch articles first",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=20, pady=20)
            return

        inner = ctk.CTkFrame(self.groundbreaker_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        # Top row: category + signals
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        cat = gb.get("category", "")
        cat_color = get_category_color(cat)
        ctk.CTkLabel(
            top, text=cat, font=FONTS["tag"],
            text_color=cat_color, fg_color=blend_color(cat_color, "#0f0f0f", 0.15),
            corner_radius=6, padx=8, pady=2
        ).pack(side="left", padx=(0, 8))

        score = gb.get("groundbreaker_score", gb.get("relevance_score", 0))
        signals = gb.get("signal_hits", 0)
        ctk.CTkLabel(
            top, text=f"Score: {score:.0%} | {signals} breakthrough signals",
            font=FONTS["body_sm"], text_color="#ff922b"
        ).pack(side="left")

        if gb.get("source_name"):
            ctk.CTkLabel(
                top, text=gb["source_name"], font=FONTS["body_sm"],
                text_color=t["fg_muted"]
            ).pack(side="right")

        # Title
        title_lbl = ctk.CTkLabel(
            inner, text=gb["title"], font=("Segoe UI", 16, "bold"),
            text_color="#ffa726", anchor="w", wraplength=700, justify="left"
        )
        title_lbl.pack(fill="x", pady=(8, 4))

        # Summary
        summary = gb.get("summary", "")
        if summary:
            ctk.CTkLabel(
                inner, text=summary[:400], font=FONTS["body"],
                text_color=t["fg_secondary"], anchor="w", wraplength=700, justify="left"
            ).pack(fill="x", pady=(0, 8))

        # Action buttons
        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack(fill="x")

        ctk.CTkButton(
            btns, text="Open in Browser \u2197", font=FONTS["button"],
            corner_radius=8, fg_color="#ff922b", hover_color="#ff7b00",
            command=lambda: webbrowser.open(gb["url"])
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btns, text="Bookmark \u2605", font=FONTS["button"],
            corner_radius=8, fg_color=t["bg_secondary"],
            command=lambda: self._bookmark(gb)
        ).pack(side="left")

        # Clickable
        for w in [title_lbl, inner]:
            if self._on_article_click:
                w.bind("<Button-1>", lambda e, a=gb: self._on_article_click(a))
                w.configure(cursor="hand2")

    # --- TOP 5 STANDOUTS ---

    def _refresh_standouts(self):
        for w in self.standouts_frame.winfo_children():
            w.destroy()
        t = self._theme

        standouts = get_standouts(limit=5, days=7)
        if not standouts:
            ctk.CTkLabel(
                self.standouts_frame, text="No standouts yet - fetch articles first",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=20, pady=20)
            return

        for i, article in enumerate(standouts):
            card = ctk.CTkFrame(
                self.standouts_frame, fg_color=t["bg_card"], corner_radius=10,
                border_width=1, border_color=blend_color("#fcc419", "#0f0f0f", 0.3)
            )
            card.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            # Rank number
            rank_colors = ["#fcc419", "#fcc419", "#fcc419", "#adb5bd", "#adb5bd"]
            ctk.CTkLabel(
                inner, text=f"#{i+1}", font=("Segoe UI", 20, "bold"),
                text_color=rank_colors[i], width=40
            ).pack(side="left", padx=(0, 10))

            # Content
            content = ctk.CTkFrame(inner, fg_color="transparent")
            content.pack(side="left", fill="x", expand=True)

            # Category + score row
            meta = ctk.CTkFrame(content, fg_color="transparent")
            meta.pack(fill="x")

            cat = article.get("category", "")
            cat_color = get_category_color(cat)
            ctk.CTkLabel(
                meta, text=cat, font=FONTS["tag"],
                text_color=cat_color, fg_color=blend_color(cat_color, "#0f0f0f", 0.15),
                corner_radius=6, padx=6, pady=1
            ).pack(side="left", padx=(0, 8))

            s_score = article.get("standout_score", article.get("relevance_score", 0))
            ctk.CTkLabel(
                meta, text=f"Score: {s_score:.0%}", font=FONTS["tag"],
                text_color="#fcc419"
            ).pack(side="left", padx=(0, 8))

            if article.get("source_name"):
                ctk.CTkLabel(
                    meta, text=article["source_name"], font=FONTS["body_sm"],
                    text_color=t["fg_muted"]
                ).pack(side="right")

            # Title
            title_lbl = ctk.CTkLabel(
                content, text=article["title"][:120], font=FONTS["heading_sm"],
                text_color=t["fg"], anchor="w", wraplength=600, justify="left"
            )
            title_lbl.pack(fill="x", pady=(4, 2))

            # Summary preview
            summary = article.get("summary", "")[:180]
            if summary:
                ctk.CTkLabel(
                    content, text=summary, font=FONTS["body_sm"],
                    text_color=t["fg_secondary"], anchor="w", wraplength=600, justify="left"
                ).pack(fill="x")

            # Open button
            ctk.CTkButton(
                inner, text="\u2197", width=32, height=32,
                font=("Segoe UI", 14), corner_radius=8,
                fg_color=t["bg_secondary"], hover_color=t["accent"],
                command=lambda url=article["url"]: webbrowser.open(url)
            ).pack(side="right")

            # Clickable
            if self._on_article_click:
                for w in [card, title_lbl]:
                    w.bind("<Button-1>", lambda e, a=article: self._on_article_click(a))
                    w.configure(cursor="hand2")

    # --- EXISTING SECTIONS (unchanged logic) ---

    def _refresh_trends(self):
        for w in self.trends_frame.winfo_children():
            w.destroy()
        t = self._theme

        trends = get_category_trends(days=7)
        if not trends:
            ctk.CTkLabel(
                self.trends_frame, text="No data yet - fetch articles first",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=20, pady=20)
            return

        max_val = max(trends.values()) if trends else 1
        for cat, count in sorted(trends.items(), key=lambda x: x[1], reverse=True):
            row = ctk.CTkFrame(self.trends_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)

            color = get_category_color(cat)
            ctk.CTkLabel(
                row, text=cat, font=FONTS["body_sm"],
                text_color=t["fg"], width=140, anchor="w"
            ).pack(side="left")

            bar_frame = ctk.CTkFrame(row, fg_color=t["bg"], height=18, corner_radius=9)
            bar_frame.pack(side="left", fill="x", expand=True, padx=8)
            bar_frame.pack_propagate(False)

            pct = count / max_val
            bar = ctk.CTkFrame(bar_frame, fg_color=color, corner_radius=9)
            bar.place(relwidth=max(pct, 0.02), relheight=1.0)

            ctk.CTkLabel(
                row, text=str(count), font=FONTS["body_sm"],
                text_color=color, width=40
            ).pack(side="right")

    def _refresh_hot_topics(self):
        for w in self.hot_frame.winfo_children():
            w.destroy()
        t = self._theme

        topics = get_hot_topics(days=7, min_mentions=1)
        if not topics:
            ctk.CTkLabel(
                self.hot_frame, text="No hot topics yet",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=20, pady=20)
            return

        for topic in topics[:8]:
            row = ctk.CTkFrame(self.hot_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)

            cat_color = get_category_color(topic.get("category", ""))
            ctk.CTkLabel(
                row, text=topic.get("category", ""), font=FONTS["tag"],
                text_color=cat_color, fg_color=blend_color(cat_color, "#0f0f0f", 0.15),
                corner_radius=6, padx=6, pady=1
            ).pack(side="left", padx=(0, 8))

            title = topic["title"][:70]
            ctk.CTkLabel(
                row, text=title, font=FONTS["body_sm"],
                text_color=t["fg"], anchor="w"
            ).pack(side="left", fill="x", expand=True)

            mentions = topic.get("mentions", 0)
            sources = topic.get("sources", 0)
            ctk.CTkLabel(
                row, text=f"{mentions} mentions / {sources} sources",
                font=FONTS["body_sm"], text_color=t["fg_muted"]
            ).pack(side="right")

    def _refresh_keywords(self):
        for w in self.keywords_frame.winfo_children():
            w.destroy()

        keywords = get_trending_keywords(days=7, top_n=20)
        if not keywords:
            ctk.CTkLabel(
                self.keywords_frame, text="No keywords yet",
                font=FONTS["body"], text_color=self._theme["fg_muted"]
            ).pack(padx=20, pady=20)
            return

        flow = ctk.CTkFrame(self.keywords_frame, fg_color="transparent")
        flow.pack(fill="x", padx=16, pady=12)

        for kw, count in keywords:
            size = min(14, max(10, 8 + count // 3))
            ctk.CTkLabel(
                flow, text=f"{kw} ({count})",
                font=("Segoe UI", size),
                text_color=self._theme["accent"],
                fg_color=self._theme["accent_light"],
                corner_radius=8, padx=8, pady=4
            ).pack(side="left", padx=3, pady=3)

    def _refresh_recent(self):
        for w in self.recent_frame.winfo_children():
            w.destroy()
        t = self._theme

        articles = db.get_articles(limit=10)
        if not articles:
            ctk.CTkLabel(
                self.recent_frame, text="No articles yet - click Refresh to fetch",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=20, pady=20)
            return

        for article in articles:
            row = ctk.CTkFrame(self.recent_frame, fg_color=t["bg_card"], corner_radius=8)
            row.pack(fill="x", pady=3)

            cat = article.get("category", "")
            cat_color = get_category_color(cat)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            ctk.CTkLabel(
                inner, text=cat, font=FONTS["tag"],
                text_color=cat_color, width=100, anchor="w"
            ).pack(side="left")

            title = article["title"][:80]
            lbl = ctk.CTkLabel(
                inner, text=title, font=FONTS["body"],
                text_color=t["fg"], anchor="w"
            )
            lbl.pack(side="left", fill="x", expand=True, padx=8)

            date = article.get("published_at", "")[:10]
            ctk.CTkLabel(
                inner, text=date, font=FONTS["body_sm"],
                text_color=t["fg_muted"]
            ).pack(side="right")

            if self._on_article_click:
                row.bind("<Button-1>", lambda e, a=article: self._on_article_click(a))
                lbl.bind("<Button-1>", lambda e, a=article: self._on_article_click(a))
                row.configure(cursor="hand2")
                lbl.configure(cursor="hand2")

    def _bookmark(self, article: dict):
        db.toggle_bookmark(article["id"])
