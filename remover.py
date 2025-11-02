import sys
from functools import lru_cache
from typing import Optional, Tuple, Union, Any, TYPE_CHECKING
import cv2
import numpy as np
from PIL import Image, ImageDraw
import torch
from loguru import logger

# Optional iopaint/LaMa imports. Keep type hints without importing at runtime.
if TYPE_CHECKING:  # only for static type checkers
    from iopaint.model_manager import ModelManager as _ModelManager
    ModelManager = _ModelManager  # type: ignore
else:
    ModelManager = Any  # type: ignore

try:
    from iopaint.model_manager import ModelManager as RuntimeModelManager  # type: ignore
    from iopaint.schema import HDStrategy, LDMSampler, InpaintRequest as Config  # type: ignore
    HAS_IOPAINT = True
except Exception:
    RuntimeModelManager = None  # type: ignore
    HAS_IOPAINT = False

logger.remove()
logger.add(
    sys.stderr,
    format="<bold><level>{level: <7}</level></bold> | <green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    colorize=True,
    backtrace=False,
    diagnose=False,
)

MaskBox = Tuple[int, int, int, int]


def parse_mask_box(box_str: str) -> MaskBox:
    parts = [part.strip() for part in box_str.split(",")]
    if len(parts) != 4:
        raise ValueError("Mask box must contain exactly four comma-separated integers.")

    try:
        x1, y1, x2, y2 = (int(value) for value in parts)
    except ValueError as exc:
        raise ValueError("Mask box values must be integers.") from exc

    if x1 >= x2 or y1 >= y2:
        raise ValueError("Mask box coordinates must define a valid rectangle (x1 < x2 and y1 < y2).")

    return x1, y1, x2, y2


def ensure_mask_box(mask_box: Union[MaskBox, str]) -> MaskBox:
    if isinstance(mask_box, str):
        return parse_mask_box(mask_box)

    if isinstance(mask_box, tuple) and len(mask_box) == 4:
        try:
            return tuple(int(value) for value in mask_box)  # type: ignore[arg-type]
        except ValueError as exc:
            raise ValueError("Mask box tuple must contain integers.") from exc

    raise TypeError("Mask box must be a tuple of four integers or a comma-separated string.")


def get_watermark_mask(image: Image.Image, mask_box: MaskBox) -> Image.Image:
    """Return a static mask covering the known watermark location."""

    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    width, height = image.size
    x1, y1, x2, y2 = mask_box

    x1 = max(0, min(x1, width))
    y1 = max(0, min(y1, height))
    x2 = max(0, min(x2, width))
    y2 = max(0, min(y2, height))

    if x1 >= x2 or y1 >= y2:
        logger.warning("Mask box is outside image bounds; skipping mask drawing.")
        return mask

    draw.rectangle([x1, y1, x2, y2], fill=255)
    return mask

def process_image_with_lama(image: np.ndarray, mask: np.ndarray, model_manager: Any) -> np.ndarray:
    if not HAS_IOPAINT:
        raise RuntimeError("LaMa/iopaint is not available; cannot run LaMa inpainting.")
    config = Config(
        ldm_steps=50,
        ldm_sampler=LDMSampler.ddim,
        hd_strategy=HDStrategy.CROP,
        hd_strategy_crop_margin=64,
        hd_strategy_crop_trigger_size=800,
        hd_strategy_resize_limit=1600,
    )
    result = model_manager(image, mask, config)

    if result.dtype in (np.float64, np.float32):
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result

@lru_cache(maxsize=1)
def _load_lama_manager(selected_device: Optional[str]) -> Any:
    if not HAS_IOPAINT:
        raise RuntimeError("LaMa/iopaint not installed. Install 'iopaint' or use transparent/OpenCV mode.")
    logger.info("Loading LaMa inpainting model... this happens only once per session.")
    return RuntimeModelManager(name="lama", device=selected_device)  # type: ignore


def process_image_with_opencv_inpaint(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fallback inpainting using OpenCV's Telea algorithm (RGB in/out)."""
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    # Convert to BGR for OpenCV
    if image.ndim == 2:
        image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    if mask.ndim == 3:
        mask_gray = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)
    else:
        mask_gray = mask
    mask_bin = (mask_gray > 0).astype(np.uint8) * 255
    inpainted_bgr = cv2.inpaint(image_bgr, mask_bin, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    return cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)


def make_region_transparent(image: Image.Image, mask: Image.Image):
    image = image.convert("RGBA")
    mask = mask.convert("L")
    transparent_image = Image.new("RGBA", image.size)
    for x in range(image.width):
        for y in range(image.height):
            if mask.getpixel((x, y)) > 0:
                transparent_image.putpixel((x, y), (0, 0, 0, 0))
            else:
                transparent_image.putpixel((x, y), image.getpixel((x, y)))
    return transparent_image

def remove_watermark(
    image: Image.Image,
    transparent: bool = False,
    force_format: Optional[str] = None,
    mask_box: Optional[Union[MaskBox, str]] = None,
    model_manager: Optional[Any] = None,
    device: Optional[str] = None,
) -> Tuple[Image.Image, str]:
    if mask_box is None:
        raise ValueError("mask_box is required to locate the watermark region.")
    
    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")


    original_format = getattr(image, "format", None)
    if image.mode != "RGB":
        image = image.convert("RGB")

    model_manager_local: Optional[Any]
    if transparent:
        model_manager_local = None
    else:
        model_manager_local = None
        if HAS_IOPAINT:
            model_manager_local = model_manager or _load_lama_manager(selected_device)

    resolved_mask_box = ensure_mask_box(mask_box)
    mask_image = get_watermark_mask(image, resolved_mask_box)

    if transparent:
        result_image = make_region_transparent(image, mask_image)
    else:
        # Inpainting path: prefer LaMa if available, otherwise OpenCV fallback
        img_np = np.array(image, copy=True)
        mask_np = np.array(mask_image, copy=True)
        if model_manager_local is not None:
            lama_bgr = process_image_with_lama(img_np, mask_np, model_manager_local)
            result_image = Image.fromarray(cv2.cvtColor(lama_bgr, cv2.COLOR_BGR2RGB))
        else:
            inpaint_rgb = process_image_with_opencv_inpaint(img_np, mask_np)
            result_image = Image.fromarray(inpaint_rgb)
        
    logger.success("Watermark removed successfully")

    valid_formats = {"PNG", "WEBP", "JPG", "JPEG"}
    if force_format:
        output_format = force_format.upper()
        if output_format not in valid_formats:
            raise ValueError(
                f"Unsupported force_format '{force_format}'. Expected one of {sorted(valid_formats)}"
            )
    elif transparent:
        output_format = "PNG"
    else:
        if original_format:
            candidate = original_format.upper()
            output_format = candidate if candidate in valid_formats else "PNG"
        else:
            output_format = "PNG"

    if output_format == "JPG":
        output_format = "JPEG"
        
    

    return result_image, output_format

