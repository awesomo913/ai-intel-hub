"""Email view - compose and send intelligence reports via email."""

import customtkinter as ctk
from .theme import FONTS
from ..emailer import (
    build_daily_digest, build_standouts_email, build_strategies_email,
    build_custom_email, send_via_mailto, send_via_gmail_web, send_via_smtp,
    save_email_config, _get_email_config
)
from ..exporter import copy_to_clipboard


class EmailView(ctk.CTkScrollableFrame):
    """Compose and send AI intelligence emails."""

    def __init__(self, master, theme: dict, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._theme = theme
        self._show_toast = show_toast
        self._current_subject = ""
        self._current_body = ""

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Email Reports", font=FONTS["heading_lg"],
            text_color=theme["fg"]
        ).pack(side="left")

        ctk.CTkLabel(
            self, text="Send AI intelligence reports to yourself or your team via email.",
            font=FONTS["body_sm"], text_color=theme["fg_muted"],
            wraplength=800, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # === QUICK SEND TEMPLATES ===
        self._section("Quick Email Templates", "One-click compose with pre-built reports")

        templates_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        templates_frame.pack(fill="x", padx=20, pady=(0, 15))

        templates = [
            ("\U0001F4A5 Groundbreaker + Top 5", "The #1 must-see article + top 5 standouts",
             self._compose_standouts),
            ("\U0001F4CA Daily Digest", "Full summary with stats, categories, and top articles",
             self._compose_digest),
            ("\U0001F4A1 Strategies Report", "All monetization strategies based on current trends",
             self._compose_strategies),
            ("\U0001F4CB Custom Selection", "Pick your own articles to include",
             self._compose_custom),
        ]

        for text, desc, cmd in templates:
            row = ctk.CTkFrame(templates_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)

            ctk.CTkButton(
                row, text=text, font=FONTS["button"],
                width=250, height=36, corner_radius=8, anchor="w",
                command=cmd
            ).pack(side="left", padx=(0, 12))

            ctk.CTkLabel(
                row, text=desc, font=FONTS["body_sm"],
                text_color=theme["fg_secondary"]
            ).pack(side="left")

        # === COMPOSE AREA ===
        self._section("Compose", "Review and customize before sending")

        compose_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        compose_frame.pack(fill="x", padx=20, pady=(0, 15))

        # To field
        to_row = ctk.CTkFrame(compose_frame, fg_color="transparent")
        to_row.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(to_row, text="To:", font=FONTS["body"], text_color=theme["fg"],
                     width=60).pack(side="left")
        email_cfg = _get_email_config()
        self._to_entry = ctk.CTkEntry(
            to_row, font=FONTS["body"], height=34, corner_radius=8,
            placeholder_text="recipient@email.com"
        )
        self._to_entry.pack(side="left", fill="x", expand=True)
        default_to = email_cfg.get("default_to", "")
        if default_to:
            self._to_entry.insert(0, default_to)

        # Subject
        subj_row = ctk.CTkFrame(compose_frame, fg_color="transparent")
        subj_row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(subj_row, text="Subject:", font=FONTS["body"], text_color=theme["fg"],
                     width=60).pack(side="left")
        self._subject_entry = ctk.CTkEntry(
            subj_row, font=FONTS["body"], height=34, corner_radius=8
        )
        self._subject_entry.pack(side="left", fill="x", expand=True)

        # Body preview
        ctk.CTkLabel(
            compose_frame, text="Body Preview:", font=FONTS["body"],
            text_color=theme["fg"]
        ).pack(anchor="w", padx=16, pady=(6, 2))

        self._body_text = ctk.CTkTextbox(
            compose_frame, font=FONTS["mono_sm"], height=300,
            corner_radius=8, fg_color=theme["bg_input"],
            text_color=theme["fg"]
        )
        self._body_text.pack(fill="x", padx=16, pady=(0, 12))

        # Send buttons
        send_row = ctk.CTkFrame(compose_frame, fg_color="transparent")
        send_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            send_row, text="\U0001F4E7 Open in Gmail", font=FONTS["button"],
            height=38, corner_radius=8, fg_color="#ea4335",
            command=self._send_gmail
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            send_row, text="\U0001F4EC Open in Email App", font=FONTS["button"],
            height=38, corner_radius=8, fg_color=theme["info"],
            command=self._send_mailto
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            send_row, text="\U0001F4E4 Send via SMTP", font=FONTS["button"],
            height=38, corner_radius=8, fg_color=theme["success"],
            command=self._send_smtp
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            send_row, text="\U0001F4CB Copy Body", font=FONTS["button"],
            height=38, corner_radius=8, fg_color=theme["bg_secondary"],
            command=self._copy_body
        ).pack(side="left")

        # === SMTP SETTINGS ===
        self._section("SMTP Settings (Optional)", "For direct sending without opening a browser")

        smtp_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        smtp_frame.pack(fill="x", padx=20, pady=(0, 15))

        smtp_fields = ctk.CTkFrame(smtp_frame, fg_color="transparent")
        smtp_fields.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(smtp_fields, text="SMTP Server:", font=FONTS["body"],
                     text_color=theme["fg"]).grid(row=0, column=0, sticky="w", pady=4)
        self._smtp_server = ctk.CTkEntry(smtp_fields, width=300, font=FONTS["body"],
                                          placeholder_text="smtp.gmail.com")
        self._smtp_server.grid(row=0, column=1, padx=8, pady=4)

        ctk.CTkLabel(smtp_fields, text="Port:", font=FONTS["body"],
                     text_color=theme["fg"]).grid(row=1, column=0, sticky="w", pady=4)
        self._smtp_port = ctk.CTkEntry(smtp_fields, width=300, font=FONTS["body"],
                                        placeholder_text="587")
        self._smtp_port.grid(row=1, column=1, padx=8, pady=4)

        ctk.CTkLabel(smtp_fields, text="Username:", font=FONTS["body"],
                     text_color=theme["fg"]).grid(row=2, column=0, sticky="w", pady=4)
        self._smtp_user = ctk.CTkEntry(smtp_fields, width=300, font=FONTS["body"],
                                        placeholder_text="your@gmail.com")
        self._smtp_user.grid(row=2, column=1, padx=8, pady=4)

        ctk.CTkLabel(smtp_fields, text="App Password:", font=FONTS["body"],
                     text_color=theme["fg"]).grid(row=3, column=0, sticky="w", pady=4)
        self._smtp_pass = ctk.CTkEntry(smtp_fields, width=300, font=FONTS["body"],
                                        placeholder_text="xxxx xxxx xxxx xxxx", show="*")
        self._smtp_pass.grid(row=3, column=1, padx=8, pady=4)

        ctk.CTkLabel(smtp_fields, text="Default To:", font=FONTS["body"],
                     text_color=theme["fg"]).grid(row=4, column=0, sticky="w", pady=4)
        self._smtp_default_to = ctk.CTkEntry(smtp_fields, width=300, font=FONTS["body"],
                                              placeholder_text="default recipient")
        self._smtp_default_to.grid(row=4, column=1, padx=8, pady=4)

        # Load existing SMTP config
        cfg = _get_email_config()
        if cfg.get("smtp_server"):
            self._smtp_server.insert(0, cfg["smtp_server"])
        if cfg.get("smtp_port"):
            self._smtp_port.insert(0, str(cfg["smtp_port"]))
        if cfg.get("username"):
            self._smtp_user.insert(0, cfg["username"])
        if cfg.get("default_to"):
            self._smtp_default_to.insert(0, cfg["default_to"])

        ctk.CTkButton(
            smtp_frame, text="Save SMTP Settings", font=FONTS["button"],
            corner_radius=8, command=self._save_smtp
        ).pack(padx=16, pady=(0, 12))

        ctk.CTkLabel(
            smtp_frame, text="For Gmail: use an App Password (Settings > Security > 2FA > App Passwords)",
            font=FONTS["body_sm"], text_color=theme["fg_muted"]
        ).pack(padx=16, pady=(0, 12))

    def _section(self, title: str, subtitle: str = ""):
        ctk.CTkLabel(self, text=title, font=FONTS["heading"],
                     text_color=self._theme["fg"]).pack(anchor="w", padx=20, pady=(15, 2))
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=FONTS["body_sm"],
                         text_color=self._theme["fg_muted"]).pack(anchor="w", padx=20, pady=(0, 8))

    def _set_compose(self, subject: str, body: str):
        self._current_subject = subject
        self._current_body = body
        self._subject_entry.delete(0, "end")
        self._subject_entry.insert(0, subject)
        self._body_text.delete("0.0", "end")
        self._body_text.insert("0.0", body)

    def _compose_standouts(self):
        subject, body = build_standouts_email()
        self._set_compose(subject, body)
        if self._show_toast:
            self._show_toast("Standouts email composed", "success")

    def _compose_digest(self):
        subject, body = build_daily_digest()
        self._set_compose(subject, body)
        if self._show_toast:
            self._show_toast("Daily digest composed", "success")

    def _compose_strategies(self):
        subject, body = build_strategies_email()
        self._set_compose(subject, body)
        if self._show_toast:
            self._show_toast("Strategies email composed", "success")

    def _compose_custom(self):
        subject, body = build_custom_email()
        self._set_compose(subject, body)
        if self._show_toast:
            self._show_toast("Custom email composed with top articles", "success")

    def _get_to(self) -> str:
        return self._to_entry.get().strip()

    def _get_subject(self) -> str:
        return self._subject_entry.get().strip()

    def _get_body(self) -> str:
        return self._body_text.get("0.0", "end").strip()

    def _send_gmail(self):
        to = self._get_to()
        if not to:
            if self._show_toast:
                self._show_toast("Enter a recipient email address", "warning")
            return
        send_via_gmail_web(to, self._get_subject(), self._get_body())
        if self._show_toast:
            self._show_toast("Opened Gmail compose", "success")

    def _send_mailto(self):
        to = self._get_to()
        if not to:
            if self._show_toast:
                self._show_toast("Enter a recipient email address", "warning")
            return
        send_via_mailto(to, self._get_subject(), self._get_body())
        if self._show_toast:
            self._show_toast("Opened email app", "success")

    def _send_smtp(self):
        to = self._get_to()
        if not to:
            if self._show_toast:
                self._show_toast("Enter a recipient email address", "warning")
            return
        success, msg = send_via_smtp(to, self._get_subject(), self._get_body())
        if self._show_toast:
            self._show_toast(msg, "success" if success else "error")

    def _copy_body(self):
        body = self._get_body()
        if copy_to_clipboard(body) and self._show_toast:
            self._show_toast("Email body copied to clipboard", "success")

    def _save_smtp(self):
        config = {
            "smtp_server": self._smtp_server.get().strip() or "smtp.gmail.com",
            "smtp_port": int(self._smtp_port.get().strip() or "587"),
            "username": self._smtp_user.get().strip(),
            "password": self._smtp_pass.get().strip(),
            "from_addr": self._smtp_user.get().strip(),
            "default_to": self._smtp_default_to.get().strip(),
        }
        save_email_config(config)
        # Update the To field with default
        if config["default_to"] and not self._to_entry.get().strip():
            self._to_entry.insert(0, config["default_to"])
        if self._show_toast:
            self._show_toast("SMTP settings saved", "success")

    def refresh(self):
        pass
