import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from PIL import Image
import cv2

from image_video import process_image_or_video, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from remover import parse_mask_box, MaskBox


uploads_dir = Path("uploads")
logs_dir = uploads_dir / "logs"
uploads_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)
log_file = logs_dir / "app.log"
try:
	logger.add(str(log_file), rotation="1 MB", enqueue=False)
except Exception:
	pass


def _is_image(path: Path) -> bool:
	return path.suffix.lower() in IMAGE_EXTENSIONS


def _is_video(path: Path) -> bool:
	return path.suffix.lower() in VIDEO_EXTENSIONS


def _extract_preview_from_video(path: Path) -> Image.Image:
	cap = cv2.VideoCapture(str(path))
	try:
		ok, frame = cap.read()
		if not ok or frame is None:
			raise RuntimeError("Unable to read the first frame from the video.")
		frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		return Image.fromarray(frame_rgb)
	finally:
		cap.release()


def _resolve_mask_box(preview_image: Optional[Image.Image], manual_mask_text: Optional[str], auto: bool) -> MaskBox:
	if manual_mask_text:
		return parse_mask_box(manual_mask_text)
	if auto:
		if preview_image is None:
			raise click.ClickException("Auto-detection requested but preview image unavailable.")
		try:
			from detector import watermark_detector  # lazy import
		except Exception as e:
			raise click.ClickException(
				f"Auto-detection unavailable due to dependency error: {e}. Provide --mask-box instead."
			)
		box = watermark_detector(preview_image)
		if box == (0, 0, 0, 0):
			raise click.ClickException("Detector could not identify a watermark region. Provide --mask-box manually.")
		return box
	raise click.ClickException("Provide --mask-box or use --auto.")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.argument("output_path", type=click.Path(path_type=Path))
@click.option("--auto", is_flag=True, help="Auto-detect watermark region using Florence (requires transformers/hf hub).")
@click.option("--mask-box", default=None, help="Manual mask as 'x1,y1,x2,y2'.")
@click.option("--max-bbox-percent", default=10.0, help="Maximum percentage of the image that a bounding box can cover.")
@click.option("--transparent", is_flag=True, help="Make region transparent (images -> PNG). For videos, transparency is composited on white.")
@click.option(
	"--force-format",
	type=click.Choice(["PNG", "WEBP", "JPG", "MP4", "AVI"], case_sensitive=False),
	default=None,
	help="Force output format.",
)
@click.option("--frame-step", type=int, default=1, show_default=True, help="Process every Nth frame for videos.")
@click.option("--target-fps", type=float, default=0.0, show_default=True, help="Target FPS for videos (0 = keep input).")
def main(
	input_path: Path,
	output_path: Path,
	auto: bool,
	mask_box: Optional[str],
	transparent: bool,
	force_format: Optional[str],
	frame_step: int,
	target_fps: float,
  	max_bbox_percent: float
):
	"""Process IMAGE/VIDEO/ DIRECTORY.

	INPUT_PATH can be an image, a video, or a directory (processed recursively).
	OUTPUT_PATH can be a file path or a directory. Processed outputs are saved under 'uploads/' when OUTPUT_PATH points there.
	"""

	if frame_step < 1:
		raise click.ClickException("--frame-step must be >= 1")
	if target_fps < 0:
		raise click.ClickException("--target-fps must be >= 0")

	# Resolve mask
	resolved_mask: MaskBox
	if input_path.is_dir():
		# For directories, we require either manual mask or auto; we use a preview from the first file if auto.
		preview_image: Optional[Image.Image] = None
		if auto:
			# find first media file for preview
			for entry in sorted(input_path.rglob("*")):
				if entry.is_file() and (_is_image(entry) or _is_video(entry)):
					if _is_image(entry):
						with Image.open(entry) as img:
							preview_image = img.convert("RGB")
					else:
						preview_image = _extract_preview_from_video(entry)
					break
		resolved_mask = _resolve_mask_box(preview_image, mask_box, auto)
	else:
		if _is_image(input_path):
			with Image.open(input_path) as img:
				preview = img.convert("RGB")
		elif _is_video(input_path):
			preview = _extract_preview_from_video(input_path)
		else:
			raise click.ClickException(f"Unsupported input type: {input_path}")
		resolved_mask = _resolve_mask_box(preview, mask_box, auto)

	# Process
	try:
		result = process_image_or_video(
			input_path,
			output_path,
			mask_box=resolved_mask,
			transparent=transparent,
			force_format=(force_format.upper() if force_format else None),
			frame_step=frame_step,
			target_fps=target_fps,
		)
	except Exception as e:
		logger.exception("Processing failed")
		raise click.ClickException(str(e))

	click.echo(str(result))


if __name__ == "__main__":
	main()
