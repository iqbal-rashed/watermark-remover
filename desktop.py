"""Desktop app entry point using pywebview + FastAPI backend."""
import multiprocessing
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview
from loguru import logger

PORT = 7842
HOST = "127.0.0.1"
APP_URL = f"http://{HOST}:{PORT}"

# Fixed port used only for single-instance IPC (not the web server)
_IPC_PORT = 7843


# ── Single instance ──────────────────────────────────────────────────────────

def _signal_existing_instance() -> bool:
    """Try to wake an already-running instance. Returns True if one exists."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((HOST, _IPC_PORT))
            s.sendall(b"show")
        return True
    except (ConnectionRefusedError, OSError):
        return False


def _start_instance_listener(get_window):
    """Background daemon thread: receives 'show' from duplicate instances."""
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, _IPC_PORT))
        srv.listen(5)
        srv.settimeout(1.0)
    except OSError:
        return

    while True:
        try:
            client, _ = srv.accept()
            data = client.recv(16)
            client.close()
            if data == b"show":
                win = get_window()
                if win:
                    win.show()
                    if sys.platform == "win32":
                        _win32_bring_to_front()
        except socket.timeout:
            continue
        except Exception:
            break


def _win32_bring_to_front():
    try:
        import ctypes
        hwnd = ctypes.windll.user32.FindWindowW(None, "Watermark Remover")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


# ── Server helpers ────────────────────────────────────────────────────────────

def _find_free_port(start: int = PORT) -> int:
    for p in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, p))
                return p
        except OSError:
            continue
    return start


def _wait_for_server(port: int, timeout: float = 30.0):
    import requests
    deadline = time.time() + timeout
    url = f"http://{HOST}:{port}/api/setup/status"
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _start_server(port: int):
    from app.server import create_app
    try:
        from app.setup_manager import _add_packages_to_path
        _add_packages_to_path()
    except Exception:
        pass
    uvicorn_app = create_app()
    config = uvicorn.Config(uvicorn_app, host=HOST, port=port, log_level="warning", access_log=False)
    uvicorn.Server(config).run()


# ── Icon helpers ──────────────────────────────────────────────────────────────

def _is_system_dark_mode() -> bool:
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        elif sys.platform == "darwin":
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True,
            )
            return result.stdout.strip() == "Dark"
    except Exception:
        pass
    return False


def _png_to_ico(png_path: Path) -> str | None:
    try:
        import tempfile
        from PIL import Image
        img = Image.open(png_path).convert("RGBA")
        ico_path = Path(tempfile.mktemp(suffix=".ico"))
        img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        return str(ico_path)
    except Exception as e:
        logger.warning(f"PNG→ICO conversion failed: {e}")
        return None


def _get_icon() -> str | None:
    base = Path(__file__).parent
    resources = base / "resources"
    is_dark = _is_system_dark_mode()
    logo_name = "logo-dark.png" if is_dark else "logo-light.png"

    logo_path = resources / logo_name
    if not logo_path.exists():
        logo_path = base / "frontend" / "public" / logo_name

    if logo_path.exists():
        if sys.platform == "win32":
            ico = _png_to_ico(logo_path)
            if ico:
                return ico
        else:
            return str(logo_path)

    fallback = resources / ("icon.ico" if sys.platform == "win32" else "icon.png")
    return str(fallback) if fallback.exists() else None


# ── JS API ────────────────────────────────────────────────────────────────────

class _WindowApi:
    def __init__(self):
        self._window = None

    def show_window(self):
        if self._window:
            self._window.show()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    from app.logger import setup_logging
    setup_logging(mode="desktop")

    # ── Single instance guard ────────────────────────────────────────────────
    if _signal_existing_instance():
        logger.info("Another instance is already running — signalled it to show.")
        sys.exit(0)

    import argparse
    parser = argparse.ArgumentParser(description="Start the desktop application.")
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parsed_args, _ = parser.parse_known_args()

    port = _find_free_port()
    url = "http://localhost:5173" if parsed_args.dev else f"http://{HOST}:{port}"

    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    logger.info(f"Waiting for server on port {port}...")
    if not _wait_for_server(port, timeout=30):
        logger.error("Server failed to start within 30s")
        sys.exit(1)

    icon_path = _get_icon()
    api = _WindowApi()

    window = webview.create_window(
        title="Watermark Remover",
        url=url,
        width=1280,
        height=820,
        min_size=(900, 600),
        resizable=True,
        hidden=True,
        js_api=api,
    )
    api._window = window

    threading.Thread(
        target=_start_instance_listener, args=(lambda: window,), daemon=True
    ).start()

    webview.start(
        debug=parsed_args.dev or parsed_args.debug,
        icon=icon_path,
        http_server=False,
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
