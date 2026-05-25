# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Watermark Remover desktop app.

Build command:
  pyinstaller build/watermark_remover.spec --distpath dist --workpath build/work

NOTE: Frontend must be built first:
  cd frontend && npm install && npm run build
"""
import sys
import os
from pathlib import Path

ROOT = Path(SPECPATH).parent
FRONTEND_DIST = ROOT / "frontend" / "dist"
RESOURCES = ROOT / "resources"

block_cipher = None

# ── Collect data files ────────────────────────────────────────────────────────

datas = [
    (str(ROOT / "version.json"), "."),
    (str(ROOT / "app"), "app"),
]

if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
else:
    print("WARNING: frontend/dist not found. Run 'npm run build' in frontend/ first.")

if RESOURCES.exists():
    datas.append((str(RESOURCES), "resources"))

# ── Analysis ──────────────────────────────────────────────────────────────────

a = Analysis(
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # FastAPI / uvicorn
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "fastapi.staticfiles",
        "starlette.staticfiles",
        "starlette.routing",
        "python_multipart",
        # webview
        "webview",
        "webview.platforms",
        # pip (for runtime installs during onboarding)
        "pip",
        "pip._internal",
        "pip._internal.cli",
        "pip._internal.cli.main",
        "pip._vendor",
        # requests
        "requests",
        "certifi",
        "charset_normalizer",
        "idna",
        "urllib3",
        # app modules
        "app",
        "app.server",
        "app.setup_manager",
        "app.updater",
        "app.core",
        "app.core.remover",
        "app.core.detector",
        "app.core.image_video",
        # loguru
        "loguru",
    ],
    hookspath=[str(ROOT / "build" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy ML packages (downloaded at runtime via onboarding)
        "torch",
        "torchvision",
        "transformers",
        "accelerate",
        "huggingface_hub",
        "timm",
        "einops",
        "safetensors",
        "tokenizers",
        "iopaint",
        "diffusers",
        "controlnet_aux",
        # Remove unused GUI/web frameworks
        "streamlit",
        "gradio",
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
        "matplotlib",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Platform-specific icon ────────────────────────────────────────────────────

if sys.platform == "win32":
    icon_path = str(RESOURCES / "icon.ico") if (RESOURCES / "icon.ico").exists() else None
elif sys.platform == "darwin":
    icon_path = str(RESOURCES / "icon.icns") if (RESOURCES / "icon.icns").exists() else None
else:
    icon_path = None

# ── EXE ───────────────────────────────────────────────────────────────────────

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="watermark-remover",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    onefile=True,           # Single file executable
)

# macOS .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Watermark Remover.app",
        icon=icon_path,
        bundle_identifier="com.watermarkremover.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
        },
    )
