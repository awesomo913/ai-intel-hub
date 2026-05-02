"""Email view - compose and send intelligence reports via email.
Refactored to Builder Pattern: __init__ -> _init_state() + _build_*() methods."""

import customtkinter as ctk
from .theme import FONTS
from ..emailer import (
    build_daily_digest, build_standouts_email, build_strategies_email,
    build_custom_email, build_html_digest, send_via_mailto, send_via_gmail_web,
    send_via_smtp, send_via_smtp_html, send_sms, SMS_GATEWAYS,
    save_email_config, _get_email_config, save_smtp_credential,
    start_scheduled_email,
)
from ..exporter import copy_to_clipboard
from .. import database as db


class EmailView(ctk.CTkScrollableFrame):
    """Compose and send AI intelligence emails."""

    def __init__(self, master, theme: dict, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._init_state(theme, show_toast)
        self._build_ui()

    def _init_state(self, theme: dict, show_toast):
        self._theme = theme
        self._show_toast = show_toast
        self._current_subject = ""
        self._current_body = ""

    def _build_ui(self):
        self._build_header()
        self._build_quick_toolbar()
        self._build_templates()
        self._build_compose()
        self._build_sms_section()
        self._build_smtp_settings()
        self._build_send_history()

    # --- Builders ---

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Email & SMS Reports", font=FONTS["heading_lg"],
            text_color=self._theme["fg"]
        ).pack(side="left")

        ctk.CTkLabel(
            self, text="Send AI intelligence reports via email or SMS text alerts.",
            font=FONTS["body_sm"], text_color=self._theme["fg_muted"],
            wraplength=800, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _build_quick_toolbar(self):
        """Quick-send icon toolbar."""
        t = self._theme
        toolbar = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=10)
        toolbar.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(toolbar, text="Quick Send:", font=FONTS["body_sm"],
                     text_color=t["fg_muted"]).pack(side="left", padx=(12, 8), pady=8)

        quick_actions = [
            ("📧 SMTP Digest", t["success"], self._quick_smtp_digest),
            ("🌐 Gmail", "#ea4335", self._quick_gmail_digest),
            ("📱 SMS Alert", t["info"], self._quick_sms),
            ("📋 Copy Top 5", t["bg_secondary"], self._quick_copy_top5),
        ]
        for text, color, cmd in quick_actions:
            ctk.CTkButton(
                toolbar, text=text, font=FONTS["button"],
                width=130, height=32, corner_radius=8, fg_color=color,
                command=cmd
            ).pack(side="left", padx=4, pady=8)

    def _build_templates(self):
        t = self._theme
        self._section("Quick Email Templates", "One-click compose with pre-built reports")

        frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        frame.pack(fill="x", padx=20, pady=(0, 15))

        templates = [
            ("\U0001F4A5 Groundbreaker + Top 5", "The #1 must-see article + top 5 standouts",
             self._compose_standouts),
            ("\U0001F4CA Daily Digest", "Full summary with stats, categories, and top articles",
             self._compose_digest),
            ("\U0001F310 HTML Digest", "Rich HTML email with color-coded scores and links",
             self._compose_html_digest),
            ("\U0001F4A1 Strategies Report", "All monetization strategies based on current trends",
             self._compose_strategies),
            ("\U0001F4CB Custom Selection", "Pick your own articles to include",
             self._compose_custom),
        ]

        for text, desc, cmd in templates:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)

            ctk.CTkButton(
                row, text=text, font=FONTS["button"],
                width=250, height=36, corner_radius=8, anchor="w",
                command=cmd
            ).pack(side="left", padx=(0, 12))

            ctk.CTkLabel(
                row, text=desc, font=FONTS["body_sm"],
                text_color=self._theme["fg_secondary"]
            ).pack(side="left")

    def _build_compose(self):
        t = self._theme
        self._section("Compose", "Review and customize before sending")

        frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        frame.pack(fill="x", padx=20, pady=(0, 15))

        email_cfg = _get_email_config()

        # To field (supports comma-separated recipients)
        to_row = ctk.CTkFrame(frame, fg_color="transparent")
        to_row.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(to_row, text="To:", font=FONTS["body"], text_color=t["fg"],
                     width=60).pack(side="left")
        self._to_entry = ctk.CTkEntry(
            to_row, font=FONTS["body"], height=34, corner_radius=8,
            placeholder_text="recipient@email.com, another@email.com"
        )
        self._to_entry.pack(side="left", fill="x", expand=True)
        default_to = email_cfg.get("default_to", "")
        if default_to:
            self._to_entry.insert(0, default_to)

        # CC field
        cc_row = ctk.CTkFrame(frame, fg_color="transparent")
        cc_row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(cc_row, text="CC:", font=FONTS["body"], text_color=t["fg"],
                     width=60).pack(side="left")
        self._cc_entry = ctk.CTkEntry(
            cc_row, font=FONTS["body"], height=34, corner_radius=8,
            placeholder_text="cc@email.com (optional)"
        )
        self._cc_entry.pack(side="left", fill="x", expand=True)
        if email_cfg.get("cc"):
            self._cc_entry.insert(0, email_cfg["cc"])

        # Subject
        subj_row = ctk.CTkFrame(frame, fg_color="transparent")
        subj_row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(subj_row, text="Subject:", font=FONTS["body"], text_color=t["fg"],
                     width=60).pack(side="left")
        self._subject_entry = ctk.CTkEntry(
            subj_row, font=FONTS["body"], height=34, corner_radius=8
        )
        self._subject_entry.pack(side="left", fill="x", expand=True)

        # Body preview
        ctk.CTkLabel(
            frame, text="Body Preview:", font=FONTS["body"], text_color=t["fg"]
        ).pack(anchor="w", padx=16, pady=(6, 2))

        self._body_text = ctk.CTkTextbox(
            frame, font=FONTS["mono_sm"], height=300,
            corner_radius=8, fg_color=t["bg_input"], text_color=t["fg"]
        )
        self._body_text.pack(fill="x", padx=16, pady=(0, 12))

        # Send buttons
        send_row = ctk.CTkFrame(frame, fg_color="transparent")
        send_row.pack(fill="x", padx=16, pady=(0, 12))

        for text, color, cmd in [
            ("\U0001F4E7 Open in Gmail", "#ea4335", self._send_gmail),
            ("\U0001F4EC Open in Email App", t["info"], self._send_mailto),
            ("\U0001F4E4 Send via SMTP", t["success"], self._send_smtp),
            ("\U0001F310 Send HTML", "#7c73ff", self._send_smtp_html),
            ("\U0001F4CB Copy Body", t["bg_secondary"], self._copy_body),
        ]:
            ctk.CTkButton(
                send_row, text=text, font=FONTS["button"],
                height=38, corner_radius=8, fg_color=color, command=cmd
            ).pack(side="left", padx=(0, 8))

    def _build_sms_section(self):
        t = self._theme
        self._section("SMS Text Alert", "Send a quick alert to your phone (Ctrl+T)")

        frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        frame.pack(fill="x", padx=20, pady=(0, 15))

        cfg = _get_email_config()

        fields = ctk.CTkFrame(frame, fg_color="transparent")
        fields.pack(fill="x", padx=16, pady=12)

        # Phone number row
        ctk.CTkLabel(fields, text="Phone #:", font=FONTS["body"],
                     text_color=t["fg"]).grid(row=0, column=0, sticky="w", pady=4)
        self._sms_phone = ctk.CTkEntry(
            fields, width=220, font=FONTS["body"],
            placeholder_text="10-digit number e.g. 5551234567"
        )
        self._sms_phone.grid(row=0, column=1, padx=8, pady=4)
        if cfg.get("sms_phone"):
            self._sms_phone.insert(0, cfg["sms_phone"])

        # Carrier dropdown row
        ctk.CTkLabel(fields, text="Carrier:", font=FONTS["body"],
                     text_color=t["fg"]).grid(row=1, column=0, sticky="w", pady=4)
        carrier_list = list(SMS_GATEWAYS.keys())
        self._sms_carrier = ctk.CTkComboBox(
            fields, values=carrier_list, width=220, font=FONTS["body"]
        )
        self._sms_carrier.grid(row=1, column=1, padx=8, pady=4)
        saved_carrier = cfg.get("sms_carrier", carrier_list[0])
        if saved_carrier in carrier_list:
            self._sms_carrier.set(saved_carrier)

        # Buttons row
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            btn_row, text="📱 Send SMS Alert (Ctrl+T)", font=FONTS["button"],
            height=38, corner_radius=8, fg_color=t["info"],
            command=self._send_sms
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="💾 Save SMS Settings", font=FONTS["button"],
            height=38, corner_radius=8, fg_color=t["bg_secondary"],
            command=self._save_sms_settings
        ).pack(side="left")

        self._sms_status = ctk.CTkLabel(
            frame, text="", font=FONTS["body_sm"], text_color=t["fg_muted"]
        )
        self._sms_status.pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            frame,
            text="Uses your existing SMTP config to send a short text via email-to-SMS gateway.",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        ).pack(anchor="w", padx=16, pady=(0, 12))

    def _build_smtp_settings(self):
        t = self._theme
        self._section("SMTP Settings", "For direct sending without opening a browser")

        frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        frame.pack(fill="x", padx=20, pady=(0, 15))

        fields = ctk.CTkFrame(frame, fg_color="transparent")
        fields.pack(fill="x", padx=16, pady=12)

        field_defs = [
            ("SMTP Server:", "smtp.gmail.com", False),
            ("Port:", "587", False),
            ("Username:", "your@gmail.com", False),
            ("App Password:", "xxxx xxxx xxxx xxxx", True),
            ("Default To:", "default recipient", False),
        ]
        entries = []
        for i, (label, placeholder, is_secret) in enumerate(field_defs):
            ctk.CTkLabel(fields, text=label, font=FONTS["body"],
                         text_color=t["fg"]).grid(row=i, column=0, sticky="w", pady=4)
            entry = ctk.CTkEntry(
                fields, width=300, font=FONTS["body"],
                placeholder_text=placeholder, show="*" if is_secret else ""
            )
            entry.grid(row=i, column=1, padx=8, pady=4)
            entries.append(entry)

        self._smtp_server, self._smtp_port, self._smtp_user, self._smtp_pass, self._smtp_default_to = entries

        # Schedule dropdown
        ctk.CTkLabel(fields, text="Auto-Send:", font=FONTS["body"],
                     text_color=t["fg"]).grid(row=len(field_defs), column=0, sticky="w", pady=4)
        schedule_opts = ["Off", "Daily 8am", "Daily 6pm", "Every 6 hours"]
        self._schedule_combo = ctk.CTkComboBox(
            fields, values=schedule_opts, width=300, font=FONTS["body"]
        )
        self._schedule_combo.grid(row=len(field_defs), column=1, padx=8, pady=4)

        # Load existing config
        cfg = _get_email_config()
        if cfg.get("smtp_server"):
            self._smtp_server.insert(0, cfg["smtp_server"])
        if cfg.get("smtp_port"):
            self._smtp_port.insert(0, str(cfg["smtp_port"]))
        if cfg.get("username"):
            self._smtp_user.insert(0, cfg["username"])
        if cfg.get("default_to"):
            self._smtp_default_to.insert(0, cfg["default_to"])
        saved_schedule = cfg.get("schedule_email", "Off")
        if saved_schedule in schedule_opts:
            self._schedule_combo.set(saved_schedule)

        ctk.CTkButton(
            frame, text="Save SMTP Settings", font=FONTS["button"],
            corner_radius=8, command=self._save_smtp
        ).pack(padx=16, pady=(0, 12))

        ctk.CTkLabel(
            frame, text="Password is stored securely in your OS keychain (Windows Credential Manager).",
            font=FONTS["body_sm"], text_color=t["success"]
        ).pack(padx=16, pady=(0, 4))

        ctk.CTkLabel(
            frame, text="For Gmail: use an App Password (Settings > Security > 2FA > App Passwords)",
            font=FONTS["body_sm"], text_color=t["fg_muted"]
        ).pack(padx=16, pady=(0, 12))

    def _build_send_history(self):
        t = self._theme
        self._section("Send History", "Last 10 email and SMS sends")

        self._history_frame = ctk.CTkFrame(self, fg_color=t["bg_card"], corner_radius=12)
        self._history_frame.pack(fill="x", padx=20, pady=(0, 20))
        self._refresh_history()

    def _refresh_history(self):
        for w in self._history_frame.winfo_children():
            w.destroy()
        t = self._theme

        history = db.get_email_history(limit=10)
        if not history:
            ctk.CTkLabel(
                self._history_frame, text="No sends yet",
                font=FONTS["body_sm"], text_color=t["fg_muted"]
            ).pack(padx=16, pady=12)
            return

        header = ctk.CTkFrame(self._history_frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(8, 4))
        for txt, w in [("Time", 130), ("To", 220), ("Method", 80), ("Status", 60)]:
            ctk.CTkLabel(header, text=txt, font=FONTS["tag"],
                         text_color=t["fg_muted"], width=w, anchor="w").pack(side="left")

        for row in history:
            r = ctk.CTkFrame(self._history_frame, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=2)
            sent_at = row.get("sent_at", "")[:16]
            to_addr = row.get("to_addr", "")[:30]
            method = row.get("method", "")
            success = row.get("success", 0)
            status_text = "✅" if success else "❌"
            status_color = t["success"] if success else t["error"]
            for txt, w, color in [
                (sent_at, 130, t["fg_secondary"]),
                (to_addr, 220, t["fg"]),
                (method, 80, t["fg_muted"]),
                (status_text, 60, status_color),
            ]:
                ctk.CTkLabel(r, text=txt, font=FONTS["body_sm"],
                             text_color=color, width=w, anchor="w").pack(side="left")

    # --- Helpers ---

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

    # --- Template Actions ---

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

    def _compose_html_digest(self):
        subject, html = build_html_digest()
        self._set_compose(subject, html)
        if self._show_toast:
            self._show_toast("HTML digest composed (use Send HTML button)", "success")

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

    def _get_cc(self) -> str:
        return self._cc_entry.get().strip()

    def _get_subject(self) -> str:
        return self._subject_entry.get().strip()

    def _get_body(self) -> str:
        return self._body_text.get("0.0", "end").strip()

    # --- Send Actions ---

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
        success, msg = send_via_smtp(to, self._get_subject(), self._get_body(),
                                     cc=self._get_cc())
        if self._show_toast:
            self._show_toast(msg, "success" if success else "error")
        self._refresh_history()

    def _send_smtp_html(self):
        to = self._get_to()
        if not to:
            if self._show_toast:
                self._show_toast("Enter a recipient email address", "warning")
            return
        success, msg = send_via_smtp_html(to, self._get_subject(), self._get_body(),
                                          cc=self._get_cc())
        if self._show_toast:
            self._show_toast(msg, "success" if success else "error")
        self._refresh_history()

    def _copy_body(self):
        body = self._get_body()
        if copy_to_clipboard(body) and self._show_toast:
            self._show_toast("Email body copied to clipboard", "success")

    def _send_sms(self):
        phone = self._sms_phone.get().strip()
        carrier = self._sms_carrier.get()
        if not phone:
            self._sms_status.configure(text="⚠️ Enter a phone number", text_color=self._theme["warning"])
            return
        if not carrier:
            self._sms_status.configure(text="⚠️ Select a carrier", text_color=self._theme["warning"])
            return
        self._sms_status.configure(text="Sending...", text_color=self._theme["fg_muted"])
        self.update_idletasks()

        import threading as _threading

        def _run():
            success, msg = send_sms(phone, carrier)
            color = self._theme["success"] if success else self._theme["error"]
            icon = "✅" if success else "❌"
            self.after(0, lambda: self._sms_status.configure(
                text=f"{icon} {msg}", text_color=color
            ))
            if self._show_toast:
                self.after(0, lambda: self._show_toast(msg, "success" if success else "error"))
            self.after(0, self._refresh_history)

        _threading.Thread(target=_run, daemon=True).start()

    def send_sms_alert(self):
        """Public entry-point for Ctrl+T shortcut."""
        self._send_sms()

    def _save_sms_settings(self):
        cfg = _get_email_config()
        cfg["sms_phone"] = self._sms_phone.get().strip()
        cfg["sms_carrier"] = self._sms_carrier.get()
        save_email_config(cfg)
        if self._show_toast:
            self._show_toast("SMS settings saved", "success")

    def _save_smtp(self):
        schedule = self._schedule_combo.get()
        config = {
            "smtp_server": self._smtp_server.get().strip() or "smtp.gmail.com",
            "smtp_port": int(self._smtp_port.get().strip() or "587"),
            "username": self._smtp_user.get().strip(),
            "password": self._smtp_pass.get().strip(),
            "from_addr": self._smtp_user.get().strip(),
            "default_to": self._smtp_default_to.get().strip(),
            "schedule_email": schedule,
        }
        # Preserve CC if already saved
        existing = _get_email_config()
        if existing.get("cc"):
            config["cc"] = existing["cc"]
        if existing.get("sms_phone"):
            config["sms_phone"] = existing["sms_phone"]
        if existing.get("sms_carrier"):
            config["sms_carrier"] = existing["sms_carrier"]
        save_email_config(config)
        if config["default_to"] and not self._to_entry.get().strip():
            self._to_entry.insert(0, config["default_to"])
        # Start scheduled email if configured
        if schedule != "Off":
            start_scheduled_email(schedule)
        if self._show_toast:
            self._show_toast("SMTP settings saved (password in OS keychain)", "success")

    # --- Quick-send toolbar handlers ---

    def _quick_smtp_digest(self):
        to = self._get_to()
        cfg = _get_email_config()
        to = to or cfg.get("default_to", "")
        if not to:
            if self._show_toast:
                self._show_toast("Enter a recipient in the To field first", "warning")
            return
        subject, body = build_daily_digest()
        success, msg = send_via_smtp(to, subject, body)
        if self._show_toast:
            self._show_toast(msg, "success" if success else "error")
        self._refresh_history()

    def _quick_gmail_digest(self):
        to = self._get_to()
        cfg = _get_email_config()
        to = to or cfg.get("default_to", "")
        if not to:
            if self._show_toast:
                self._show_toast("Enter a recipient in the To field first", "warning")
            return
        subject, body = build_standouts_email()
        send_via_gmail_web(to, subject, body)
        if self._show_toast:
            self._show_toast("Opened Gmail compose", "success")

    def _quick_sms(self):
        self._send_sms()

    def _quick_copy_top5(self):
        from ..analyzer import get_standouts
        standouts = get_standouts(limit=5)
        if not standouts:
            if self._show_toast:
                self._show_toast("No standouts available yet", "warning")
            return
        lines = ["TOP 5 AI INTEL STANDOUTS", "=" * 40, ""]
        for i, a in enumerate(standouts, 1):
            lines.append(f"{i}. {a['title']}")
            lines.append(f"   {a['url']}")
            lines.append("")
        text = "\n".join(lines)
        if copy_to_clipboard(text) and self._show_toast:
            self._show_toast("Top 5 copied to clipboard", "success")

    def refresh(self):
        self._refresh_history()
