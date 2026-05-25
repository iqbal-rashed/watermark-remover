"""Auto-update system that checks GitHub releases and applies updates."""
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import requests
from loguru import logger

def _get_github_repo() -> str:
    try:
        import json
        version_file = Path(__file__).parent.parent / "version.json"
        with open(version_file) as f:
            return json.load(f).get("github_repo", "iqbal-rashed/watermark-remover")
    except Exception:
        return "iqbal-rashed/watermark-remover"

GITHUB_REPO = _get_github_repo()
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _get_current_version() -> str:
    try:
        version_file = Path(__file__).parent.parent / "version.json"
        import json
        with open(version_file) as f:
            return json.load(f)["version"]
    except Exception:
        return "0.0.0"


def _parse_version(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except Exception:
        return (0, 0, 0)


def _get_asset_name() -> str:
    """Get the expected release asset filename for this platform."""
    system = platform.system().lower()
    if system == "windows":
        return "watermark-remover-windows.exe"
    elif system == "darwin":
        return "watermark-remover-macos.dmg"
    else:
        return "watermark-remover-linux"


def check_for_updates() -> dict:
    """Check GitHub releases for a newer version. Returns update info dict."""
    current = _get_current_version()
    try:
        resp = requests.get(API_URL, timeout=10, headers={"Accept": "application/vnd.github.v3+json"})
        if resp.status_code != 200:
            return {"update_available": False, "current_version": current, "error": f"HTTP {resp.status_code}"}

        data = resp.json()
        latest_tag = data.get("tag_name", "").lstrip("v")
        latest_name = data.get("name", latest_tag)
        body = data.get("body", "")

        if _parse_version(latest_tag) > _parse_version(current):
            asset_name = _get_asset_name()
            download_url = None
            for asset in data.get("assets", []):
                if asset["name"] == asset_name:
                    download_url = asset["browser_download_url"]
                    break

            return {
                "update_available": True,
                "current_version": current,
                "latest_version": latest_tag,
                "release_name": latest_name,
                "release_notes": body,
                "download_url": download_url,
            }

        return {"update_available": False, "current_version": current, "latest_version": latest_tag}

    except requests.RequestException as e:
        logger.warning(f"Update check failed: {e}")
        return {"update_available": False, "current_version": current, "error": str(e)}


def download_update(download_url: str, progress_callback=None) -> Optional[Path]:
    """Download update to temp file, yielding progress. Returns path to downloaded file."""
    try:
        resp = requests.get(download_url, stream=True, timeout=30)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        suffix = Path(download_url).suffix or ".tmp"
        tmp_file = Path(tempfile.mktemp(suffix=suffix))

        with open(tmp_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        progress_callback(int(downloaded / total * 100), f"Downloading update... {downloaded // 1048576}MB / {total // 1048576}MB")

        return tmp_file
    except Exception as e:
        logger.error(f"Update download failed: {e}")
        return None


def apply_update(new_file: Path):
    """Replace the current executable with the downloaded update and restart."""
    system = platform.system().lower()
    current_exe = Path(sys.executable)

    if system == "windows":
        _apply_update_windows(current_exe, new_file)
    elif system == "darwin":
        _apply_update_macos(new_file)
    else:
        _apply_update_linux(current_exe, new_file)


def _apply_update_windows(current_exe: Path, new_exe: Path):
    """Use a batch script to replace the exe after the process exits."""
    backup = current_exe.with_suffix(".old")
    batch_content = f"""@echo off
    ping 127.0.0.1 -n 3 > nul
    del "{backup}" 2>nul
    move "{current_exe}" "{backup}"
    move "{new_exe}" "{current_exe}"
    start "" "{current_exe}"
    del "%~f0"
    """
    batch_path = Path(tempfile.mktemp(suffix=".bat"))
    batch_path.write_text(batch_content)
    subprocess.Popen([str(batch_path)], shell=True, close_fds=True,
                     creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
    sys.exit(0)


def _apply_update_macos(dmg_path: Path):
    """Mount DMG and copy .app to Applications."""
    mount_point = Path(tempfile.mkdtemp())
    try:
        subprocess.run(["hdiutil", "attach", str(dmg_path), "-mountpoint", str(mount_point)], check=True)
        app_files = list(mount_point.glob("*.app"))
        if app_files:
            app = app_files[0]
            dest = Path("/Applications") / app.name
            subprocess.run(["cp", "-R", str(app), str(dest)], check=True)
        subprocess.run(["hdiutil", "detach", str(mount_point)], check=False)
    except Exception as e:
        logger.error(f"macOS update failed: {e}")
    finally:
        subprocess.run(["open", "-a", "Watermark Remover"], check=False)
        sys.exit(0)


def _apply_update_linux(current_exe: Path, new_file: Path):
    """Replace the binary directly."""
    backup = current_exe.with_suffix(".old")
    try:
        current_exe.rename(backup)
        new_file.rename(current_exe)
        os.chmod(current_exe, 0o755)
        subprocess.Popen([str(current_exe)], close_fds=True)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Linux update failed: {e}")
        if backup.exists():
            backup.rename(current_exe)
