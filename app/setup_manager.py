"""Manages first-run setup: GPU detection, package installation, model downloads."""
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Callable, Generator, Optional

from loguru import logger

APP_DATA = Path.home() / ".watermark-remover"
PACKAGES_DIR = APP_DATA / "packages"
CONFIG_FILE = APP_DATA / "setup.json"

# HuggingFace default cache
HF_CACHE = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"

FLORENCE_MODEL_ID = "microsoft/Florence-2-large"
LAMA_MODEL_ID = "lama"  # iopaint internal name


def get_app_data() -> Path:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    return APP_DATA


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    APP_DATA.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def is_setup_complete() -> bool:
    return _load_config().get("complete", False)


def _add_packages_to_path():
    pkg_path = str(PACKAGES_DIR)
    if pkg_path not in sys.path:
        sys.path.append(pkg_path)

    if sys.platform != "win32":
        return

    # Build the list of directories that contain native DLLs.
    dll_dirs = [PACKAGES_DIR]

    # numpy 2.x ships DLLs in numpy.libs/ at the packages root;
    # numpy 1.x ships them inside numpy/core/.
    for candidate in [PACKAGES_DIR / "numpy.libs", PACKAGES_DIR / "numpy" / "core"]:
        if candidate.exists():
            dll_dirs.append(candidate)

    # cv2's config.py hardcodes a cmake build path (../../x64/vc17/bin) that
    # never exists in a pip wheel installation, so cv2's own bootstrap fails to
    # register its DLL directory. We must add cv2/ to PATH *before* cv2 is
    # imported so Windows can find opencv_videoio_ffmpeg*.dll and any other
    # bundled DLLs regardless of what cv2's bootstrap does.
    cv2_dir = PACKAGES_DIR / "cv2"
    if cv2_dir.exists():
        dll_dirs.append(cv2_dir)

    # Prepend all DLL directories to PATH — the most reliable mechanism on
    # Windows because it works even before os.add_dll_directory is called and
    # covers DLLs loaded transitively by .pyd files.
    path_entries = [str(d) for d in dll_dirs]
    existing_path = os.environ.get("PATH", "")
    os.environ["PATH"] = ";".join(path_entries) + (";" if existing_path else "") + existing_path

    # Also register with os.add_dll_directory (Python 3.8+ safe DLL search).
    for d in dll_dirs:
        try:
            os.add_dll_directory(str(d))
        except (AttributeError, OSError):
            pass


def detect_gpu() -> bool:
    """Detect NVIDIA GPU without requiring torch."""
    # Try nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
    except Exception:
        pass

    # Try torch if already available
    try:
        _add_packages_to_path()
        import torch
        return torch.cuda.is_available()
    except Exception:
        pass

    return False


def is_cv2_installed() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False


def is_torch_installed() -> bool:
    _add_packages_to_path()
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def is_transformers_installed() -> bool:
    _add_packages_to_path()
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def is_florence_downloaded() -> bool:
    """Check if Florence-2 model weights are cached locally."""
    if HF_CACHE.exists():
        for d in HF_CACHE.iterdir():
            if "florence" in d.name.lower() and "large" in d.name.lower():
                # Check that snapshots dir has content
                snapshots = d / "snapshots"
                if snapshots.exists() and any(snapshots.iterdir()):
                    return True
    return False


def get_setup_status() -> dict:
    gpu = detect_gpu()
    return {
        "complete": is_setup_complete(),
        "gpu_available": gpu,
        "cv2_installed": is_cv2_installed(),
        "torch_installed": is_torch_installed(),
        "transformers_installed": is_transformers_installed(),
        "florence_downloaded": is_florence_downloaded(),
    }


def _find_system_python() -> Optional[str]:
    """Find a usable Python interpreter (not the frozen exe)."""
    import shutil
    frozen_exe = os.path.abspath(sys.executable)
    for name in ["python3", "python", "python3.exe", "python.exe"]:
        found = shutil.which(name)
        if found and os.path.abspath(found) != frozen_exe:
            return found
    return None


def _pip_install(packages: list, index_url: Optional[str] = None) -> tuple:
    """Install packages to PACKAGES_DIR. Returns (success: bool, error: str)."""
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    # No --upgrade: we check is_*_installed() before calling, so we never need to
    # overwrite existing files. On Windows, --upgrade tries to delete locked .pyd
    # files (loaded by the running process), causing PermissionError WinError 5.
    args = ["install", "--target", str(PACKAGES_DIR)]
    if index_url:
        args += ["--index-url", index_url]
    args += packages

    if getattr(sys, "frozen", False):
        # Frozen PyInstaller exe: sys.executable is the .exe, not python.exe.
        # Find system Python via PATH so we can call pip normally via subprocess.
        python_exe = _find_system_python()
        if python_exe:
            try:
                result = subprocess.run(
                    [python_exe, "-m", "pip"] + args,
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    err = (result.stderr or result.stdout or "unknown pip error")[-800:]
                    logger.error(f"pip install error: {err}")
                    return False, err
                return True, ""
            except Exception as e:
                logger.error(f"pip install failed (system python): {e}")
                # fall through to bundled pip

        # Fallback: use pip bundled inside the PyInstaller archive
        try:
            from pip._internal.cli.main import main as pip_main  # type: ignore
            ret = pip_main(args)
            if ret != 0:
                return False, "pip exited with a non-zero code (check pip logs)"
            return True, ""
        except Exception as e:
            logger.error(f"pip install failed (frozen fallback): {e}")
            return False, str(e)
    else:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip"] + args,
                capture_output=True, text=True
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "unknown pip error")[-800:]
                logger.error(f"pip install error: {err}")
                return False, err
            return True, ""
        except Exception as e:
            logger.error(f"pip install failed: {e}")
            return False, str(e)


