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
        sys.path.insert(0, pkg_path)


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
        "torch_installed": is_torch_installed(),
        "transformers_installed": is_transformers_installed(),
        "florence_downloaded": is_florence_downloaded(),
    }


def _pip_install(packages: list, index_url: Optional[str] = None) -> bool:
    """Install packages to PACKAGES_DIR using pip."""
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    args = ["install", "--target", str(PACKAGES_DIR), "--quiet", "--upgrade"]
    if index_url:
        args += ["--index-url", index_url]
    args += packages

    if getattr(sys, "frozen", False):
        # Frozen PyInstaller app: use bundled pip
        try:
            from pip._internal.cli.main import main as pip_main  # type: ignore
            return pip_main(args) == 0
        except Exception as e:
            logger.error(f"pip install failed (frozen): {e}")
            return False
    else:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip"] + args,
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.error(f"pip install error: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            logger.error(f"pip install failed: {e}")
            return False


def run_setup(gpu: bool = False) -> Generator[dict, None, None]:
    """Generator that yields progress events during setup."""
    yield {"step": "start", "status": "Starting setup...", "progress": 0}

    # Step 1: Install torch
    if not is_torch_installed():
        yield {"step": "torch", "status": "Installing PyTorch...", "progress": 0}
        torch_pkg = ["torch", "torchvision"]
        if gpu:
            index_url = "https://download.pytorch.org/whl/cu121"
            yield {"step": "torch", "status": "Downloading PyTorch (CUDA)... this may take a few minutes", "progress": 10}
        else:
            index_url = "https://download.pytorch.org/whl/cpu"
            yield {"step": "torch", "status": "Downloading PyTorch (CPU)... this may take a few minutes", "progress": 10}

        success = _pip_install(torch_pkg, index_url=index_url)
        if not success:
            yield {"step": "torch", "status": "PyTorch installation failed", "progress": 0, "error": True}
            return
        yield {"step": "torch", "status": "PyTorch installed", "progress": 100, "done_step": True}
    else:
        yield {"step": "torch", "status": "PyTorch already installed", "progress": 100, "done_step": True, "skipped": True}

    # Step 2: Install transformers + accelerate
    if not is_transformers_installed():
        yield {"step": "transformers", "status": "Installing transformers...", "progress": 0}
        success = _pip_install(["transformers", "accelerate", "huggingface-hub", "timm", "einops", "flash-attn"], None)
        if not success:
            # Try without flash-attn (compilation issue on some platforms)
            success = _pip_install(["transformers", "accelerate", "huggingface-hub", "timm", "einops"], None)
        if not success:
            yield {"step": "transformers", "status": "transformers installation failed", "progress": 0, "error": True}
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
            from huggingface_hub import constants as hf_constants

            # Download with progress tracking via tqdm callback
            yield {"step": "florence2", "status": "Connecting to HuggingFace...", "progress": 5}
            snapshot_download(
                FLORENCE_MODEL_ID,
                ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "tf_model*"],
            )
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
