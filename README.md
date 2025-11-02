# Watermark Remover

A Python toolkit that detects and removes watermark regions from images and videos. It ships with both a Streamlit web UI and a Click-based CLI, supports batch processing, and can inpaint the masked region or make it transparent.

## Features

- **Streamlit UI** for drag-and-drop watermark removal.
- **CLI** for scripted workflows and directory recursion.
- **Automatic mask detection** powered by Florence-2 (optional manual masks).
- **Image & video support** with configurable output formats, FPS, and frame skipping.
- **Transparent PNG export** or inpainting via OpenCV / LaMa (if installed).
- **Structured logging** under `uploads/logs/app.log`.

## Quick Start

### 1. Environment

```pwsh
# Create and activate a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install core dependencies
pip install -r requirements.txt
```

Optional extras:

- `pip install iopaint` enables LaMa-based inpainting for higher quality results.
- `pip install torch --index-url https://download.pytorch.org/whl/cpu` (or the CUDA wheel) if PyTorch is not already present.

### 2. Florence-2 model download

Automatic mask detection uses the Hugging Face model `microsoft/Florence-2-large`. The first run triggers a download (~3 GB). Ensure you have:

```pwsh
pip install "transformers>=4.49" accelerate safetensors
```

If you lack a GPU, the code automatically falls back to CPU.

### 3. Launch the Streamlit App

```pwsh
streamlit run main.py
```

1. Choose _Image_ or _Video_.
2. Upload your media.
3. Leave **Auto-detect watermark** enabled to run Florence-2, or provide coordinates like `120,430,980,540`.
4. Select optional settings (transparent PNG, output format, FPS, frame step).
5. Click **Process**. Outputs land in `uploads/`.

### 4. CLI Usage

```pwsh
python cli.py INPUT_PATH OUTPUT_PATH [options]
```

Key flags:

- `--auto` — auto-detect the watermark box.
- `--mask-box "x1,y1,x2,y2"` — manual rectangle.
- `--transparent` — produce PNG with transparent region.
- `--force-format PNG|WEBP|JPG|MP4|AVI` — override output format.
- `--frame-step N` — process every Nth frame (videos).
- `--target-fps F` — retime output video (0 keeps original).

Examples:

```pwsh
# Remove watermark from a single image
python cli.py example/watermark.jpg uploads/cleaned/ --auto

# Batch process a directory with manual mask
python cli.py example/ uploads/batch/ --mask-box "125,410,980,545"

# Process a video every 5th frame at 24 FPS
python cli.py example/promo.mp4 uploads/promo_clean.mp4 --auto --frame-step 5 --target-fps 24
```

## Project Structure

- `main.py` — Streamlit UI entry point.
- `cli.py` — Command line interface.
- `image_video.py` — Core image/video processing pipeline.
- `detector.py` — Florence-2 binding for watermark detection.
- `remover.py` — Inpainting, transparency, and mask utilities.
- `uploads/` — Default output directory (auto-created).

## Logs & Troubleshooting

- If automatic detection fails, provide manual coordinates via the UI or CLI.
- For FFmpeg audio muxing, ensure `ffmpeg` is on your `PATH`. Without it, the processed video remains mute.
- LaMa inpainting requires `iopaint` and a CUDA-capable GPU for best performance; otherwise, OpenCV Telea is used.

## Development Notes

- Source code is formatted using standard Python style (PEP 8).
- Unit tests are not bundled; consider adding regression media and golden outputs before major changes.
- Contributions should avoid committing large media files; store samples under `example/` if needed.

## License

This project inherits the original repository's license. Please consult the upstream repository for details.
