"""Chrome profile manager — discover installed profiles and launch accounts."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_CHROME_DIRS = [
    Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data",
    Path.home() / "AppData" / "Local" / "Google" / "Chrome Beta" / "User Data",
    Path.home() / "AppData" / "Local" / "Google" / "Chrome SxS" / "User Data",
]

_CHROME_EXES = [
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
]


def _find_chrome_exe() -> Optional[Path]:
    for p in _CHROME_EXES:
        if p.exists():
            return p
    return None


def _read_profile_prefs(profile_path: Path) -> dict:
    prefs_file = profile_path / "Preferences"
    if not prefs_file.exists():
        return {}
    try:
        raw = prefs_file.read_bytes()
        return json.loads(raw)
    except Exception as exc:
        log.warning("Could not read profile prefs at %s: %s", profile_path, exc)
        return {}


def get_chrome_profiles() -> list[dict]:
    """Return all discovered Chrome profiles with account metadata.

    Each dict has:
        profile_dir (str)  — folder name, e.g. "Default" or "Profile 1"
        user_data_dir (str) — full path to Chrome's User Data folder
        display_name (str) — profile display name from Chrome settings
        email (str)        — signed-in Google account, or "" if none
        avatar_color (str) — hex color for the profile avatar chip
        is_default (bool)
    """
    profiles: list[dict] = []
    avatar_palette = [
        "#4285f4", "#ea4335", "#fbbc04", "#34a853",
        "#ff6d00", "#8e24aa", "#00acc1", "#e91e63",
    ]

    for user_data_dir in _CHROME_DIRS:
        if not user_data_dir.exists():
            continue

        local_state_path = user_data_dir / "Local State"
        local_state: dict = {}
        if local_state_path.exists():
            try:
                local_state = json.loads(local_state_path.read_bytes())
            except Exception as exc:
                log.warning("Could not parse Local State: %s", exc)

        profile_info_cache: dict = (
            local_state.get("profile", {}).get("info_cache", {})
        )

        for entry in user_data_dir.iterdir():
            if entry.name != "Default" and not entry.name.startswith("Profile"):
                continue
            if not (entry / "Preferences").exists():
                continue

            prefs = _read_profile_prefs(entry)
            account_info = prefs.get("account_info", [])
            email = ""
            if account_info and isinstance(account_info, list):
                email = account_info[0].get("email", "")

            cache_entry = profile_info_cache.get(entry.name, {})
            display_name = (
                cache_entry.get("name")
                or prefs.get("profile", {}).get("name", "")
                or entry.name
            )

            idx = len(profiles)
            profiles.append({
                "profile_dir": entry.name,
                "user_data_dir": str(user_data_dir),
                "display_name": display_name,
                "email": email,
                "avatar_color": avatar_palette[idx % len(avatar_palette)],
                "is_default": entry.name == "Default",
            })

    profiles.sort(key=lambda p: (not p["is_default"], p["profile_dir"]))
    log.info("Discovered %d Chrome profile(s)", len(profiles))
    return profiles


def launch_profile(
    profile_dir: str,
    user_data_dir: str,
    url: Optional[str] = None,
) -> bool:
    """Open Chrome with the given profile.  Returns True if process started."""
    chrome = _find_chrome_exe()
    if not chrome:
        log.error("Chrome executable not found")
        return False

    args = [
        str(chrome),
        f"--profile-directory={profile_dir}",
        f"--user-data-dir={user_data_dir}",
    ]
    if url:
        args.append(url)

    try:
        subprocess.Popen(args)
        log.info("Launched Chrome profile=%s url=%s", profile_dir, url)
        return True
    except OSError as exc:
        log.error("Failed to launch Chrome: %s", exc)
        return False


def get_account_map() -> dict[str, str]:
    """Return {email: profile_dir} for all signed-in profiles (non-empty email)."""
    return {
        p["email"]: p["profile_dir"]
        for p in get_chrome_profiles()
        if p["email"]
    }
