"""FastAPI backend server for the desktop and web app."""
import asyncio
import io
import json
import mimetypes
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

# Must run before any core module import so that numpy/cv2/torch are findable
# on all code paths — not just the guarded endpoint handlers.
from app.setup_manager import _add_packages_to_path
_add_packages_to_path()

TEMP_DIR = Path(tempfile.gettempdir()) / "watermark-remover-server"
TEMP_DIR.mkdir(exist_ok=True)

# file_id -> {"input": path, "output": path, "name": str, "type": "image"|"video"}
_file_registry: dict = {}
_executor = ThreadPoolExecutor(max_workers=2)

app = FastAPI(title="Watermark Remover API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────── Setup endpoints ────────────────────────────────

@app.get("/api/setup/status")
async def setup_status():
    from app.setup_manager import get_setup_status
    return get_setup_status()


@app.get("/api/setup/install")
async def setup_install(gpu: bool = Query(False)):
    """SSE stream for installation progress. Use GET so EventSource can connect."""
    from app.setup_manager import run_setup

    async def generate():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                for event in run_setup(gpu=gpu):
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put({"error": True, "status": str(e)}), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel

        loop.run_in_executor(_executor, _run)

        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("all_done") or event.get("error"):
                break

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─────────────────────────── File endpoints ─────────────────────────────────

@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = TEMP_DIR / file_id

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    content_type = file.content_type or ""
    file_type = "video" if content_type.startswith("video/") else "image"

    _file_registry[file_id] = {
        "input": str(file_path),
        "output": None,
        "name": file.filename or "upload",
        "type": file_type,
    }
    return {"file_id": file_id, "type": file_type, "name": file.filename}


@app.get("/api/files/download/{file_id}")
async def download_file(file_id: str):
    info = _file_registry.get(file_id)
    if not info or not info.get("output"):
        raise HTTPException(status_code=404, detail="File not found")
    output_path = Path(info["output"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file missing")
    media_type, _ = mimetypes.guess_type(str(output_path))
    return FileResponse(str(output_path), media_type=media_type or "application/octet-stream",
                        filename=output_path.name)


@app.get("/api/files/preview/{file_id}")
async def preview_file(file_id: str):
    info = _file_registry.get(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = Path(info["input"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Input file missing")
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(str(file_path), media_type=media_type or "application/octet-stream")


# ─────────────────────────── Detection endpoint ─────────────────────────────

@app.get("/api/detect")
async def detect_watermark(file_id: str = Query(...), max_bbox_percent: float = Query(10.0)):
    info = _file_registry.get(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")

    async def generate():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                yield_event = lambda e: asyncio.run_coroutine_threadsafe(queue.put(e), loop)
                yield_event({"status": "Loading model...", "progress": 5})

                from app.core.detector import watermark_detector
                import torch
                from PIL import Image

                input_path = Path(info["input"])
                file_type = info["type"]

                if file_type == "video":
                    import cv2
                    cap = cv2.VideoCapture(str(input_path))
                    ok, frame = cap.read()
                    cap.release()
                    if not ok:
                        raise RuntimeError("Cannot read video frame")
                    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                else:
                    image = Image.open(input_path).convert("RGB")

                yield_event({"status": "Running detection...", "progress": 40})
                box = watermark_detector(image, max_bbox_percent=max_bbox_percent)
                yield_event({"status": "Done", "progress": 100, "box": list(box)})
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put({"error": True, "status": str(e)}), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(_executor, _run)

        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("box") is not None or event.get("error"):
                break

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─────────────────────────── Process endpoint ───────────────────────────────

@app.get("/api/process")
async def process_file(
    file_id: str = Query(...),
    mask_box: str = Query(...),
    transparent: bool = Query(False),
    force_format: Optional[str] = Query(None),
    frame_step: int = Query(1),
    target_fps: float = Query(0.0),
    max_bbox_percent: float = Query(10.0),
):
    info = _file_registry.get(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")

    async def generate():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            emit = lambda e: asyncio.run_coroutine_threadsafe(queue.put(e), loop)
            try:
                emit({"status": "Starting...", "progress": 0})

                from app.core.image_video import process_image_or_video
                from app.core.remover import parse_mask_box

                input_path = Path(info["input"])
                resolved_box = parse_mask_box(mask_box)

                # Determine output path
                ext_map = {"PNG": ".png", "WEBP": ".webp", "JPEG": ".jpg", "JPG": ".jpg",
                           "MP4": ".mp4", "AVI": ".avi"}
                out_ext = ext_map.get((force_format or "PNG").upper(), ".png")
                out_name = Path(info["name"]).stem + "_no_watermark" + out_ext
                output_path = TEMP_DIR / (file_id + "_out" + out_ext)

                def progress_cb(pct, status):
                    emit({"status": status, "progress": pct})

                result_path = process_image_or_video(
                    input_path,
                    output_path,
                    mask_box=resolved_box,
                    transparent=transparent,
                    force_format=force_format,
                    frame_step=frame_step,
                    target_fps=target_fps,
                    max_bbox_percent=max_bbox_percent,
                    progress_callback=progress_cb,
                )

                # Register output
                output_id = file_id + "_out"
                _file_registry[output_id] = {
                    "input": str(input_path),
                    "output": str(result_path),
                    "name": out_name,
                    "type": info["type"],
                }
                info["output"] = str(result_path)

                emit({"status": "Done", "progress": 100, "output_id": output_id, "filename": out_name})
            except Exception as e:
                logger.exception("Processing error")
                emit({"error": True, "status": str(e), "progress": 0})
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(_executor, _run)

        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("output_id") or event.get("error"):
                break

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─────────────────────────── Update endpoints ───────────────────────────────

@app.get("/api/update/check")
async def check_update():
    try:
        from app.updater import check_for_updates
        return check_for_updates()
    except Exception as e:
        return {"update_available": False, "error": str(e)}


@app.get("/api/update/download")
async def download_update_stream(download_url: str = Query(...)):
    from app.updater import download_update, apply_update

    async def generate():
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            emit = lambda e: asyncio.run_coroutine_threadsafe(queue.put(e), loop)

            def progress_cb(pct, msg):
                emit({"progress": pct, "status": msg})

            new_file = download_update(download_url, progress_callback=progress_cb)
            if new_file:
                emit({"progress": 100, "status": "Applying update...", "ready": True, "path": str(new_file)})
            else:
                emit({"error": True, "status": "Download failed"})
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(_executor, _run)

        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("ready") or event.get("error"):
                break

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/update/apply")
async def apply_update_endpoint(path: str = Query(...)):
    from app.updater import apply_update
    from pathlib import Path as P
    # Apply update in background (will restart the app)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, apply_update, P(path))
    return {"status": "Applying update, app will restart..."}


# ─────────────────────────── Logs endpoint ──────────────────────────────────

@app.get("/api/logs")
async def get_logs(mode: str = "desktop", lines: int = 200):
    """Return the last N lines of a log file."""
    from app.logger import get_log_file
    log_file = get_log_file(mode)
    if not log_file.exists():
        return {"lines": [], "file": str(log_file), "exists": False}
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        return {"lines": all_lines[-lines:], "file": str(log_file), "exists": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────── Static frontend ────────────────────────────────

def _mount_frontend():
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
        logger.info(f"Serving frontend from {frontend_dist}")
    else:
        logger.warning(f"Frontend dist not found at {frontend_dist}. Run 'npm run build' in frontend/")


_mount_frontend()


def create_app(log_mode: str = "desktop") -> FastAPI:
    """Return the FastAPI instance, ensuring logging is configured."""
    from app.logger import setup_logging
    setup_logging(mode=log_mode)
    return app


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the Watermark Remover server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7842, help="Port to bind (default: 7842)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    from app.logger import setup_logging
    setup_logging(mode="server")

    logger.info(f"Starting server on http://{args.host}:{args.port}")
    uvicorn.run(
        "app.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="warning",
        access_log=False,
    )
