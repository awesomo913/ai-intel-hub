"""Source manager view - add, edit, delete, toggle RSS sources."""

import customtkinter as ctk
from .theme import FONTS, get_category_color
from .. import database as db


class SourcesView(ctk.CTkScrollableFrame):
    """Manage RSS feed sources."""

    def __init__(self, master, theme: dict, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._theme = theme
        self._show_toast = show_toast

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Sources", font=FONTS["heading_lg"],
            text_color=theme["fg"]
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Add Source", font=FONTS["button"],
            corner_radius=8, command=self._show_add_form
        ).pack(side="right")

        # Add form (hidden by default)
        self.add_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.add_frame_visible = False

        # Sources table
        self.table_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.table_frame.pack(fill="x", padx=20, pady=(0, 20))

    def _show_add_form(self):
        if self.add_frame_visible:
            self.add_frame.pack_forget()
            self.add_frame_visible = False
            return

        self.add_frame.pack(fill="x", padx=20, pady=(0, 15), before=self.table_frame)
        self.add_frame_visible = True

        for w in self.add_frame.winfo_children():
            w.destroy()

        t = self._theme
        ctk.CTkLabel(
            self.add_frame, text="Add New Source", font=FONTS["heading_sm"],
            text_color=t["fg"]
        ).pack(anchor="w", padx=16, pady=(12, 8))

        fields = ctk.CTkFrame(self.add_frame, fg_color="transparent")
        fields.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(fields, text="Name:", font=FONTS["body"], text_color=t["fg"]).grid(
            row=0, column=0, sticky="w", pady=4)
        self._name_entry = ctk.CTkEntry(fields, width=300, font=FONTS["body"])
        self._name_entry.grid(row=0, column=1, padx=8, pady=4)

        ctk.CTkLabel(fields, text="Website URL:", font=FONTS["body"], text_color=t["fg"]).grid(
            row=1, column=0, sticky="w", pady=4)
        self._url_entry = ctk.CTkEntry(fields, width=300, font=FONTS["body"])
        self._url_entry.grid(row=1, column=1, padx=8, pady=4)

        ctk.CTkLabel(fields, text="Feed URL:", font=FONTS["body"], text_color=t["fg"]).grid(
            row=2, column=0, sticky="w", pady=4)
        self._feed_entry = ctk.CTkEntry(fields, width=300, font=FONTS["body"])
        self._feed_entry.grid(row=2, column=1, padx=8, pady=4)

        ctk.CTkLabel(fields, text="Category:", font=FONTS["body"], text_color=t["fg"]).grid(
            row=3, column=0, sticky="w", pady=4)
        self._cat_entry = ctk.CTkComboBox(
            fields, values=["AI News", "AI Research", "AI Companies", "AI Tools",
                            "Local AI", "AI Agents", "Vibe Coding", "Breakthroughs",
                            "AI Business", "Open Source AI"],
            width=300, font=FONTS["body"]
        )
        self._cat_entry.grid(row=3, column=1, padx=8, pady=4)

        btn_row = ctk.CTkFrame(self.add_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            btn_row, text="Add Source", font=FONTS["button"],
            corner_radius=8, command=self._add_source
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Cancel", font=FONTS["button"],
            corner_radius=8, fg_color=t["bg_secondary"],
            command=self._show_add_form
        ).pack(side="left")

    def _add_source(self):
        name = self._name_entry.get().strip()
        url = self._url_entry.get().strip()
        feed = self._feed_entry.get().strip()
        cat = self._cat_entry.get().strip()

        if not name or not feed:
            if self._show_toast:
                self._show_toast("Name and Feed URL are required", "warning")
            return

        db.insert_source(name, url or feed, feed, cat)
        self._show_add_form()  # hide form
        self.refresh()
        if self._show_toast:
            self._show_toast(f"Added source: {name}", "success")

    def refresh(self):
        for w in self.table_frame.winfo_children():
            w.destroy()

        sources = db.get_sources()
        t = self._theme

        if not sources:
            ctk.CTkLabel(
                self.table_frame, text="No sources configured",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(pady=40)
            return

        # Header row
        hdr = ctk.CTkFrame(self.table_frame, fg_color=t["bg_secondary"], corner_radius=8)
        hdr.pack(fill="x", pady=(0, 4))
        hdr_inner = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_inner.pack(fill="x", padx=12, pady=8)

        for text, width in [("Status", 60), ("Name", 200), ("Category", 100),
                            ("Articles", 70), ("Errors", 60), ("Last Fetched", 130), ("Actions", 120)]:
            ctk.CTkLabel(
                hdr_inner, text=text, font=FONTS["tag"],
                text_color=t["fg_muted"], width=width, anchor="w"
            ).pack(side="left", padx=2)

        for source in sources:
            self._create_source_row(source)

    def _create_source_row(self, source: dict):
        t = self._theme
        row = ctk.CTkFrame(self.table_frame, fg_color=t["bg_card"], corner_radius=8)
        row.pack(fill="x", pady=2)
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=6)

        # Status
        active = source.get("is_active", 1)
        status_color = t["success"] if active else t["fg_muted"]
        status_text = "\u25CF" if active else "\u25CB"
        ctk.CTkLabel(
            inner, text=status_text, font=("Segoe UI", 14),
            text_color=status_color, width=60, anchor="w"
        ).pack(side="left", padx=2)

        # Name
        ctk.CTkLabel(
            inner, text=source["name"][:25], font=FONTS["body"],
            text_color=t["fg"], width=200, anchor="w"
        ).pack(side="left", padx=2)

        # Category
        cat = source.get("category", "")
        cat_color = get_category_color(cat)
        ctk.CTkLabel(
            inner, text=cat, font=FONTS["body_sm"],
            text_color=cat_color, width=100, anchor="w"
        ).pack(side="left", padx=2)

        # Fetch count
        ctk.CTkLabel(
            inner, text=str(source.get("fetch_count", 0)),
            font=FONTS["body_sm"], text_color=t["fg_secondary"],
            width=70, anchor="w"
        ).pack(side="left", padx=2)

        # Error count
        errors = source.get("error_count", 0)
        err_color = t["error"] if errors > 0 else t["fg_muted"]
        ctk.CTkLabel(
            inner, text=str(errors), font=FONTS["body_sm"],
            text_color=err_color, width=60, anchor="w"
        ).pack(side="left", padx=2)

        # Last fetched
        last = source.get("last_fetched", "Never") or "Never"
        ctk.CTkLabel(
            inner, text=last[:16], font=FONTS["body_sm"],
            text_color=t["fg_muted"], width=130, anchor="w"
        ).pack(side="left", padx=2)

        # Actions
        actions = ctk.CTkFrame(inner, fg_color="transparent", width=120)
        actions.pack(side="left", padx=2)

        toggle_text = "Disable" if active else "Enable"
        ctk.CTkButton(
            actions, text=toggle_text, width=55, height=24,
            font=FONTS["body_sm"], corner_radius=6,
            fg_color=t["warning"] if active else t["success"],
            command=lambda sid=source["id"]: self._toggle(sid)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions, text="Delete", width=50, height=24,
            font=FONTS["body_sm"], corner_radius=6,
            fg_color=t["error"],
            command=lambda sid=source["id"]: self._delete(sid)
        ).pack(side="left", padx=2)

    def _toggle(self, source_id: int):
        db.toggle_source(source_id)
        self.refresh()

    def _delete(self, source_id: int):
        db.delete_source(source_id)
        self.refresh()
        if self._show_toast:
            self._show_toast("Source deleted", "info")
