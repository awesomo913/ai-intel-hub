"""Export center - bulk URL copy, article exports, and file exports."""

import customtkinter as ctk
from pathlib import Path
from .theme import FONTS, get_category_color, CATEGORY_COLORS, blend_color
from .. import database as db
from ..exporter import (
    articles_to_markdown, articles_to_csv, articles_to_json, articles_to_text,
    articles_urls_only, get_urls_by_category,
    copy_to_clipboard, export_articles, export_strategies, export_full_report
)
from ..platform_utils import get_export_dir, get_desktop_path


class ExportView(ctk.CTkScrollableFrame):
    """Export center with bulk URL copy, format selection, and destinations."""

    def __init__(self, master, theme: dict, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._theme = theme
        self._show_toast = show_toast

        # Header
        ctk.CTkLabel(
            self, text="Export Center", font=FONTS["heading_lg"],
            text_color=theme["fg"]
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            self, text="Bulk-copy URLs by category to feed your AIs, or export full reports.",
            font=FONTS["body_sm"], text_color=theme["fg_muted"],
            wraplength=800, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 20))

        # =============================================
        # === BULK URL COPY (the main new feature) ===
        # =============================================
        self._section("Bulk URL Copy", "One-click copy URL lists by category - paste straight into Claude, Gemini, ChatGPT")

        # URL format selector
        fmt_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        fmt_frame.pack(fill="x", padx=20, pady=(0, 8))

        fmt_inner = ctk.CTkFrame(fmt_frame, fg_color="transparent")
        fmt_inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(fmt_inner, text="URL Format:", font=FONTS["body"],
                     text_color=theme["fg"]).pack(side="left", padx=(0, 10))

        self._url_fmt_var = ctk.StringVar(value="ai_prompt")
        for val, label in [("ai_prompt", "AI Prompt"), ("plain", "URLs Only"),
                           ("markdown", "Markdown Links"), ("titled", "Title + URL"),
                           ("numbered", "Numbered"), ("csv", "CSV"), ("json", "JSON")]:
            ctk.CTkRadioButton(
                fmt_inner, text=label, variable=self._url_fmt_var, value=val,
                font=FONTS["body_sm"]
            ).pack(side="left", padx=6)

        # Filters row
        filter_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        filter_frame.pack(fill="x", padx=20, pady=(0, 8))

        filter_inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(filter_inner, text="Min Score:", font=FONTS["body"],
                     text_color=theme["fg"]).pack(side="left", padx=(0, 6))
        self._min_score_var = ctk.StringVar(value="0.0")
        ctk.CTkComboBox(
            filter_inner, values=["0.0", "0.3", "0.5", "0.7", "0.9"],
            variable=self._min_score_var, width=80, font=FONTS["body"]
        ).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(filter_inner, text="Max URLs:", font=FONTS["body"],
                     text_color=theme["fg"]).pack(side="left", padx=(0, 6))
        self._max_urls_var = ctk.StringVar(value="100")
        ctk.CTkComboBox(
            filter_inner, values=["25", "50", "100", "200", "500", "1000"],
            variable=self._max_urls_var, width=80, font=FONTS["body"]
        ).pack(side="left", padx=(0, 15))

        self._bm_only_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            filter_inner, text="Bookmarked only", variable=self._bm_only_var,
            font=FONTS["body_sm"], checkbox_height=18, checkbox_width=18
        ).pack(side="left")

        # === CATEGORY BUTTONS GRID ===
        cats_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        cats_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            cats_frame, text="Click a category to copy its URLs to clipboard:",
            font=FONTS["body_sm"], text_color=theme["fg_muted"]
        ).pack(anchor="w", padx=16, pady=(12, 8))

        # "Copy ALL URLs" button
        all_row = ctk.CTkFrame(cats_frame, fg_color="transparent")
        all_row.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkButton(
            all_row, text="Copy ALL URLs", font=("Segoe UI", 13, "bold"),
            height=42, corner_radius=10, fg_color=theme["accent"],
            hover_color=theme["accent_hover"],
            command=lambda: self._copy_category_urls("")
        ).pack(side="left", padx=(0, 10))

        self._all_count_label = ctk.CTkLabel(
            all_row, text="", font=FONTS["body_sm"], text_color=theme["fg_muted"]
        )
        self._all_count_label.pack(side="left")

        # Per-category buttons
        self._cat_buttons_frame = ctk.CTkFrame(cats_frame, fg_color="transparent")
        self._cat_buttons_frame.pack(fill="x", padx=16, pady=(0, 12))

        self._cat_count_labels = {}

        categories = list(CATEGORY_COLORS.keys())
        for i, cat in enumerate(categories):
            row_idx = i // 3
            col_idx = i % 3

            cell = ctk.CTkFrame(self._cat_buttons_frame, fg_color="transparent")
            cell.grid(row=row_idx, column=col_idx, padx=4, pady=3, sticky="ew")
            self._cat_buttons_frame.columnconfigure(col_idx, weight=1)

            color = get_category_color(cat)
            btn = ctk.CTkButton(
                cell, text=f"  {cat}", font=FONTS["button"],
                height=36, corner_radius=8, anchor="w",
                fg_color=blend_color(color, "#0f0f0f", 0.25),
                hover_color=blend_color(color, "#0f0f0f", 0.4),
                text_color=color,
                command=lambda c=cat: self._copy_category_urls(c)
            )
            btn.pack(side="left", fill="x", expand=True)

            count_lbl = ctk.CTkLabel(
                cell, text="", font=FONTS["body_sm"],
                text_color=theme["fg_muted"], width=40
            )
            count_lbl.pack(side="right", padx=4)
            self._cat_count_labels[cat] = count_lbl

        # Preview area
        ctk.CTkLabel(
            cats_frame, text="Preview (last copied):", font=FONTS["body_sm"],
            text_color=theme["fg_muted"]
        ).pack(anchor="w", padx=16, pady=(4, 2))

        self._preview_text = ctk.CTkTextbox(
            cats_frame, font=FONTS["mono_sm"], height=120,
            corner_radius=8, fg_color=theme["bg_input"],
            text_color=theme["fg_secondary"]
        )
        self._preview_text.pack(fill="x", padx=16, pady=(0, 12))

        # ============================
        # === QUICK CLIPBOARD COPY ===
        # ============================
        self._section("Quick Copy to Clipboard", "Copy formatted reports for pasting anywhere")

        clip_frame = ctk.CTkFrame(self, fg_color="transparent")
        clip_frame.pack(fill="x", padx=20, pady=(0, 15))

        clip_actions = [
            ("Copy All Articles (Markdown)", lambda: self._copy_articles("markdown")),
            ("Copy Bookmarked", self._copy_bookmarked),
            ("Copy Today's", self._copy_today),
            ("Copy Strategies", self._copy_strategies),
            ("Copy Full Report", self._copy_full_report),
        ]
        for text, cmd in clip_actions:
            ctk.CTkButton(
                clip_frame, text=text, font=FONTS["button"],
                corner_radius=8, height=38,
                command=cmd
            ).pack(side="left", padx=(0, 8), pady=4)

        # ====================
        # === FILE EXPORT ===
        # ====================
        self._section("Export to File", "Save as files to share or upload to Drive")

        file_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        file_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Format selector
        fmt_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        fmt_row.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(fmt_row, text="Format:", font=FONTS["body"],
                     text_color=theme["fg"]).pack(side="left", padx=(0, 10))

        self._format_var = ctk.StringVar(value="markdown")
        for fmt, label in [("markdown", "Markdown (.md)"), ("csv", "CSV (.csv)"),
                           ("json", "JSON (.json)"), ("text", "Plain Text (.txt)")]:
            ctk.CTkRadioButton(
                fmt_row, text=label, variable=self._format_var, value=fmt,
                font=FONTS["body_sm"]
            ).pack(side="left", padx=10)

        # Destination selector
        dest_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        dest_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(dest_row, text="Save to:", font=FONTS["body"],
                     text_color=theme["fg"]).pack(side="left", padx=(0, 10))

        self._dest_var = ctk.StringVar(value="exports")
        ctk.CTkRadioButton(
            dest_row, text="Exports folder", variable=self._dest_var,
            value="exports", font=FONTS["body_sm"]
        ).pack(side="left", padx=10)
        ctk.CTkRadioButton(
            dest_row, text="Desktop", variable=self._dest_var,
            value="desktop", font=FONTS["body_sm"]
        ).pack(side="left", padx=10)

        # What to export
        what_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        what_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(what_row, text="Export:", font=FONTS["body"],
                     text_color=theme["fg"]).pack(side="left", padx=(0, 10))

        self._what_var = ctk.StringVar(value="all")
        for val, label in [("all", "All articles"), ("bookmarked", "Bookmarked"),
                           ("today", "Today's"), ("strategies", "Strategies"),
                           ("full", "Full Report")]:
            ctk.CTkRadioButton(
                what_row, text=label, variable=self._what_var, value=val,
                font=FONTS["body_sm"]
            ).pack(side="left", padx=10)

        # Export button
        ctk.CTkButton(
            file_frame, text="Export to File", font=FONTS["heading_sm"],
            height=44, corner_radius=10,
            command=self._export_file
        ).pack(padx=16, pady=(0, 16))

        # ==========================
        # === DESTINATION GUIDE ===
        # ==========================
        self._section("Paste Destinations Guide", "Where to use your exported data")

        guide = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        guide.pack(fill="x", padx=20, pady=(0, 20))

        destinations = [
            ("\U0001F916 Claude", "Bulk copy URLs (AI Prompt format) \u2192 Paste into Claude for analysis"),
            ("\u2728 Gemini", "Bulk copy URLs \u2192 Paste into Gemini for competitive research"),
            ("\U0001F4AC ChatGPT", "Bulk copy URLs \u2192 Paste with browsing enabled for deep reading"),
            ("\U0001F4E7 Gmail", "Copy text report \u2192 Compose email \u2192 Paste"),
            ("\U0001F4C1 Google Drive", "Export as .md/.csv \u2192 Upload to Drive"),
            ("\U0001F4CA Sheets", "Export as CSV \u2192 Import into Google Sheets"),
            ("\U0001F4DD Notion", "Copy Markdown report \u2192 Paste into Notion page"),
        ]
        for icon_name, desc in destinations:
            row = ctk.CTkFrame(guide, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(
                row, text=icon_name, font=FONTS["body"],
                text_color=theme["accent"], width=120, anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=desc, font=FONTS["body_sm"],
                text_color=theme["fg_secondary"], anchor="w"
            ).pack(side="left", fill="x", expand=True)

        # Export folder path
        self.path_label = ctk.CTkLabel(
            self, text=f"Export folder: {get_export_dir()}",
            font=FONTS["body_sm"], text_color=theme["fg_muted"]
        )
        self.path_label.pack(anchor="w", padx=20, pady=(0, 20))

    def _section(self, title: str, subtitle: str):
        ctk.CTkLabel(
            self, text=title, font=FONTS["heading"],
            text_color=self._theme["fg"]
        ).pack(anchor="w", padx=20, pady=(15, 2))
        ctk.CTkLabel(
            self, text=subtitle, font=FONTS["body_sm"],
            text_color=self._theme["fg_muted"]
        ).pack(anchor="w", padx=20, pady=(0, 10))

    # --- Bulk URL Copy ---

    def _copy_category_urls(self, category: str):
        fmt = self._url_fmt_var.get()
        try:
            min_score = float(self._min_score_var.get())
        except ValueError:
            min_score = 0.0
        try:
            limit = int(self._max_urls_var.get())
        except ValueError:
            limit = 100
        bm_only = self._bm_only_var.get()

        articles = get_urls_by_category(
            category=category, min_score=min_score,
            limit=limit, bookmarked_only=bm_only
        )

        if not articles:
            if self._show_toast:
                cat_name = category or "any category"
                self._show_toast(f"No articles found for {cat_name}", "warning")
            return

        text = articles_urls_only(articles, fmt)

        if copy_to_clipboard(text):
            # Update preview
            self._preview_text.delete("0.0", "end")
            preview = text[:2000]
            if len(text) > 2000:
                preview += f"\n\n... ({len(articles)} total URLs)"
            self._preview_text.insert("0.0", preview)

            cat_name = category or "ALL categories"
            if self._show_toast:
                self._show_toast(
                    f"Copied {len(articles)} URLs from {cat_name} ({fmt})",
                    "success"
                )

    def _get_dest_dir(self) -> Path:
        if self._dest_var.get() == "desktop":
            return get_desktop_path()
        return get_export_dir()

    # --- Clipboard exports ---

    def _copy_articles(self, fmt: str = "markdown"):
        articles = db.get_articles(limit=200)
        text = articles_to_markdown(articles)
        if copy_to_clipboard(text) and self._show_toast:
            self._show_toast(f"Copied {len(articles)} articles to clipboard", "success")

    def _copy_bookmarked(self):
        articles = db.get_articles(limit=200, bookmarked_only=True)
        text = articles_to_markdown(articles, "Bookmarked Articles")
        if copy_to_clipboard(text) and self._show_toast:
            self._show_toast(f"Copied {len(articles)} bookmarked articles", "success")

    def _copy_today(self):
        from datetime import datetime
        articles = db.get_articles(limit=200)
        today = datetime.now().strftime("%Y-%m-%d")
        today_articles = [a for a in articles if a.get("fetched_at", "").startswith(today)]
        text = articles_to_markdown(today_articles, "Today's Articles")
        if copy_to_clipboard(text) and self._show_toast:
            self._show_toast(f"Copied {len(today_articles)} today's articles", "success")

    def _copy_strategies(self):
        from ..strategy import get_strategy_summary
        text = get_strategy_summary()
        if copy_to_clipboard(text) and self._show_toast:
            self._show_toast("Strategies copied to clipboard", "success")

    def _copy_full_report(self):
        articles = db.get_articles(limit=200)
        from ..strategy import get_strategy_summary
        text = articles_to_markdown(articles, "Full Intelligence Report")
        text += "\n\n---\n\n" + get_strategy_summary()
        if copy_to_clipboard(text) and self._show_toast:
            self._show_toast("Full report copied to clipboard", "success")

    # --- File export ---

    def _export_file(self):
        dest = self._get_dest_dir()
        what = self._what_var.get()
        fmt = self._format_var.get()

        if what == "strategies":
            path = export_strategies(dest)
        elif what == "full":
            path = export_full_report(dest)
        else:
            if what == "bookmarked":
                articles = db.get_articles(limit=500, bookmarked_only=True)
            elif what == "today":
                articles = db.get_articles(limit=500)
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                articles = [a for a in articles if a.get("fetched_at", "").startswith(today)]
            else:
                articles = db.get_articles(limit=500)
            path = export_articles(articles, fmt, dest)

        if self._show_toast:
            self._show_toast(f"Exported to {path.name}", "success")

    def refresh(self):
        """Update category counts."""
        try:
            total = db.get_article_count()
            self._all_count_label.configure(text=f"{total} articles")

            for cat, lbl in self._cat_count_labels.items():
                count = db.get_article_count(category=cat)
                lbl.configure(text=str(count) if count > 0 else "")
        except Exception:
            pass
