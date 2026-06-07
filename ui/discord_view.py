"""Discord webhook view - configure and send AI intelligence alerts to Discord channels."""

import threading
import customtkinter as ctk
from .theme import FONTS
from ..discord_webhook import (
    get_webhook_url, save_webhook_url, delete_webhook_url,
    send_groundbreaker_alert, send_standouts_digest, send_daily_digest,
    send_discord_message, build_groundbreaker_payload,
)
from .. import database as db


class DiscordView(ctk.CTkScrollableFrame):
    """Configure Discord webhook and send AI intelligence alerts."""

    def __init__(self, master, theme: dict, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._init_state(theme, show_toast)
        self._build_ui()

    def _init_state(self, theme: dict, show_toast):
        self._theme = theme
        self._show_toast = show_toast
        self._sending = False

    def _build_ui(self):
        self._build_header()
        self._build_webhook_config()
        self._build_quick_send()
        self._build_history()

    # --- Builders ---

    def _build_header(self):
        t = self._theme
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Discord Alerts", font=FONTS["heading_lg"],
            text_color=t["fg"]
        ).pack(side="left")

        ctk.CTkLabel(
            self, text="Send AI intelligence alerts directly to a Discord channel via webhook.",
            font=FONTS["body_sm"], text_color=t["fg_muted"],
            wraplength=800, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _build_webhook_config(self):
        t = self._theme
        self._section("Webhook Configuration", "Paste your Discord channel webhook URL below")

        frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        frame.pack(fill="x", padx=20, pady=(0, 15))

        url_row = ctk.CTkFrame(frame, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            url_row, text="Webhook URL:", font=FONTS["body"],
            text_color=t["fg"], width=120
        ).pack(side="left")

        self._url_entry = ctk.CTkEntry(
            url_row, font=FONTS["body"], height=34, corner_radius=8,
            placeholder_text="https://discord.com/api/webhooks/...",
            show="*"
        )
        self._url_entry.pack(side="left", fill="x", expand=True)

        # Load existing URL mask
        existing = get_webhook_url()
        if existing:
            self._url_entry.insert(0, existing)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(6, 14))

        ctk.CTkButton(
            btn_row, text="Save Webhook URL", font=FONTS["button"],
            height=36, corner_radius=8, fg_color=t["success"],
            command=self._save_webhook_url
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Test Connection", font=FONTS["button"],
            height=36, corner_radius=8, fg_color=t["info"],
            command=self._test_connection
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Clear", font=FONTS["button"],
            height=36, corner_radius=8, fg_color=t["error"],
            command=self._clear_webhook_url
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text="URL is stored securely in your OS keychain — never written to disk.",
            font=FONTS["body_sm"], text_color=t["success"]
        ).pack(anchor="w", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            frame,
            text="To create a webhook: Discord Channel → Edit Channel → Integrations → Webhooks → New Webhook",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        ).pack(anchor="w", padx=16, pady=(0, 12))

    def _build_quick_send(self):
        t = self._theme
        self._section("Send Alerts", "Choose what to post to your Discord channel")

        frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        frame.pack(fill="x", padx=20, pady=(0, 15))

        actions = [
            (
                "🔥 Groundbreaker Alert",
                "Post the #1 must-read article with full details",
                self._send_groundbreaker,
                t["accent"],
            ),
            (
                "📊 Top 5 Standouts",
                "Post the top 5 highest-scoring articles as rich embeds",
                self._send_standouts,
                t["success"],
            ),
            (
                "📰 Daily Digest",
                "Post a compact digest of today's high-value articles",
                self._send_digest,
                t["info"],
            ),
        ]

        for text, desc, cmd, color in actions:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)

            ctk.CTkButton(
                row, text=text, font=FONTS["button"],
                width=230, height=38, corner_radius=8,
                fg_color=color, anchor="w", command=cmd
            ).pack(side="left", padx=(0, 12))

            ctk.CTkLabel(
                row, text=desc, font=FONTS["body_sm"],
                text_color=t["fg_secondary"]
            ).pack(side="left")

        self._send_status = ctk.CTkLabel(
            frame, text="", font=FONTS["body_sm"],
            text_color=t["fg_muted"]
        )
        self._send_status.pack(anchor="w", padx=16, pady=(4, 12))

    def _build_history(self):
        t = self._theme
        self._section("Send History", "Last 10 Discord sends")

        self._history_frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        self._history_frame.pack(fill="x", padx=20, pady=(0, 20))

        self._populate_history()

    def _populate_history(self):
        # Clear old rows
        for widget in self._history_frame.winfo_children():
            widget.destroy()

        t = self._theme
        history = db.get_discord_history(limit=10)

        if not history:
            ctk.CTkLabel(
                self._history_frame, text="No sends yet.",
                font=FONTS["body_sm"], text_color=t["fg_muted"]
            ).pack(padx=16, pady=12)
            return

        # Header row
        hdr = ctk.CTkFrame(self._history_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        for col, w in [("Time", 140), ("Type", 120), ("Articles", 70), ("Status", 80)]:
            ctk.CTkLabel(
                hdr, text=col, font=FONTS["body_sm"],
                text_color=t["fg_muted"], width=w, anchor="w"
            ).pack(side="left", padx=(0, 8))

        for row_data in history:
            row = ctk.CTkFrame(self._history_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)

            sent_at = str(row_data.get("sent_at", ""))[:16]
            msg_type = row_data.get("message_type", "")
            count = str(row_data.get("article_count", 0))
            ok = row_data.get("success", 0)
            status_text = "✅ OK" if ok else "❌ Failed"
            status_color = t["success"] if ok else t["error"]

            for val, w, color in [
                (sent_at, 140, t["fg_secondary"]),
                (msg_type, 120, t["fg"]),
                (count, 70, t["fg_secondary"]),
                (status_text, 80, status_color),
            ]:
                ctk.CTkLabel(
                    row, text=val, font=FONTS["body_sm"],
                    text_color=color, width=w, anchor="w"
                ).pack(side="left", padx=(0, 8))

            err = row_data.get("error_msg", "")
            if err:
                ctk.CTkLabel(
                    row, text=err[:80], font=FONTS["body_sm"],
                    text_color=t["error"]
                ).pack(side="left")

        ctk.CTkFrame(self._history_frame, fg_color="transparent", height=8).pack()

    # --- Helpers ---

    def _section(self, title: str, subtitle: str = ""):
        ctk.CTkLabel(
            self, text=title, font=FONTS["heading"],
            text_color=self._theme["fg"]
        ).pack(anchor="w", padx=20, pady=(15, 2))
        if subtitle:
            ctk.CTkLabel(
                self, text=subtitle, font=FONTS["body_sm"],
                text_color=self._theme["fg_muted"]
            ).pack(anchor="w", padx=20, pady=(0, 8))

    def _set_status(self, text: str, color_key: str = "fg_muted"):
        color = self._theme.get(color_key, self._theme["fg_muted"])
        self._send_status.configure(text=text, text_color=color)

    def _run_send(self, fn, label: str):
        """Run a send function in a background thread."""
        if self._sending:
            return
        self._sending = True
        self._set_status(f"Sending {label}…", "fg_muted")

        def _worker():
            ok, msg = fn()
            self.after(0, lambda: self._on_send_done(ok, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_send_done(self, ok: bool, msg: str):
        self._sending = False
        color_key = "success" if ok else "error"
        self._set_status(msg, color_key)
        if self._show_toast:
            self._show_toast(msg, "success" if ok else "error")
        self._populate_history()

    # --- Actions ---

    def _save_webhook_url(self):
        url = self._url_entry.get().strip()
        if not url:
            if self._show_toast:
                self._show_toast("Enter a webhook URL first", "warning")
            return
        save_webhook_url(url)
        if self._show_toast:
            self._show_toast("Webhook URL saved to OS keychain", "success")

    def _test_connection(self):
        url = self._url_entry.get().strip() or get_webhook_url()
        if not url:
            if self._show_toast:
                self._show_toast("Enter a webhook URL first", "warning")
            return

        self._set_status("Testing connection…", "fg_muted")

        def _worker():
            payload = {"content": "✅ AI Intel Hub — webhook connection test successful!"}
            ok, msg = send_discord_message(payload, url)
            self.after(0, lambda: self._on_send_done(ok, msg))

        self._sending = True
        threading.Thread(target=_worker, daemon=True).start()

    def _clear_webhook_url(self):
        delete_webhook_url()
        self._url_entry.delete(0, "end")
        if self._show_toast:
            self._show_toast("Webhook URL removed from keychain", "success")

    def _send_groundbreaker(self):
        self._run_send(send_groundbreaker_alert, "groundbreaker alert")

    def _send_standouts(self):
        self._run_send(send_standouts_digest, "top 5 standouts")

    def _send_digest(self):
        self._run_send(send_daily_digest, "daily digest")

    def refresh(self):
        self._populate_history()
