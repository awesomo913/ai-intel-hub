"""Feed view - browse, search, filter, and read articles.
Refactored to Builder Pattern."""

import webbrowser
import customtkinter as ctk
from .theme import FONTS, get_category_color, CATEGORY_COLORS, blend_color
from .widgets import SearchBar, CategoryFilter
from .. import database as db


class FeedView(ctk.CTkFrame):
    """Article feed with search, filters, and detail panel."""

    def __init__(self, master, theme: dict, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._init_state(theme)
        self._build_ui()

    def _init_state(self, theme: dict):
        self._theme = theme
        self._current_search = ""
        self._current_category = ""
        self._current_page = 0
        self._page_size = 30
        self._selected_article = None
        self._bookmark_var = ctk.BooleanVar(value=False)
        self._unread_var = ctk.BooleanVar(value=False)

    def _build_ui(self):
        self._build_header()
        self._build_search_filters()
        self._build_content_area()
        self._build_pagination()

    def _build_header(self):
        t = self._theme
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="Articles", font=FONTS["heading_lg"],
                     text_color=t["fg"]).pack(side="left")
        self.count_label = ctk.CTkLabel(header, text="", font=FONTS["body"],
                                         text_color=t["fg_muted"])
        self.count_label.pack(side="right")

    def _build_search_filters(self):
        t = self._theme
        self.search_bar = SearchBar(
            self, placeholder="Search articles...",
            on_search=self._on_search, fg_color=t["bg_secondary"]
        )
        self.search_bar.pack(fill="x", padx=20, pady=(0, 8))

        self.cat_filter = CategoryFilter(
            self, categories=list(CATEGORY_COLORS.keys()),
            on_select=self._on_category
        )
        self.cat_filter.pack(fill="x", padx=20, pady=(0, 8))

        qf = ctk.CTkFrame(self, fg_color="transparent")
        qf.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkCheckBox(
            qf, text="Bookmarked only", variable=self._bookmark_var,
            font=FONTS["body_sm"], command=self.refresh,
            checkbox_height=18, checkbox_width=18
        ).pack(side="left", padx=(0, 15))
        ctk.CTkCheckBox(
            qf, text="Unread only", variable=self._unread_var,
            font=FONTS["body_sm"], command=self.refresh,
            checkbox_height=18, checkbox_width=18
        ).pack(side="left")

    def _build_content_area(self):
        t = self._theme
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        self.list_frame = ctk.CTkScrollableFrame(
            content, fg_color=t["bg_secondary"], corner_radius=12
        )
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.detail_frame = ctk.CTkScrollableFrame(
            content, fg_color=t["bg_card"], corner_radius=12
        )
        self.detail_frame.grid(row=0, column=1, sticky="nsew")
        self._show_detail_placeholder()

    def _build_pagination(self):
        t = self._theme
        pager = ctk.CTkFrame(self, fg_color="transparent")
        pager.pack(fill="x", padx=20, pady=(0, 10))
        self.prev_btn = ctk.CTkButton(
            pager, text="\u25C0 Previous", font=FONTS["button"],
            width=100, command=self._prev_page
        )
        self.prev_btn.pack(side="left")
        self.page_label = ctk.CTkLabel(
            pager, text="Page 1", font=FONTS["body"], text_color=t["fg_muted"]
        )
        self.page_label.pack(side="left", padx=20)
        self.next_btn = ctk.CTkButton(
            pager, text="Next \u25B6", font=FONTS["button"],
            width=100, command=self._next_page
        )
        self.next_btn.pack(side="left")

    def _on_search(self, query: str):
        self._current_search = query
        self._current_page = 0
        self.refresh()

    def _on_category(self, category: str):
        self._current_category = category
        self._current_page = 0
        self.refresh()

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self.refresh()

    def _next_page(self):
        self._current_page += 1
        self.refresh()

    def refresh(self):
        """Reload article list."""
        for w in self.list_frame.winfo_children():
            w.destroy()

        articles = db.get_articles(
            limit=self._page_size,
            offset=self._current_page * self._page_size,
            category=self._current_category,
            search=self._current_search,
            bookmarked_only=self._bookmark_var.get(),
            unread_only=self._unread_var.get(),
        )

        total = db.get_article_count(
            category=self._current_category,
            search=self._current_search,
            bookmarked_only=self._bookmark_var.get(),
            unread_only=self._unread_var.get(),
        )
        self.count_label.configure(text=f"{total} articles")
        self.page_label.configure(
            text=f"Page {self._current_page + 1} of {max(1, (total - 1) // self._page_size + 1)}"
        )

        if not articles:
            ctk.CTkLabel(
                self.list_frame, text="No articles found",
                font=FONTS["body"], text_color=self._theme["fg_muted"]
            ).pack(pady=40)
            return

        for article in articles:
            self._create_article_row(article)

    def _create_article_row(self, article: dict):
        row = ctk.CTkFrame(
            self.list_frame, fg_color=self._theme["bg_card"],
            corner_radius=8
        )
        row.pack(fill="x", pady=3, padx=4)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # Category badge
        cat = article.get("category", "")
        cat_color = get_category_color(cat)
        ctk.CTkLabel(
            inner, text=cat[:15], font=FONTS["tag"],
            text_color=cat_color, fg_color=blend_color(cat_color, "#0f0f0f", 0.15),
            corner_radius=6, padx=6, pady=1, width=90
        ).pack(side="left")

        # Title
        read_color = self._theme["fg_muted"] if article.get("is_read") else self._theme["fg"]
        title = article["title"][:90]
        lbl = ctk.CTkLabel(
            inner, text=title, font=FONTS["body"],
            text_color=read_color, anchor="w"
        )
        lbl.pack(side="left", fill="x", expand=True, padx=8)

        # Score
        score = article.get("relevance_score", 0)
        s_color = "#00c853" if score >= 0.7 else ("#ffa726" if score >= 0.4 else self._theme["fg_muted"])
        ctk.CTkLabel(
            inner, text=f"{score:.0%}", font=FONTS["tag"],
            text_color=s_color, width=40
        ).pack(side="right", padx=4)

        # Bookmark indicator
        if article.get("is_bookmarked"):
            ctk.CTkLabel(
                inner, text="\u2605", font=("Segoe UI", 12),
                text_color="#ffa726", width=20
            ).pack(side="right")

        # Date
        date = article.get("published_at", "")[:10]
        ctk.CTkLabel(
            inner, text=date, font=FONTS["body_sm"],
            text_color=self._theme["fg_muted"], width=80
        ).pack(side="right")

        # Click to show detail
        for widget in [row, lbl]:
            widget.bind("<Button-1>", lambda e, a=article: self._show_detail(a))
            widget.configure(cursor="hand2")

    def _show_detail_placeholder(self):
        for w in self.detail_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.detail_frame, text="Select an article to view details",
            font=FONTS["body"], text_color=self._theme["fg_muted"]
        ).pack(pady=60)

    def _show_detail(self, article: dict):
        self._selected_article = article
        db.mark_read(article["id"])

        for w in self.detail_frame.winfo_children():
            w.destroy()

        t = self._theme

        # Category
        cat = article.get("category", "")
        cat_color = get_category_color(cat)
        ctk.CTkLabel(
            self.detail_frame, text=cat, font=FONTS["tag"],
            text_color=cat_color, fg_color=blend_color(cat_color, "#0f0f0f", 0.15),
            corner_radius=6, padx=8, pady=2
        ).pack(anchor="w", padx=16, pady=(16, 8))

        # Title
        ctk.CTkLabel(
            self.detail_frame, text=article["title"],
            font=FONTS["heading"], text_color=t["fg"],
            wraplength=400, justify="left", anchor="w"
        ).pack(fill="x", padx=16, pady=(0, 8))

        # Meta
        meta = f"Source: {article.get('source_name', 'N/A')} | {article.get('published_at', '')[:16]}"
        meta += f" | Score: {article.get('relevance_score', 0):.0%}"
        ctk.CTkLabel(
            self.detail_frame, text=meta, font=FONTS["body_sm"],
            text_color=t["fg_muted"], wraplength=400, justify="left"
        ).pack(fill="x", padx=16, pady=(0, 12))

        # Summary
        summary = article.get("summary", "")
        if summary:
            ctk.CTkLabel(
                self.detail_frame, text=summary,
                font=FONTS["body"], text_color=t["fg_secondary"],
                wraplength=400, justify="left", anchor="nw"
            ).pack(fill="x", padx=16, pady=(0, 12))

        # Content snippet
        snippet = article.get("content_snippet", "")
        if snippet and snippet != summary:
            ctk.CTkLabel(
                self.detail_frame, text="Content Preview",
                font=FONTS["heading_sm"], text_color=t["fg"]
            ).pack(anchor="w", padx=16, pady=(0, 4))
            ctk.CTkLabel(
                self.detail_frame, text=snippet[:500],
                font=FONTS["body_sm"], text_color=t["fg_secondary"],
                wraplength=400, justify="left", anchor="nw"
            ).pack(fill="x", padx=16, pady=(0, 12))

        # Full article text (if enriched)
        full_text = article.get("full_text", "")
        if full_text:
            ctk.CTkLabel(
                self.detail_frame, text="Full Article Text",
                font=FONTS["heading_sm"], text_color=t["fg"]
            ).pack(anchor="w", padx=16, pady=(0, 4))
            ctk.CTkLabel(
                self.detail_frame, text=full_text[:2000],
                font=FONTS["body_sm"], text_color=t["fg_secondary"],
                wraplength=400, justify="left", anchor="nw"
            ).pack(fill="x", padx=16, pady=(0, 12))

        # Action buttons
        actions = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            actions, text="Open in Browser \u2197",
            font=FONTS["button"], corner_radius=8,
            command=lambda: webbrowser.open(article["url"])
        ).pack(side="left", padx=(0, 8))

        bm_text = "Unbookmark" if article.get("is_bookmarked") else "Bookmark \u2605"
        ctk.CTkButton(
            actions, text=bm_text, font=FONTS["button"],
            corner_radius=8, fg_color=t["warning"],
            command=lambda: self._toggle_bookmark(article)
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions, text="Copy Link", font=FONTS["button"],
            corner_radius=8, fg_color=t["bg_secondary"],
            command=lambda: self._copy_link(article)
        ).pack(side="left", padx=(0, 8))

        if not article.get("has_full_text"):
            ctk.CTkButton(
                actions, text="Fetch Full Text", font=FONTS["button"],
                corner_radius=8, fg_color="#69db7c", text_color="#1a1a2e",
                command=lambda: self._fetch_full_text(article)
            ).pack(side="left")

        # Feedback row
        feedback_row = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        feedback_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            feedback_row, text="Feedback:", font=FONTS["body_sm"],
            text_color=t["fg_muted"]
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            feedback_row, text="👍 Like", width=80, height=30,
            font=FONTS["button"], corner_radius=8, fg_color=t["success"],
            command=lambda: self._give_feedback(article, 1)
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            feedback_row, text="👎 Dislike", width=80, height=30,
            font=FONTS["button"], corner_radius=8, fg_color=t["error"],
            command=lambda: self._give_feedback(article, -1)
        ).pack(side="left")

    def _give_feedback(self, article: dict, feedback: int):
        """Store +1/-1 feedback for an article to train the scoring model."""
        try:
            db.save_article_feedback(article["id"], feedback)
            label = "👍 Liked!" if feedback > 0 else "👎 Noted!"
            # Refresh detail panel to reflect feedback was recorded
            self._show_detail(article)
        except Exception:
            pass

    def _toggle_bookmark(self, article: dict):
        db.toggle_bookmark(article["id"])
        article["is_bookmarked"] = not article.get("is_bookmarked")
        self._show_detail(article)
        self.refresh()

    def _fetch_full_text(self, article: dict):
        """Fetch full article text for a single article."""
        import threading

        def _run():
            try:
                from ..full_article_fetcher import fetch_full_article
                result = fetch_full_article(article["url"])
                if result.get("text") and not result.get("error"):
                    db.update_full_text(article["id"], result["text"])
                    article["full_text"] = result["text"]
                    article["has_full_text"] = 1
                    self.after(0, lambda: self._show_detail(article))
            except ImportError:
                pass
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    def _copy_link(self, article: dict):
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(article["url"])
            root.update()
            root.destroy()
        except Exception:
            pass
