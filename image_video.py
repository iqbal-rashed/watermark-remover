import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union
import static_ffmpeg
import cv2
import numpy as np
from sympy import Float
import torch
from PIL import Image
from loguru import logger
from remover import MaskBox, remove_watermark, ensure_mask_box

static_ffmpeg.add_paths()

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".mpg",
    ".mpeg",
    ".wmv",
    ".webm",
    ".m4v",
}


def _auto_detect_mask_box(image: Image.Image,max_bbox_percent:Optional[Float]) -> MaskBox:
    if image.mode != "RGB":
        preview = image.convert("RGB")
    else:
        preview = image
    try:
        from detector import watermark_detector
    except Exception as exc:  # pragma: no cover - heavy dependency path
        raise RuntimeError(f"Auto mask detection unavailable: {exc}") from exc

    detected_box = watermark_detector(preview,max_bbox_percent=max_bbox_percent or 10)
    if detected_box == (0, 0, 0, 0):
        raise RuntimeError("Detector could not identify a watermark region.")

    logger.info("Auto-detected mask box %s", detected_box)
    return ensure_mask_box(detected_box)


def process_image_or_video(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    mask_box: Optional[Union[MaskBox, str]],
    transparent: bool = False,
    force_format: Optional[str] = None,
    frame_step: int = 1,
    target_fps: float = 0.0,
) -> Path:
    if frame_step < 1:
        raise ValueError("frame_step must be >= 1")
    if target_fps < 0:
        raise ValueError("target_fps must be >= 0")

    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_dir():
        if output_path.suffix:
            output_path = output_path.with_suffix("")
        output_path.mkdir(parents=True, exist_ok=True)
        for entry in sorted(input_path.iterdir()):
            if entry.is_dir():
                process_image_or_video(
                    entry,
                    output_path / entry.name,
                    mask_box=mask_box,
                    transparent=transparent,
                    force_format=force_format,
                    frame_step=frame_step,
                    target_fps=target_fps,
                )
            elif _is_image_file(entry):
                _process_single_image(
                    entry,
                    output_path,
                    mask_box=mask_box,
                    transparent=transparent,
                    force_format=force_format,
                )
            elif _is_video_file(entry):
                _process_single_video(
                    entry,
                    output_path,
                    mask_box=mask_box,
                    transparent=transparent,
                    force_format=force_format,
                    frame_step=frame_step,
                    target_fps=target_fps,
                )
            else:
                logger.debug("Skipping unsupported file '{}'.", entry)
        return output_path

    if _is_image_file(input_path):
        return _process_single_image(
            input_path,
            output_path,
            mask_box=mask_box,
            transparent=transparent,
            force_format=force_format,
        )

    if _is_video_file(input_path):
        return _process_single_video(
            input_path,
            output_path,
            mask_box=mask_box,
            transparent=transparent,
            force_format=force_format,
            frame_step=frame_step,
            target_fps=target_fps,
        )

    raise ValueError(f"Unsupported input type for '{input_path}'. Only image/video files or directories are allowed.")


def _process_single_image(
    input_file: Path,
    output_path: Path,
    *,
    mask_box: Optional[Union[MaskBox, str]],
    transparent: bool,
    force_format: Optional[str],
    max_bbox_percent:Optional[Float]
) -> Path:
    with Image.open(input_file) as image:
        resolved_mask_box = ensure_mask_box(mask_box) if mask_box is not None else _auto_detect_mask_box(image,max_bbox_percent=max_bbox_percent or 10)
        result_image, output_format = remove_watermark(
            image=image,
            transparent=transparent,
            force_format=force_format,
            mask_box=resolved_mask_box,
        )

    final_path = _resolve_image_output_path(input_file, output_path, output_format)
    result_image.save(final_path, format=output_format)
    logger.success("Processed image '{}' -> '{}'", input_file, final_path)
    return final_path, resolved_mask_box


def _resolve_image_output_path(input_file: Path, output_path: Path, output_format: str) -> Path:
    ext = f".{output_format.lower()}"
    if (output_path.exists() and output_path.is_dir()) or not output_path.suffix:
        output_dir = output_path if output_path.suffix else output_path
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{input_file.stem}_no_watermark{ext}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() != ext:
        return output_path.with_suffix(ext)
    return output_path


