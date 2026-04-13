"""Health & Logs view - performance monitoring, bottleneck detection, session history."""

import customtkinter as ctk
from datetime import datetime
from .theme import FONTS, blend_color
from ..perf_logger import get_performance_summary, get_bottleneck_report, get_recent_events
from ..session_manager import get_session_history
from ..diagnostics import calculate_health_score, _get_source_health, _get_db_health


class HealthView(ctk.CTkScrollableFrame):
    """Health monitor, performance logs, bottleneck reports, session history."""

    def __init__(self, master, theme: dict, show_toast=None, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._theme = theme
        self._show_toast = show_toast

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Health & Logs", font=FONTS["heading_lg"],
            text_color=theme["fg"]
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Generate Full Report", font=FONTS["button"],
            corner_radius=8, fg_color=theme["info"],
            command=self._gen_report
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            header, text="Refresh", font=FONTS["button"],
            corner_radius=8, fg_color=theme["accent"],
            command=self.refresh
        ).pack(side="right")

        # Health score card
        self.score_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.score_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Bottlenecks
        self._section("Bottlenecks & Fix Suggestions")
        self.bottleneck_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.bottleneck_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Performance stats
        self._section("Performance (Last 24h)")
        self.perf_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.perf_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Source health table
        self._section("Source Health")
        self.source_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.source_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Database health
        self._section("Database Health")
        self.db_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.db_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Recent events log
        self._section("Recent Events Log")
        self.events_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.events_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Session history
        self._section("Session History")
        self.session_frame = ctk.CTkFrame(self, fg_color=theme["bg_card"], corner_radius=12)
        self.session_frame.pack(fill="x", padx=20, pady=(0, 20))

    def _section(self, title: str):
        ctk.CTkLabel(
            self, text=title, font=FONTS["heading"],
            text_color=self._theme["fg"]
        ).pack(anchor="w", padx=20, pady=(15, 8))

    def refresh(self):
        self._refresh_health_score()
        self._refresh_bottlenecks()
        self._refresh_perf()
        self._refresh_source_health()
        self._refresh_db_health()
        self._refresh_events()
        self._refresh_sessions()

    def _refresh_health_score(self):
        for w in self.score_frame.winfo_children():
            w.destroy()
        t = self._theme

        score, reasons = calculate_health_score()
        color = t["success"] if score >= 80 else (t["warning"] if score >= 50 else t["error"])
        label = "HEALTHY" if score >= 80 else ("NEEDS ATTENTION" if score >= 50 else "CRITICAL")

        row = ctk.CTkFrame(self.score_frame, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(
            row, text=str(score), font=("Segoe UI", 48, "bold"),
            text_color=color
        ).pack(side="left", padx=(0, 8))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info, text=f"/100  {label}",
            font=FONTS["heading"], text_color=color
        ).pack(anchor="w")

        for reason in reasons[:5]:
            ctk.CTkLabel(
                info, text=f"  - {reason}",
                font=FONTS["body_sm"], text_color=t["fg_secondary"]
            ).pack(anchor="w")

    def _refresh_bottlenecks(self):
        for w in self.bottleneck_frame.winfo_children():
            w.destroy()
        t = self._theme

        issues = get_bottleneck_report()
        for issue in issues:
            sev = issue["severity"]
            color = {
                "critical": t["error"], "warning": t["warning"],
                "info": t["info"], "good": t["success"]
            }.get(sev, t["fg_muted"])

            row = ctk.CTkFrame(self.bottleneck_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                row, text=sev.upper(), font=FONTS["tag"],
                text_color="#fff",
                fg_color=color, corner_radius=6, padx=8, pady=2,
                width=70
            ).pack(side="left", padx=(0, 10))

            detail = ctk.CTkFrame(row, fg_color="transparent")
            detail.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                detail, text=issue["issue"], font=FONTS["body"],
                text_color=t["fg"], anchor="w", wraplength=600, justify="left"
            ).pack(anchor="w")

            ctk.CTkLabel(
                detail, text=f"Fix: {issue['fix']}", font=FONTS["body_sm"],
                text_color=t["success"], anchor="w", wraplength=600, justify="left"
            ).pack(anchor="w")

    def _refresh_perf(self):
        for w in self.perf_frame.winfo_children():
            w.destroy()
        t = self._theme

        perf = get_performance_summary(hours=24)
        if perf.get("status") == "no_data":
            ctk.CTkLabel(
                self.perf_frame, text="No performance data yet. Run a fetch first.",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=16, pady=16)
            return

        stats_data = [
            ("Total Fetches", str(perf.get("total_fetches", 0)), t["accent"]),
            ("Total Errors", str(perf.get("total_errors", 0)),
             t["error"] if perf.get("total_errors", 0) > 0 else t["success"]),
            ("Error Rate", f"{perf.get('error_rate', 0)}%",
             t["error"] if perf.get("error_rate", 0) > 10 else t["success"]),
            ("Articles Fetched", str(perf.get("total_articles_fetched", 0)), t["info"]),
            ("Avg Fetch Time", f"{perf.get('avg_fetch_time_ms', 0):.0f}ms", t["fg"]),
            ("Avg Full Refresh", f"{perf.get('avg_full_fetch_ms', 0)/1000:.1f}s", t["fg"]),
        ]

        grid = ctk.CTkFrame(self.perf_frame, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=12)

        for i, (label, value, color) in enumerate(stats_data):
            col = i % 3
            row_idx = i // 3
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=row_idx, column=col, padx=10, pady=6, sticky="w")
            grid.columnconfigure(col, weight=1)

            ctk.CTkLabel(cell, text=value, font=FONTS["heading"], text_color=color).pack(anchor="w")
            ctk.CTkLabel(cell, text=label, font=FONTS["body_sm"], text_color=t["fg_muted"]).pack(anchor="w")

        # Slowest sources
        if perf.get("slowest_sources"):
            ctk.CTkLabel(
                self.perf_frame, text="Slowest Sources:", font=FONTS["heading_sm"],
                text_color=t["fg"]
            ).pack(anchor="w", padx=16, pady=(8, 4))

            for name, ms in perf["slowest_sources"][:5]:
                color = t["error"] if ms > 10000 else (t["warning"] if ms > 5000 else t["fg_secondary"])
                row = ctk.CTkFrame(self.perf_frame, fg_color="transparent")
                row.pack(fill="x", padx=24, pady=2)
                ctk.CTkLabel(row, text=f"{name}: {ms/1000:.1f}s", font=FONTS["body_sm"],
                             text_color=color).pack(side="left")

    def _refresh_source_health(self):
        for w in self.source_frame.winfo_children():
            w.destroy()
        t = self._theme

        sources = _get_source_health()
        status_order = {"BROKEN": 0, "UNRELIABLE": 1, "NEVER_FETCHED": 2, "DISABLED": 3, "HEALTHY": 4}
        sources.sort(key=lambda x: status_order.get(x["status"], 5))

        for s in sources:
            row = ctk.CTkFrame(self.source_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)

            status_colors = {
                "HEALTHY": t["success"], "BROKEN": t["error"],
                "UNRELIABLE": t["warning"], "DISABLED": t["fg_muted"],
                "NEVER_FETCHED": t["info"],
            }
            color = status_colors.get(s["status"], t["fg_muted"])

            ctk.CTkLabel(
                row, text=s["status"], font=FONTS["tag"],
                text_color=color, width=100, anchor="w"
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=s["name"], font=FONTS["body_sm"],
                text_color=t["fg"], width=200, anchor="w"
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=f"fetches: {s['fetches']}  errors: {s['errors']}  rate: {s['error_rate']}%",
                font=FONTS["body_sm"], text_color=t["fg_muted"]
            ).pack(side="left")

    def _refresh_db_health(self):
        for w in self.db_frame.winfo_children():
            w.destroy()
        t = self._theme

        health = _get_db_health()
        items = [
            ("Integrity", health.get("integrity", "unknown")),
            ("Size", f"{health.get('size_kb', 0)} KB"),
            ("Journal Mode", health.get("journal_mode", "unknown")),
            ("Fragmentation", f"{health.get('fragmentation_pct', 0)}%"),
            ("Orphaned Articles", str(health.get("orphaned_articles", 0))),
        ]
        for label, value in items:
            row = ctk.CTkFrame(self.db_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=f"{label}:", font=FONTS["body"],
                         text_color=t["fg"], width=150, anchor="w").pack(side="left")
            color = t["success"] if "ok" in str(value).lower() or value == "0" else t["fg_secondary"]
            ctk.CTkLabel(row, text=value, font=FONTS["mono"],
                         text_color=color).pack(side="left")

    def _refresh_events(self):
        for w in self.events_frame.winfo_children():
            w.destroy()
        t = self._theme

        events = get_recent_events(hours=24, limit=30)
        if not events:
            ctk.CTkLabel(
                self.events_frame, text="No events logged yet.",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=16, pady=16)
            return

        for e in reversed(events[-20:]):
            row = ctk.CTkFrame(self.events_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=1)

            ts = e.get("ts", "")
            if "T" in ts:
                ts = ts.split("T")[1][:8]

            color = t["error"] if not e.get("success", True) else t["fg_muted"]
            ctk.CTkLabel(row, text=ts, font=FONTS["mono_sm"],
                         text_color=t["fg_muted"], width=65, anchor="w").pack(side="left")

            ev = e.get("event", "")
            ctk.CTkLabel(row, text=ev, font=FONTS["mono_sm"],
                         text_color=t["accent"], width=100, anchor="w").pack(side="left")

            source = e.get("source", "")
            if source:
                ctk.CTkLabel(row, text=source[:25], font=FONTS["mono_sm"],
                             text_color=t["fg_secondary"], width=180, anchor="w").pack(side="left")

            dur = e.get("duration_ms", 0)
            if dur:
                ctk.CTkLabel(row, text=f"{dur:.0f}ms", font=FONTS["mono_sm"],
                             text_color=t["fg_muted"], width=70, anchor="w").pack(side="left")

            err = e.get("error", "")
            if err:
                ctk.CTkLabel(row, text=err[:50], font=FONTS["mono_sm"],
                             text_color=t["error"]).pack(side="left")
            elif e.get("articles", 0):
                ctk.CTkLabel(row, text=f"+{e['articles']} articles", font=FONTS["mono_sm"],
                             text_color=t["success"]).pack(side="left")

    def _refresh_sessions(self):
        for w in self.session_frame.winfo_children():
            w.destroy()
        t = self._theme

        sessions = get_session_history(limit=10)
        if not sessions:
            ctk.CTkLabel(
                self.session_frame, text="No session history yet.",
                font=FONTS["body"], text_color=t["fg_muted"]
            ).pack(padx=16, pady=16)
            return

        for s in reversed(sessions):
            row = ctk.CTkFrame(self.session_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)

            started = s.get("started", "")[:16].replace("T", " ")
            ctk.CTkLabel(row, text=started, font=FONTS["mono_sm"],
                         text_color=t["fg_muted"], width=120, anchor="w").pack(side="left")

            dur = s.get("duration_minutes", 0)
            ctk.CTkLabel(row, text=f"{dur:.0f}min", font=FONTS["body_sm"],
                         text_color=t["fg"], width=60, anchor="w").pack(side="left")

            fetched = s.get("articles_fetched", 0)
            ctk.CTkLabel(row, text=f"+{fetched} articles", font=FONTS["body_sm"],
                         text_color=t["success"], width=100, anchor="w").pack(side="left")

            errs = s.get("errors_count", 0)
            err_color = t["error"] if errs > 0 else t["fg_muted"]
            ctk.CTkLabel(row, text=f"{errs} errors", font=FONTS["body_sm"],
                         text_color=err_color, width=80, anchor="w").pack(side="left")

            views = ", ".join(s.get("views_visited", []))
            ctk.CTkLabel(row, text=views, font=FONTS["body_sm"],
                         text_color=t["fg_muted"]).pack(side="left")

    def _gen_report(self):
        from ..diagnostics import generate_diagnostic_report
        path = generate_diagnostic_report()
        if self._show_toast:
            self._show_toast(f"Report saved: {path.name}", "success")