def run_setup(gpu: bool = False) -> Generator[dict, None, None]:
    """Generator that yields progress events during setup."""
    yield {"step": "start", "status": "Starting setup...", "progress": 0}

    # Step 1: numpy + opencv are bundled with the app — always skip
    yield {"step": "cv2", "status": "OpenCV ready", "progress": 100, "done_step": True, "skipped": True}

    # Step 2: Install torch
    if not is_torch_installed():
        yield {"step": "torch", "status": "Installing PyTorch...", "progress": 0}
        torch_pkg = ["torch", "torchvision"]

        # Try CUDA indexes newest-first (cu126 → cu124 → cu121), then CPU fallback.
        # Newer indexes support Python 3.12/3.13; older indexes may lack wheels entirely.
        if gpu:
            index_candidates = [
                ("https://download.pytorch.org/whl/cu132", "CUDA 13.2"),
                ("https://download.pytorch.org/whl/cu130", "CUDA 13.0"),
                ("https://download.pytorch.org/whl/cu126", "CUDA 12.6"),
                ("https://download.pytorch.org/whl/cpu", "CPU (CUDA unavailable for this Python)"),
            ]
        else:
            index_candidates = [
                ("https://download.pytorch.org/whl/cpu", "CPU"),
            ]

        success, err = False, ""
        for index_url, label in index_candidates:
            yield {"step": "torch", "status": f"Downloading PyTorch ({label})... this may take a few minutes", "progress": 10}
            success, err = _pip_install(torch_pkg, index_url=index_url)
            if success:
                break
            logger.warning(f"PyTorch install failed with {label}: {err[:200]}")

        if not success:
            msg = f"PyTorch installation failed: {err}" if err else "PyTorch installation failed"
            yield {"step": "torch", "status": msg, "progress": 0, "error": True}
            return
        yield {"step": "torch", "status": "PyTorch installed", "progress": 100, "done_step": True}
    else:
        yield {"step": "torch", "status": "PyTorch already installed", "progress": 100, "done_step": True, "skipped": True}

    # Step 3: Install transformers + accelerate
    if not is_transformers_installed():
        yield {"step": "transformers", "status": "Installing transformers...", "progress": 0}
        success, err = _pip_install(["transformers", "accelerate", "huggingface-hub", "hf_xet", "timm", "einops", "flash-attn"], None)
        if not success:
            # Try without flash-attn and hf_xet (compilation issues on some platforms)
            success, err = _pip_install(["transformers", "accelerate", "huggingface-hub", "timm", "einops"], None)
        if not success:
            msg = f"transformers installation failed: {err}" if err else "transformers installation failed"
            yield {"step": "transformers", "status": msg, "progress": 0, "error": True}
            return
        yield {"step": "transformers", "status": "transformers installed", "progress": 100, "done_step": True}
    else:
        yield {"step": "transformers", "status": "transformers already installed", "progress": 100, "done_step": True, "skipped": True}

    # Step 3: Download Florence-2 model
    if not is_florence_downloaded():
        yield {"step": "florence2", "status": "Downloading Florence-2 model (~3 GB)...", "progress": 0}
        _add_packages_to_path()
        try:
            from huggingface_hub import snapshot_download

            yield {"step": "florence2", "status": "Connecting to HuggingFace...", "progress": 5}
            _IGNORE = ["*.msgpack", "*.h5", "flax_model*", "tf_model*"]
            try:
                snapshot_download(FLORENCE_MODEL_ID, ignore_patterns=_IGNORE)
            except Exception as xet_err:
                if "hf_xet" in str(xet_err) or "Xet" in str(xet_err):
                    # hf_xet not available — disable Xet storage and retry with plain HTTP
                    import os as _os
                    _os.environ["HF_HUB_DISABLE_XET"] = "1"
                    snapshot_download(FLORENCE_MODEL_ID, ignore_patterns=_IGNORE)
                else:
                    raise
            yield {"step": "florence2", "status": "Florence-2 model downloaded", "progress": 100, "done_step": True}
        except Exception as e:
            yield {"step": "florence2", "status": f"Download failed: {e}", "progress": 0, "error": True}
            return
    else:
        yield {"step": "florence2", "status": "Florence-2 already downloaded", "progress": 100, "done_step": True, "skipped": True}

    # Mark setup complete
    config = _load_config()
    config["complete"] = True
    config["gpu"] = gpu
    _save_config(config)

    yield {"step": "done", "status": "Setup complete!", "progress": 100, "all_done": True}
