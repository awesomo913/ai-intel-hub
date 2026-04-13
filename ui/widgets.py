"""Reusable styled widgets - cards, tags, search bar, stat cards."""

import customtkinter as ctk
from .theme import FONTS, get_category_color, blend_color


class StatCard(ctk.CTkFrame):
    """Dashboard stat card with number and label."""

    def __init__(self, master, label: str, value: str, color: str = "#6c63ff", **kwargs):
        super().__init__(master, corner_radius=12, **kwargs)
        self._color = color

        self.value_label = ctk.CTkLabel(
            self, text=value, font=FONTS["stat_number"],
            text_color=color
        )
        self.value_label.pack(pady=(15, 2), padx=15)

        self.text_label = ctk.CTkLabel(
            self, text=label, font=FONTS["stat_label"],
            text_color="gray"
        )
        self.text_label.pack(pady=(0, 15), padx=15)

    def update_value(self, value: str):
        self.value_label.configure(text=value)


class ArticleCard(ctk.CTkFrame):
    """Compact article display card."""

    def __init__(self, master, article: dict, on_click=None,
                 on_bookmark=None, theme=None, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)
        self.article = article
        self._on_click = on_click
        self._theme = theme or {}

        fg = self._theme.get("fg", "#e0e0e0")
        fg_sec = self._theme.get("fg_secondary", "#a0a0b0")
        fg_muted = self._theme.get("fg_muted", "#666680")

        # Top row: category tag + source
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 4))

        cat = article.get("category", "")
        cat_color = get_category_color(cat)
        ctk.CTkLabel(
            top, text=cat, font=FONTS["tag"],
            text_color=cat_color, fg_color=blend_color(cat_color, "#0f0f0f", 0.15),
            corner_radius=6, padx=8, pady=2
        ).pack(side="left")

        src = article.get("source_name", "")
        if src:
            ctk.CTkLabel(
                top, text=src, font=FONTS["body_sm"],
                text_color=fg_muted
            ).pack(side="right")

        # Title
        title_text = article.get("title", "Untitled")
        read_color = fg_muted if article.get("is_read") else fg
        title = ctk.CTkLabel(
            self, text=title_text, font=FONTS["heading_sm"],
            text_color=read_color, anchor="w", wraplength=500,
            justify="left"
        )
        title.pack(fill="x", padx=12, pady=(0, 4))

        # Summary (truncated)
        summary = article.get("summary", "")[:200]
        if summary:
            ctk.CTkLabel(
                self, text=summary, font=FONTS["body_sm"],
                text_color=fg_sec, anchor="w", wraplength=500,
                justify="left"
            ).pack(fill="x", padx=12, pady=(0, 4))

        # Bottom row: date + score + bookmark
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(0, 10))

        date = article.get("published_at", "")[:10]
        ctk.CTkLabel(
            bottom, text=date, font=FONTS["body_sm"],
            text_color=fg_muted
        ).pack(side="left")

        score = article.get("relevance_score", 0)
        score_color = "#00c853" if score >= 0.7 else ("#ffa726" if score >= 0.4 else fg_muted)
        ctk.CTkLabel(
            bottom, text=f"{score:.0%}", font=FONTS["tag"],
            text_color=score_color
        ).pack(side="left", padx=(10, 0))

        bm_text = "\u2605" if article.get("is_bookmarked") else "\u2606"
        bm_btn = ctk.CTkButton(
            bottom, text=bm_text, width=30, height=24,
            font=("Segoe UI", 14), fg_color="transparent",
            hover_color=self._theme.get("bg_card_hover", "#1a2745"),
            text_color="#ffa726" if article.get("is_bookmarked") else fg_muted,
            command=lambda: on_bookmark(article["id"]) if on_bookmark else None
        )
        bm_btn.pack(side="right")

        # Click binding
        if on_click:
            for widget in [self, title]:
                widget.bind("<Button-1>", lambda e: on_click(article))
                widget.configure(cursor="hand2")


class SearchBar(ctk.CTkFrame):
    """Search bar with icon and clear button."""

    def __init__(self, master, placeholder: str = "Search...",
                 on_search=None, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)
        self._on_search = on_search

        self.entry = ctk.CTkEntry(
            self, placeholder_text=placeholder,
            font=FONTS["body"], height=36, corner_radius=8,
            border_width=1
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=6)
        self.entry.bind("<Return>", self._do_search)

        self.search_btn = ctk.CTkButton(
            self, text="\U0001F50D", width=36, height=36,
            font=("Segoe UI", 14), corner_radius=8,
            command=self._do_search
        )
        self.search_btn.pack(side="left", padx=(0, 4), pady=6)

        self.clear_btn = ctk.CTkButton(
            self, text="\u2715", width=36, height=36,
            font=("Segoe UI", 14), corner_radius=8,
            fg_color="transparent", hover_color="#333",
            command=self._clear
        )
        self.clear_btn.pack(side="left", padx=(0, 8), pady=6)

    def _do_search(self, event=None):
        query = self.entry.get().strip()
        if self._on_search:
            self._on_search(query)

    def _clear(self):
        self.entry.delete(0, "end")
        if self._on_search:
            self._on_search("")

    def get_query(self) -> str:
        return self.entry.get().strip()


class CategoryFilter(ctk.CTkFrame):
    """Horizontal category filter chips."""

    def __init__(self, master, categories: list[str],
                 on_select=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select = on_select
        self._buttons = {}
        self._selected = "All"

        self._add_chip("All", "#6c63ff")
        for cat in categories:
            color = get_category_color(cat)
            self._add_chip(cat, color)

        self._update_styles()

    def _add_chip(self, name: str, color: str):
        btn = ctk.CTkButton(
            self, text=name, font=FONTS["tag"],
            height=28, corner_radius=14,
            fg_color=blend_color(color, "#0f0f0f", 0.2),
            hover_color=blend_color(color, "#0f0f0f", 0.35),
            text_color=color, border_width=1,
            border_color=blend_color(color, "#0f0f0f", 0.25),
            command=lambda n=name: self._select(n)
        )
        btn.pack(side="left", padx=3, pady=4)
        self._buttons[name] = (btn, color)

    def _select(self, name: str):
        self._selected = name
        self._update_styles()
        if self._on_select:
            self._on_select(name if name != "All" else "")

    def _update_styles(self):
        for name, (btn, color) in self._buttons.items():
            if name == self._selected:
                btn.configure(fg_color=color, text_color="#fff")
            else:
                btn.configure(fg_color=blend_color(color, "#0f0f0f", 0.2), text_color=color)


class ToastNotification(ctk.CTkFrame):
    """Non-blocking toast notification."""

    def __init__(self, master, message: str, msg_type: str = "info",
                 duration: int = 3000, **kwargs):
        colors = {
            "info": "#42a5f5", "success": "#00c853",
            "warning": "#ffa726", "error": "#ef5350"
        }
        color = colors.get(msg_type, colors["info"])
        super().__init__(master, fg_color=color, corner_radius=10, **kwargs)

        ctk.CTkLabel(
            self, text=message, font=FONTS["body"],
            text_color="#fff"
        ).pack(padx=16, pady=10)

        self.place(relx=0.5, rely=0.95, anchor="s")
        self.after(duration, self.destroy)
