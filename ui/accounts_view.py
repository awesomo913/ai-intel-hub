"""Accounts view — Chrome profile grid with quick-launch buttons."""

import logging
import threading
import customtkinter as ctk

from .theme import FONTS
from ..chrome_profiles import get_chrome_profiles, launch_profile

log = logging.getLogger(__name__)

# ── Quick-launch targets shown on every profile card ─────────────────────────
# Each entry: (label, url)
# Customize this list to match the AI services you use most.
QUICK_LAUNCH_TARGETS: list[tuple[str, str]] = [
    ("Gemini",     "https://gemini.google.com/app"),
    ("Claude.ai",  "https://claude.ai"),
    ("ChatGPT",    "https://chat.openai.com"),
    ("GitHub",     "https://github.com"),
    ("Gmail",      "https://mail.google.com"),
    ("Drive",      "https://drive.google.com"),
]
# ─────────────────────────────────────────────────────────────────────────────


class ProfileCard(ctk.CTkFrame):
    """A single Chrome profile card with avatar, name, email, and launch buttons."""

    def __init__(self, master, profile: dict, theme: dict, show_toast, **kwargs):
        super().__init__(
            master,
            fg_color=theme["bg_card"],
            corner_radius=12,
            **kwargs,
        )
        self._profile = profile
        self._theme = theme
        self._show_toast = show_toast
        self._build()

    def _build(self):
        t = self._theme
        p = self._profile

        # Avatar circle (initials)
        initials = (p["display_name"] or "?")[:2].upper()
        ctk.CTkLabel(
            self,
            text=initials,
            font=("Segoe UI", 20, "bold"),
            fg_color=p["avatar_color"],
            text_color="#ffffff",
            corner_radius=26,
            width=52,
            height=52,
        ).pack(pady=(14, 6))

        ctk.CTkLabel(
            self,
            text=p["display_name"] or "Unknown",
            font=FONTS["heading_sm"],
            text_color=t["fg"],
        ).pack()

        email_text = p["email"] or "No account signed in"
        ctk.CTkLabel(
            self,
            text=email_text,
            font=FONTS["body_sm"],
            text_color=t["fg_muted"],
            wraplength=180,
        ).pack(pady=(2, 8))

        # Quick-launch buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        for label, url in QUICK_LAUNCH_TARGETS:
            btn = ctk.CTkButton(
                btn_frame,
                text=label,
                font=FONTS["body_sm"],
                height=28,
                corner_radius=6,
                fg_color=t["bg_secondary"],
                hover_color=t["bg_card_hover"],
                text_color=t["fg"],
                command=lambda u=url, pd=self._profile: self._launch(u, pd),
            )
            btn.pack(fill="x", padx=2, pady=2)

        # Open Chrome (no URL) button
        ctk.CTkButton(
            self,
            text="Open Chrome",
            font=FONTS["button"],
            height=34,
            corner_radius=8,
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            command=lambda: self._launch(None, self._profile),
        ).pack(fill="x", padx=12, pady=(0, 14))

    def _launch(self, url, profile: dict):
        def _run():
            ok = launch_profile(
                profile_dir=profile["profile_dir"],
                user_data_dir=profile["user_data_dir"],
                url=url,
            )
            if not ok:
                self.after(0, lambda: self._show_toast("Chrome not found — check installation", "error"))
        threading.Thread(target=_run, daemon=True).start()
        self._show_toast(
            f"Opening {url.split('/')[2] if url else 'Chrome'} as {profile['display_name']}",
            "info",
        )


class AccountsView(ctk.CTkFrame):
    """Accounts tab — shows all Chrome profiles in a scrollable card grid."""

    def __init__(self, master, theme: dict, show_toast, **kwargs):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kwargs)
        self._theme = theme
        self._show_toast = show_toast
        self._profiles: list[dict] = []
        self._build()

    def _build(self):
        t = self._theme

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 12))

        ctk.CTkLabel(
            header,
            text="Chrome Accounts",
            font=FONTS["heading"],
            text_color=t["fg"],
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="Refresh Profiles",
            font=FONTS["button"],
            height=32,
            width=140,
            corner_radius=8,
            fg_color=t["bg_card"],
            hover_color=t["bg_card_hover"],
            text_color=t["fg"],
            command=self._load_profiles,
        ).pack(side="right")

        ctk.CTkLabel(
            self,
            text="Each card is one Chrome profile. Click a service to open it in that account.",
            font=FONTS["body_sm"],
            text_color=t["fg_muted"],
        ).pack(anchor="w", padx=24, pady=(0, 16))

        # Scrollable card area
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=t["bg"],
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Status label (shown while loading or if no profiles)
        self._status_label = ctk.CTkLabel(
            self._scroll,
            text="Loading Chrome profiles...",
            font=FONTS["body"],
            text_color=t["fg_muted"],
        )
        self._status_label.pack(pady=40)

    def refresh(self):
        """Called by the main app whenever this view is shown."""
        if self._profiles:
            # Re-render existing profiles (handles grid remount after tab switch)
            self._render_profiles(self._profiles)
        else:
            self._load_profiles()

    def _load_profiles(self):
        self._status_label.configure(text="Scanning Chrome profiles...")
        self._clear_cards()
        self._status_label.pack(pady=40)

        def _run():
            try:
                profiles = get_chrome_profiles()
                self.after(0, lambda: self._render_profiles(profiles))
            except Exception as exc:
                log.error("Could not load Chrome profiles: %s", exc)
                self.after(0, lambda: self._status_label.configure(
                    text=f"Error loading profiles: {exc}"
                ))

        threading.Thread(target=_run, daemon=True).start()

    def _render_profiles(self, profiles: list[dict]):
        self._profiles = profiles
        self._clear_cards()

        if not profiles:
            self._status_label.configure(
                text="No Chrome profiles found.\n\nMake sure Google Chrome is installed and has at least one profile."
            )
            self._status_label.pack(pady=40)
            return

        # Grid layout: 3 cards per row
        row_frame = None
        for i, profile in enumerate(profiles):
            if i % 3 == 0:
                row_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
                row_frame.pack(fill="x", pady=4, padx=8)

            card = ProfileCard(
                row_frame,
                profile=profile,
                theme=self._theme,
                show_toast=self._show_toast,
            )
            card.pack(side="left", padx=8, pady=4, fill="y")

        count_msg = f"{len(profiles)} profile{'s' if len(profiles) != 1 else ''} found"
        self._show_toast(count_msg, "success")

    def _clear_cards(self):
        self._status_label.pack_forget()
        for widget in self._scroll.winfo_children():
            if widget is not self._status_label:
                widget.destroy()
