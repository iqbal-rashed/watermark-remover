import importlib
from pathlib import Path
from typing import Optional, Union

from PIL import Image
from loguru import logger

from remover import MaskBox, remove_watermark


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
) -> Path:
    if mask_box is None:
        raise ValueError("mask_box is required to locate the watermark region for image processing.")

    with Image.open(input_file) as image:
        result_image, output_format = remove_watermark(
            image=image,
            transparent=transparent,
            force_format=force_format,
            mask_box=mask_box,
        )

    final_path = _resolve_image_output_path(input_file, output_path, output_format)
    result_image.save(final_path, format=output_format)
    logger.success("Processed image '{}' -> '{}'", input_file, final_path)
    return final_path


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
) -> Path:
    video_module = importlib.import_module("video")
    return video_module.remove_watermark_from_video(
        input_file,
        output_path,
        mask_box=mask_box,
        transparent=transparent,
        force_format=force_format,
        frame_step=frame_step,
        target_fps=target_fps,
    )



