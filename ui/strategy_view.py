"""Strategy view - browse, rate, and export monetization strategies."""

import customtkinter as ctk
from .theme import FONTS, get_category_color
from .. import database as db
from ..strategy import generate_strategies_from_trends, get_strategy_summary
from ..exporter import copy_to_clipboard, export_strategies


class StrategyView(ctk.CTkScrollableFrame):
    """Browse and manage monetization strategies."""

    def __init__(self, master, theme: dict, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._theme = theme
        self._show_toast = show_toast

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Monetization Strategies", font=FONTS["heading_lg"],
            text_color=theme["fg"]
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Generate from Trends", font=FONTS["button"],
            corner_radius=8, command=self._generate
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            header, text="Copy All", font=FONTS["button"],
            corner_radius=8, fg_color=theme["info"],
            command=self._copy_all
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            header, text="Export to File", font=FONTS["button"],
            corner_radius=8, fg_color=theme["success"],
            command=self._export
        ).pack(side="right")

        # Info text
        ctk.CTkLabel(
            self, text="Strategies are generated based on trending AI topics. "
                       "Rate them to track which ideas resonate with you.",
            font=FONTS["body_sm"], text_color=theme["fg_muted"],
            wraplength=800, justify="left"
        ).pack(fill="x", padx=20, pady=(0, 15))

        # Strategy cards container
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="x", padx=20, pady=(0, 20))

    def refresh(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()

        strategies = db.get_strategies()

        if not strategies:
            ctk.CTkLabel(
                self.cards_frame,
                text="No strategies yet. Fetch articles first, then click 'Generate from Trends'.",
                font=FONTS["body"], text_color=self._theme["fg_muted"]
            ).pack(pady=40)
            return

        # Group by category
        by_cat = {}
        for s in strategies:
            cat = s.get("category", "General")
            by_cat.setdefault(cat, []).append(s)

        for cat, strats in sorted(by_cat.items()):
            cat_color = get_category_color(cat)

            # Category header
            cat_header = ctk.CTkFrame(self.cards_frame, fg_color="transparent")
            cat_header.pack(fill="x", pady=(15, 8))
            ctk.CTkLabel(
                cat_header, text=cat, font=FONTS["heading"],
                text_color=cat_color
            ).pack(side="left")
            ctk.CTkLabel(
                cat_header, text=f"{len(strats)} strategies",
                font=FONTS["body_sm"], text_color=self._theme["fg_muted"]
            ).pack(side="right")

            for s in strats:
                self._create_strategy_card(s, cat_color)

    def _create_strategy_card(self, strategy: dict, color: str):
        card = ctk.CTkFrame(
            self.cards_frame, fg_color=self._theme["bg_card"],
            corner_radius=12
        )
        card.pack(fill="x", pady=4)

        # Title row
        title_row = ctk.CTkFrame(card, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            title_row, text=strategy["title"],
            font=FONTS["heading_sm"], text_color=self._theme["fg"]
        ).pack(side="left", fill="x", expand=True)

        # Star rating
        rating = strategy.get("rating", 0)
        for i in range(5):
            star = "\u2605" if i < rating else "\u2606"
            star_color = "#ffa726" if i < rating else self._theme["fg_muted"]
            btn = ctk.CTkButton(
                title_row, text=star, width=24, height=24,
                font=("Segoe UI", 14), fg_color="transparent",
                hover_color=self._theme["bg_card_hover"],
                text_color=star_color,
                command=lambda sid=strategy["id"], r=i+1: self._rate(sid, r)
            )
            btn.pack(side="right")

        # Description
        ctk.CTkLabel(
            card, text=strategy["description"],
            font=FONTS["body"], text_color=self._theme["fg_secondary"],
            wraplength=700, justify="left", anchor="nw"
        ).pack(fill="x", padx=16, pady=(0, 8))

        # Trend basis
        basis = strategy.get("trend_basis", "")
        if basis:
            ctk.CTkLabel(
                card, text=basis, font=FONTS["body_sm"],
                text_color=self._theme["fg_muted"], wraplength=700,
                justify="left", anchor="w"
            ).pack(fill="x", padx=16, pady=(0, 12))

    def _rate(self, strategy_id: int, rating: int):
        db.rate_strategy(strategy_id, rating)
        self.refresh()

    def _generate(self):
        generated = generate_strategies_from_trends()
        count = len(generated)
        self.refresh()
        if self._show_toast:
            self._show_toast(
                f"Generated {count} new strategies" if count else "No new strategies to generate",
                "success" if count else "info"
            )

    def _copy_all(self):
        text = get_strategy_summary()
        if copy_to_clipboard(text):
            if self._show_toast:
                self._show_toast("Strategies copied to clipboard", "success")

    def _export(self):
        path = export_strategies()
        if self._show_toast:
            self._show_toast(f"Exported to {path.name}", "success")
