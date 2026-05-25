from enum import Enum
from functools import lru_cache
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw
from loguru import logger

from .remover import MaskBox

try:
    from cv2.typing import MatLike
except ImportError:
    MatLike = np.ndarray  # type: ignore


class TaskType(str, Enum):
    OPEN_VOCAB_DETECTION = "<OPEN_VOCABULARY_DETECTION>"


DEFAULT_MODEL_ID = "microsoft/Florence-2-large"


@lru_cache(maxsize=1)
def _load_default_model(selected_device: str):
    from transformers import AutoModelForCausalLM, AutoProcessor
    logger.info(f"Loading detection model '{DEFAULT_MODEL_ID}' (cached)")
    model = AutoModelForCausalLM.from_pretrained(
        DEFAULT_MODEL_ID, trust_remote_code=True
    ).to(selected_device).eval()
    processor = AutoProcessor.from_pretrained(DEFAULT_MODEL_ID, trust_remote_code=True)
    return model, processor


def watermark_detector(
    image: Image.Image,
    model=None,
    processor=None,
    max_bbox_percent: float = 10.0,
    device: Optional[str] = None,
) -> MaskBox:
    import torch
    if image.mode != "RGB":
        image = image.convert("RGB")

    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if model is None or processor is None:
        model, processor = _load_default_model(selected_device)

    filtered_boxes = _detect_bounding_boxes(
        image, model, processor,
        max_bbox_percent=max_bbox_percent,
        device=selected_device,
    )
    if filtered_boxes:
        logger.success(f"Detected {len(filtered_boxes)} watermark box(es)")
        return filtered_boxes[0]

    logger.warning("No watermark bounding boxes detected; returning empty box")
    return (0, 0, 0, 0)


def identify(task_prompt: TaskType, image: Image.Image, text_input: str, model, processor, *, device: str) -> dict:
    if not isinstance(task_prompt, TaskType):
        raise ValueError(f"task_prompt must be a TaskType, got {type(task_prompt)}")
    prompt = task_prompt.value if text_input is None else task_prompt.value + text_input
    inputs = processor(text=prompt, images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        early_stopping=False,
        do_sample=False,
        num_beams=3,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    return processor.post_process_generation(
        generated_text, task=task_prompt.value, image_size=(image.width, image.height)
    )


def _detect_bounding_boxes(
    image: Image.Image,
    model,
    processor,
    *,
    max_bbox_percent: float,
    device: str,
) -> List[MaskBox]:
    parsed_answer = identify(TaskType.OPEN_VOCAB_DETECTION, image, "veo text", model, processor, device=device)
    mask_boxes: List[MaskBox] = []
    detection_key = TaskType.OPEN_VOCAB_DETECTION.value
    detections = parsed_answer.get(detection_key, {})
    bboxes = detections.get("bboxes", [])
    image_area = image.width * image.height

    for bbox in bboxes:
        x1, y1, x2, y2 = map(int, bbox)
        bbox_area = max(0, (x2 - x1)) * max(0, (y2 - y1))
        if bbox_area == 0:
            continue
        coverage = (bbox_area / image_area) * 100 if image_area else 0
        if coverage <= max_bbox_percent:
            mask_boxes.append((x1, y1, x2, y2))
            logger.success("Box x1:{} y1:{} x2:{} y2:{}", x1, y1, x2, y2)
        else:
            logger.debug("Skipping box covering {:.2f}% (limit {:.2f}%)", coverage, max_bbox_percent)

    return mask_boxes


def get_watermark_mask_image(
    image: Image.Image,
    model,
    processor,
    max_bbox_percent: float,
    device: Optional[str] = None,
) -> Image.Image:
    import torch
    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    boxes = _detect_bounding_boxes(image, model, processor, max_bbox_percent=max_bbox_percent, device=selected_device)
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    for x1, y1, x2, y2 in boxes:
        draw.rectangle([x1, y1, x2, y2], fill=255)
    return mask