def _is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def _is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def _process_single_video(
    input_file: Path,
    output_path: Path,
    *,
    mask_box: Optional[Union[MaskBox, str]],
    transparent: bool,
    force_format: Optional[str],
    frame_step: int,
    target_fps: float,
    max_bbox_percent:Optional[Float] = 10
) -> Path:
    if frame_step < 1:
        raise ValueError("frame_step must be >= 1")
    if target_fps < 0:
        raise ValueError("target_fps must be >= 0")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    # LaMa will be loaded lazily inside remover if available; otherwise OpenCV fallback is used.
    model_manager = None

    cap = cv2.VideoCapture(str(input_file))
    if not cap.isOpened():
        raise RuntimeError(f"Error opening video file: {input_file}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    if fps <= 0:
        logger.warning("Falling back to 30 FPS because source FPS could not be determined.")
        fps = 30.0
    fps_out = target_fps if target_fps > 0 else fps
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    valid_video_formats = {"MP4", "AVI"}
    if force_format:
        output_format = force_format.upper()
        if output_format not in valid_video_formats:
            raise ValueError(
                f"Unsupported force_format '{force_format}'. Expected one of {sorted(valid_video_formats)}"
            )
    else:
        ext = input_file.suffix.lower().lstrip(".")
        candidate = ext.upper() if ext else ""
        output_format = candidate if candidate in valid_video_formats else "MP4"

    if output_path.is_dir() or output_path.suffix == "":
        output_path.mkdir(parents=True, exist_ok=True)
        output_file = output_path / f"{input_file.stem}_no_watermark.{output_format.lower()}"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if force_format:
            output_file = output_path.with_suffix(f".{output_format.lower()}")
        else:
            suffix = output_path.suffix.lower()
            if suffix and suffix.lstrip(".").upper() in valid_video_formats:
                output_file = output_path
            else:
                output_file = output_path.with_suffix(f".{output_format.lower()}")

    temp_dir = Path(tempfile.mkdtemp())
    temp_video_path = temp_dir / f"temp_no_audio.{output_format.lower()}"

    if output_format == "MP4":
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    else:
        fourcc = cv2.VideoWriter_fourcc(*"XVID")

    out = cv2.VideoWriter(str(temp_video_path), fourcc, fps_out, (width, height))

    try:
        pending_frame = None
        if mask_box is None:
            ok_preview, preview_frame = cap.read()
            if not ok_preview or preview_frame is None:
                raise RuntimeError("Unable to read first frame for auto mask detection.")
            preview_image = Image.fromarray(cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB))
            resolved_mask_box = _auto_detect_mask_box(preview_image,max_bbox_percent)
            pending_frame = preview_frame
        else:
            resolved_mask_box = ensure_mask_box(mask_box)

        frame_idx = 0
        while cap.isOpened():
            if pending_frame is not None:
                frame = pending_frame
                pending_frame = None
            else:
                ret, frame = cap.read()
                if not ret:
                    break

            if frame_idx % frame_step != 0:
                frame_idx += 1
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # Use high-level image remover for each frame
            result_image, _ = remove_watermark(
                image=pil_image,
                transparent=transparent,
                force_format=None,
                mask_box=resolved_mask_box,
                model_manager=model_manager,
                device=device,
            )

            # Ensure RGB for video encoding (no alpha channel)
            if result_image.mode == "RGBA":
                background = Image.new("RGB", result_image.size, (255, 255, 255))
                background.paste(result_image, mask=result_image.split()[3])
                result_image = background
            elif result_image.mode != "RGB":
                result_image = result_image.convert("RGB")

            frame_result = cv2.cvtColor(np.array(result_image), cv2.COLOR_RGB2BGR)
            out.write(frame_result)

            frame_idx += 1
    finally:
        cap.release()
        out.release()

    try:
        logger.info("Merging processed video with original audio using ffmpeg (if available)...")
        try:
            subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("FFmpeg is not available. The processed video will not include audio.")
            shutil.copy(str(temp_video_path), str(output_file))
        else:
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(temp_video_path),
                "-i",
                str(input_file),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
                str(output_file),
            ]
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("Audio merge completed successfully.")
    except Exception as exc:
        logger.error(f"Error while merging audio: {exc}")
        shutil.copy(str(temp_video_path), str(output_file))
    finally:
        try:
            if temp_video_path.exists():
                temp_video_path.unlink()
            temp_dir.rmdir()
        except OSError:
            pass

    logger.info(f"input_path:{input_file}, output_path:{output_file}")
    return output_file



