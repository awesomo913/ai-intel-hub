"""Cross-platform path utilities and system detection."""

import platform
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PlatformInfo:
    os_name: str = ""
    os_version: str = ""
    architecture: str = ""
    machine: str = ""
    python_version: str = ""
    screen_width: int = 0
    screen_height: int = 0
    total_ram_mb: int = 0
    available_disk_gb: float = 0.0


def detect_platform() -> PlatformInfo:
    info = PlatformInfo(
        os_name=platform.system(),
        os_version=platform.version(),
        architecture=platform.architecture()[0],
        machine=platform.machine(),
        python_version=platform.python_version(),
    )
    try:
        import psutil
        info.total_ram_mb = psutil.virtual_memory().total // (1024 * 1024)
    except ImportError:
        pass
    try:
        disk = shutil.disk_usage(Path.home())
        info.available_disk_gb = round(disk.free / (1024 ** 3), 1)
    except Exception:
        pass
    return info


def get_app_dir() -> Path:
    """Get platform-appropriate app data directory."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    app_dir = base / "AIIntelHub"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_dir() -> Path:
    return get_app_dir()


def get_data_dir() -> Path:
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_export_dir() -> Path:
    export_dir = get_app_dir() / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def get_desktop_path() -> Path:
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop
    return Path.home()
