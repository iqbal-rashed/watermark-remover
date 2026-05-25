<p align="center">
  <img src="resources/logo-dark.png" width="96" height="96" alt="Watermark Remover" />
</p>

<h1 align="center">Watermark Remover</h1>

<p align="center">
  AI-powered watermark removal for images and videos.<br/>
  Desktop app · Browser UI · CLI
</p>

<p align="center">
  <a href="https://github.com/iqbal-rashed/watermark-remover/releases/latest">
    <img src="https://img.shields.io/github/v/release/iqbal-rashed/watermark-remover?style=flat-square&label=latest&color=3b82f6" alt="Latest Release" />
  </a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-6366f1?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" alt="License" />
</p>

<br/>

<p align="center">
  <a href="https://github.com/iqbal-rashed/watermark-remover/releases/latest/download/watermark-remover-windows.exe">
    <img src="https://img.shields.io/badge/Download%20for%20Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Download for Windows" />
  </a>
  &nbsp;
  <a href="https://github.com/iqbal-rashed/watermark-remover/releases/latest/download/watermark-remover-macos.dmg">
    <img src="https://img.shields.io/badge/Download%20for%20macOS-000000?style=for-the-badge&logo=apple&logoColor=white" alt="Download for macOS" />
  </a>
  &nbsp;
  <a href="https://github.com/iqbal-rashed/watermark-remover/releases/latest/download/watermark-remover-linux">
    <img src="https://img.shields.io/badge/Download%20for%20Linux-E95420?style=for-the-badge&logo=linux&logoColor=white" alt="Download for Linux" />
  </a>
</p>

<p align="center">
  <a href="https://github.com/iqbal-rashed/watermark-remover/releases">All releases →</a>
</p>

---

## Features

| | |
|---|---|
| **AI Auto-Detection** | Florence-2 (Microsoft) finds the watermark region automatically |
| **High-Quality Inpainting** | LaMa deep learning model fills the removed area naturally |
| **Desktop App** | Native window with a modern React UI — no browser needed |
| **Browser UI** | Run the server and open in any browser |
| **CLI** | Beautiful terminal interface with Rich progress bars |
| **GPU Acceleration** | CUDA support for faster processing on NVIDIA GPUs |
| **Video Support** | Removes watermarks from MP4, AVI frame by frame |
| **Formats** | PNG, WEBP, JPG, MP4, AVI |
| **Auto-Update** | Checks GitHub releases and notifies you of new versions |

---

## How It Works

1. **Upload** an image or video
2. **Detect** — click Auto-Detect and Florence-2 finds the watermark, or draw a box manually
3. **Remove** — LaMa inpaints the region with AI-generated content
4. **Download** the clean result

On first launch, the app guides you through a one-time setup to download PyTorch and the Florence-2 model (~3 GB, cached in `~/.cache/huggingface/`). Subsequent launches start instantly.

---

## Quick Start (Development)

**Requirements:** Python 3.11+, Node 20+

```bash
git clone https://github.com/iqbal-rashed/watermark-remover
cd watermark-remover

# Install Python deps
pip install -r requirements.txt

# Build and run the desktop app
cd frontend && yarn install && yarn build && cd ..
python desktop.py
```

**Run backend + frontend separately (hot reload):**

```bash
# Terminal 1 — backend
python -m app.server --reload

# Terminal 2 — frontend
cd frontend && yarn dev
```

Then open `http://localhost:5173` in your browser.

---

## CLI

```bash
# First-time setup
python cli.py setup

# Remove watermark (auto-detect)
python cli.py remove input.jpg output/ --auto

# Remove watermark (manual region)
python cli.py remove input.jpg output/ --mask-box "120,80,400,120"

# Video
python cli.py remove input.mp4 output/ --auto --frame-step 2
```

**All options:**

```
python cli.py remove INPUT OUTPUT [options]

  --auto                   Auto-detect watermark with Florence-2
  --mask-box X1,Y1,X2,Y2  Manual watermark region
  --transparent            Make region transparent (PNG only)
  --force-format           PNG | WEBP | JPG | MP4 | AVI
  --frame-step N           Process every Nth frame (video, default: 1)
  --target-fps F           Output FPS (0 = keep original)
  --max-bbox-percent F     Max detection box size % (default: 10)
```

---

## Build from Source

```bash
pip install pyinstaller
python build/build.py
# Output: dist/watermark-remover[.exe]
```

Produces a single-file executable with the frontend bundled. ML models are downloaded at runtime on first launch (not bundled, keeping the exe small).

---

## Project Structure

```
watermark-remover/
├── app/
│   ├── core/
│   │   ├── detector.py        # Florence-2 watermark detection
│   │   ├── remover.py         # LaMa / OpenCV inpainting
│   │   └── image_video.py     # Processing pipeline
│   ├── server.py              # FastAPI backend
│   ├── setup_manager.py       # First-run model download wizard
│   └── updater.py             # GitHub releases auto-updater
├── frontend/                  # React + TypeScript + Tailwind
├── build/
│   ├── watermark_remover.spec # PyInstaller config
│   └── build.py               # Build helper
├── .github/workflows/
│   └── release.yml            # CI: build & release all platforms
├── resources/                 # App icons
├── desktop.py                 # Desktop entry point (pywebview)
├── cli.py                     # CLI entry point (Rich)
└── version.json
```

---

## Releasing

Push a version tag — GitHub Actions builds Windows, macOS, and Linux automatically and creates a GitHub Release with all artifacts attached.

```bash
# Bump version.json first, then:
git tag v1.0.1 && git push origin v1.0.1
```

---

## License

MIT — see [LICENSE](LICENSE)
