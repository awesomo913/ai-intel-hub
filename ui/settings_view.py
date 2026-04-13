"""Expanded settings view - 30+ options, profiles, session customization, data management."""

import customtkinter as ctk
from .theme import FONTS
from ..config import AppConfig, save_config
from ..diagnostics import generate_diagnostic_report
from ..platform_utils import get_app_dir, get_data_dir, get_export_dir
from ..session_manager import get_profiles, apply_profile, save_profile
from .. import database as db


class SettingsView(ctk.CTkScrollableFrame):
    """Application settings with 30+ configurable options and profiles."""

    def __init__(self, master, theme: dict, config: AppConfig,
                 on_theme_change=None, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._theme = theme
        self._config = config
        self._on_theme_change = on_theme_change
        self._show_toast = show_toast
        self._widgets = {}

        ctk.CTkLabel(
            self, text="Settings", font=FONTS["heading_lg"],
            text_color=theme["fg"]
        ).pack(anchor="w", padx=20, pady=(20, 20))

        # === SESSION PROFILES ===
        self._section("Session Profiles", "Switch between pre-configured modes instantly")

        profile_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        profile_frame.pack(fill="x", padx=20, pady=(0, 15))

        pr = ctk.CTkFrame(profile_frame, fg_color="transparent")
        pr.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(pr, text="Active Profile:", font=FONTS["body"], text_color=theme["fg"]).pack(side="left")

        profiles = get_profiles()
        profile_names = list(profiles.keys())
        self._profile_var = ctk.StringVar(value=config.active_profile)
        self._profile_menu = ctk.CTkComboBox(
            pr, values=profile_names, variable=self._profile_var,
            width=180, font=FONTS["body"], command=self._on_profile_change
        )
        self._profile_menu.pack(side="left", padx=12)

        ctk.CTkButton(
            pr, text="Apply", font=FONTS["button"], width=70,
            corner_radius=8, command=self._apply_profile
        ).pack(side="left", padx=(0, 8))

        # Profile descriptions
        self.profile_desc = ctk.CTkLabel(
            profile_frame, text=profiles.get(config.active_profile, {}).get("description", ""),
            font=FONTS["body_sm"], text_color=theme["fg_muted"]
        )
        self.profile_desc.pack(padx=16, pady=(0, 12))

        # === APPEARANCE ===
        self._section("Appearance", "Visual customization")

        app_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        app_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._add_segmented(app_frame, "Theme:", "theme", ["dark", "light"], self._change_theme)
        self._add_slider(app_frame, "Font Size:", "font_size", 8, 24, 16)
        self._add_switch(app_frame, "Compact Mode:", "compact_mode")
        self._add_switch(app_frame, "Show Article Previews:", "show_article_previews")
        self._add_switch(app_frame, "Highlight High Relevance:", "highlight_high_relevance")
        self._add_combo(app_frame, "Articles Per Page:", "articles_per_page",
                        ["10", "20", "30", "50", "100"])
        self._add_slider(app_frame, "High Relevance Threshold:", "high_relevance_threshold", 0.1, 1.0, 18,
                         fmt=lambda v: f"{v:.0%}")

        # === FETCHING ===
        self._section("Data Fetching", "Control how and when articles are fetched")

        fetch_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        fetch_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._add_switch(fetch_frame, "Auto-Refresh:", "auto_refresh_enabled")
        self._add_combo(fetch_frame, "Refresh Interval:", "auto_refresh_minutes",
                        ["5", "10", "15", "30", "60", "120", "240"], suffix="min")
        self._add_combo(fetch_frame, "Max Articles/Source:", "max_articles_per_source",
                        ["10", "25", "50", "100", "200"])
        self._add_combo(fetch_frame, "Fetch Timeout:", "fetch_timeout_seconds",
                        ["5", "10", "15", "20", "30", "60"], suffix="sec")
        self._add_combo(fetch_frame, "Concurrent Fetches:", "max_concurrent_fetches",
                        ["1", "2", "4", "6", "8", "10", "15"])
        self._add_combo(fetch_frame, "Max Retries:", "max_retries",
                        ["0", "1", "2", "3", "5"])
        self._add_combo(fetch_frame, "Retry Delay:", "retry_delay_seconds",
                        ["1", "2", "3", "5", "10"], suffix="sec")
        self._add_switch(fetch_frame, "Fetch on Startup:", "fetch_on_startup")

        # === CONTENT FILTERING ===
        self._section("Content Filtering", "Control what shows up in your feed")

        filter_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        filter_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._add_slider(filter_frame, "Relevance Threshold:", "relevance_threshold", 0.0, 1.0, 20,
                         fmt=lambda v: f"{v:.0%}")
        self._add_switch(filter_frame, "Show Read Articles:", "show_read_articles")
        self._add_segmented(filter_frame, "Default Sort:", "default_sort",
                            ["date", "relevance", "source"])
        self._add_combo(filter_frame, "Min Summary Length:", "min_summary_length",
                        ["0", "20", "50", "100"])

        # === NOTIFICATIONS ===
        self._section("Notifications", "Toast and alert preferences")

        notif_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        notif_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._add_switch(notif_frame, "Notify on Fetch:", "notification_on_fetch")
        self._add_switch(notif_frame, "Notify on Error:", "notification_on_error")
        self._add_combo(notif_frame, "Toast Duration:", "toast_duration_ms",
                        ["1000", "2000", "3000", "5000", "8000"], suffix="ms")

        # === AUTOMATION ===
        self._section("Automation", "Background tasks and maintenance")

        auto_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        auto_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._add_switch(auto_frame, "Auto-Score Articles:", "auto_score_articles")
        self._add_switch(auto_frame, "Auto-Generate Strategies:", "auto_generate_strategies")
        self._add_combo(auto_frame, "Auto-Cleanup Older Than:", "auto_cleanup_days",
                        ["30", "60", "90", "180", "365"], suffix="days")
        self._add_switch(auto_frame, "Auto-Backup:", "auto_backup_enabled")
        self._add_combo(auto_frame, "Backup Interval:", "auto_backup_interval_hours",
                        ["6", "12", "24", "48", "72"], suffix="hrs")

        # === PERFORMANCE ===
        self._section("Performance & Logging", "Diagnostics and monitoring")

        perf_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        perf_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._add_switch(perf_frame, "Performance Logging:", "perf_logging_enabled")
        self._add_switch(perf_frame, "Session Tracking:", "session_tracking_enabled")
        self._add_segmented(perf_frame, "Log Level:", "log_level",
                            ["DEBUG", "INFO", "WARNING", "ERROR"])
        self._add_switch(perf_frame, "Vacuum DB on Startup:", "db_vacuum_on_startup")

        # === EXPORT ===
        self._section("Export Defaults", "Default settings for exports")

        export_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        export_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._add_segmented(export_frame, "Default Format:", "export_format",
                            ["markdown", "csv", "json", "text"])
        self._add_switch(export_frame, "Include Summary:", "export_include_summary")
        self._add_switch(export_frame, "Include Scores:", "export_include_scores")
        self._add_combo(export_frame, "Max Export Articles:", "export_max_articles",
                        ["100", "200", "500", "1000", "2000"])

        # === DATA MANAGEMENT ===
        self._section("Data Management", "Database and file operations")

        data_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        data_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.stats_label = ctk.CTkLabel(
            data_frame, text="", font=FONTS["body"], text_color=theme["fg_secondary"]
        )
        self.stats_label.pack(padx=16, pady=(12, 8))

        btn_row = ctk.CTkFrame(data_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkButton(
            btn_row, text="Generate Diagnostic Report", font=FONTS["button"],
            corner_radius=8, fg_color=theme["info"], command=self._run_diagnostic
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Open Export Folder", font=FONTS["button"],
            corner_radius=8, fg_color=theme["bg_secondary"], command=self._open_export_folder
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Open Data Folder", font=FONTS["button"],
            corner_radius=8, fg_color=theme["bg_secondary"], command=self._open_data_folder
        ).pack(side="left")

        btn_row2 = ctk.CTkFrame(data_frame, fg_color="transparent")
        btn_row2.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            btn_row2, text="Vacuum Database", font=FONTS["button"],
            corner_radius=8, fg_color=theme["warning"], command=self._vacuum_db
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row2, text="Reset Broken Sources", font=FONTS["button"],
            corner_radius=8, fg_color=theme["error"], command=self._reset_broken_sources
        ).pack(side="left")

        # === PATHS ===
        self._section("File Paths", "Where your data lives")

        paths_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        paths_frame.pack(fill="x", padx=20, pady=(0, 15))

        for label, path in [("Config:", get_app_dir()), ("Data:", get_data_dir()),
                            ("Exports:", get_export_dir())]:
            row = ctk.CTkFrame(paths_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(row, text=label, font=FONTS["body"], text_color=theme["fg"],
                         width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(path), font=FONTS["mono_sm"],
                         text_color=theme["fg_muted"], anchor="w").pack(side="left", fill="x")

        # === KEYBOARD SHORTCUTS ===
        self._section("Keyboard Shortcuts", "Quick navigation")

        kb_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        kb_frame.pack(fill="x", padx=20, pady=(0, 20))

        shortcuts = [
            ("Ctrl+R", "Refresh all feeds"),
            ("Ctrl+F", "Focus search bar"),
            ("Ctrl+E", "Open export center"),
            ("Ctrl+D", "Go to dashboard"),
            ("Ctrl+H", "Open health & logs"),
            ("Ctrl+1-6", "Navigate sidebar tabs"),
            ("F5", "Refresh current view"),
        ]
        for key, desc in shortcuts:
            row = ctk.CTkFrame(kb_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=key, font=FONTS["mono"], text_color=theme["accent"],
                         width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=FONTS["body_sm"],
                         text_color=theme["fg_secondary"]).pack(side="left")

    # --- Widget Builders ---

    def _section(self, title: str, subtitle: str = ""):
        ctk.CTkLabel(self, text=title, font=FONTS["heading"],
                     text_color=self._theme["fg"]).pack(anchor="w", padx=20, pady=(15, 2))
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=FONTS["body_sm"],
                         text_color=self._theme["fg_muted"]).pack(anchor="w", padx=20, pady=(0, 8))

    def _add_switch(self, parent, label: str, key: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(row, text=label, font=FONTS["body"],
                     text_color=self._theme["fg"]).pack(side="left")
        var = ctk.BooleanVar(value=getattr(self._config, key, False))
        sw = ctk.CTkSwitch(row, text="", variable=var, command=self._save_all)
        sw.pack(side="right")
        self._widgets[key] = ("bool", var)

    def _add_combo(self, parent, label: str, key: str, values: list, suffix: str = ""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(row, text=label, font=FONTS["body"],
                     text_color=self._theme["fg"]).pack(side="left")
        if suffix:
            ctk.CTkLabel(row, text=suffix, font=FONTS["body_sm"],
                         text_color=self._theme["fg_muted"]).pack(side="right", padx=(8, 0))
        var = ctk.StringVar(value=str(getattr(self._config, key, values[0])))
        cb = ctk.CTkComboBox(row, values=values, variable=var, width=100,
                             font=FONTS["body"], command=lambda _: self._save_all())
        cb.pack(side="right")
        self._widgets[key] = ("int_str", var)

    def _add_segmented(self, parent, label: str, key: str, values: list, cmd=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(row, text=label, font=FONTS["body"],
                     text_color=self._theme["fg"]).pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._config, key, values[0])))
        def _on_change(val):
            self._save_all()
            if cmd:
                cmd(val)
        ctk.CTkSegmentedButton(
            row, values=values, variable=var, font=FONTS["body_sm"],
            command=_on_change
        ).pack(side="right")
        self._widgets[key] = ("str", var)

    def _add_slider(self, parent, label: str, key: str, min_v, max_v, steps,
                    fmt=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(row, text=label, font=FONTS["body"],
                     text_color=self._theme["fg"]).pack(side="left")

        current = getattr(self._config, key, min_v)
        if fmt:
            lbl_text = fmt(current)
        else:
            lbl_text = str(int(current)) if isinstance(current, (int, float)) and current == int(current) else str(current)

        val_lbl = ctk.CTkLabel(row, text=lbl_text, font=FONTS["body_sm"],
                               text_color=self._theme["fg_muted"], width=50)
        val_lbl.pack(side="right")

        def _on_slide(v):
            if fmt:
                val_lbl.configure(text=fmt(v))
            else:
                val_lbl.configure(text=str(int(v)))
            self._save_all()

        sl = ctk.CTkSlider(row, from_=min_v, to=max_v, number_of_steps=steps,
                           command=_on_slide)
        sl.set(current)
        sl.pack(side="right", padx=8)
        self._widgets[key] = ("slider", sl)

    # --- Actions ---

    def _save_all(self):
        for key, (wtype, widget) in self._widgets.items():
            if wtype == "bool":
                setattr(self._config, key, widget.get())
            elif wtype == "str":
                setattr(self._config, key, widget.get())
            elif wtype == "int_str":
                try:
                    val = widget.get()
                    current = getattr(self._config, key)
                    if isinstance(current, int):
                        setattr(self._config, key, int(val))
                    elif isinstance(current, float):
                        setattr(self._config, key, float(val))
                    else:
                        setattr(self._config, key, val)
                except (ValueError, TypeError):
                    pass
            elif wtype == "slider":
                val = widget.get()
                current = getattr(self._config, key)
                if isinstance(current, int):
                    setattr(self._config, key, int(val))
                else:
                    setattr(self._config, key, round(val, 2))
        save_config(self._config)

    def _on_profile_change(self, name):
        profiles = get_profiles()
        desc = profiles.get(name, {}).get("description", "")
        self.profile_desc.configure(text=desc)

    def _apply_profile(self):
        name = self._profile_var.get()
        apply_profile(name, self._config)
        self._config.active_profile = name
        save_config(self._config)
        # Update all widgets
        for key, (wtype, widget) in self._widgets.items():
            val = getattr(self._config, key, None)
            if val is not None:
                if wtype == "bool":
                    widget.set(val)
                elif wtype in ("str", "int_str"):
                    widget.set(str(val))
                elif wtype == "slider":
                    widget.set(val)
        if self._show_toast:
            self._show_toast(f"Applied profile: {name}", "success")

    def _change_theme(self, value):
        self._config.theme = value
        self._save_all()
        if self._on_theme_change:
            self._on_theme_change(value)

    def _run_diagnostic(self):
        path = generate_diagnostic_report()
        if self._show_toast:
            self._show_toast(f"Report saved to Desktop: {path.name}", "success")

    def _vacuum_db(self):
        import threading
        # Disable button during operation
        for w in self.winfo_children():
            pass  # Can't easily grab button ref, use toast as feedback
        if self._show_toast:
            self._show_toast("Vacuuming database...", "info")

        def _run():
            try:
                db.vacuum_database()
                if self._show_toast:
                    self.after(0, lambda: self._show_toast(
                        "Database vacuumed successfully", "success"))
            except Exception as e:
                if self._show_toast:
                    self.after(0, lambda: self._show_toast(
                        f"Vacuum failed: {e}", "error"))

        threading.Thread(target=_run, daemon=True).start()

    def _reset_broken_sources(self):
        db.reset_source_errors()
        if self._show_toast:
            self._show_toast("Error counts reset for all sources", "success")

    def _open_export_folder(self):
        import subprocess, sys
        folder = str(get_export_dir())
        if sys.platform == "win32":
            subprocess.Popen(["explorer", folder])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _open_data_folder(self):
        import subprocess, sys
        folder = str(get_data_dir())
        if sys.platform == "win32":
            subprocess.Popen(["explorer", folder])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def refresh(self):
        stats = db.get_stats()
        self.stats_label.configure(
            text=f"Articles: {stats['total_articles']} | "
                 f"Sources: {stats['active_sources']} | "
                 f"Strategies: {stats['strategies']} | "
                 f"Bookmarked: {stats['bookmarked']}"
        )
