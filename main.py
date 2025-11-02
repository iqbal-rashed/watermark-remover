import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import cv2
import streamlit as st
from PIL import Image

from detector import watermark_detector
from image_video import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, process_image_or_video
from remover import MaskBox, parse_mask_box, remove_watermark


st.set_page_config(layout="wide", page_title="Watermark Remover")
st.title("Watermark Remover")
st.write(
    "Upload an image or video and remove its watermark. "
    "Enable automatic detection or provide custom coordinates if you already know the watermark location."
)

SUPPORTED_EXTENSIONS = sorted({ext.lstrip(".") for ext in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS})

with st.sidebar:
    st.header("Input")
    uploaded_file = st.file_uploader(
        "Upload media",
        type=SUPPORTED_EXTENSIONS,
        help="Supported images: PNG, JPG, JPEG, WEBP, BMP, TIF, TIFF, GIF. Supported videos: MP4, AVI, MOV, MKV, MPG, MPEG, WMV, WEBM, M4V.",
    )

    st.header("Watermark Region")
    auto_detect = st.checkbox("Auto-detect watermark region", value=True)
    manual_mask_input = st.text_input(
        "Mask box (x1,y1,x2,y2)",
        help="Leave blank to rely on detection. Provide coordinates if you know the watermark location.",
        placeholder="3655,2042,3797,2115",
    )

    st.header("Processing Options")
    transparent = st.checkbox("Make watermark area transparent", value=False)
    image_format_choice = st.selectbox("Image output format", ["Original", "PNG", "WEBP", "JPG"])
    video_format_choice = st.selectbox("Video output format", ["Original", "MP4", "AVI"])
    frame_step = st.number_input("Process every Nth frame", min_value=1, value=1)
    target_fps = st.number_input("Target FPS (0 = keep input)", min_value=0.0, value=0.0)

    process_button = st.button("Remove Watermark", type="primary")

col_original, col_result = st.columns(2)


def _load_image_from_bytes(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def _resolve_mask_box(preview_image: Optional[Image.Image], manual_mask_text: str, auto: bool) -> MaskBox:
    if manual_mask_text.strip():
        return parse_mask_box(manual_mask_text)

    if auto:
        if preview_image is None:
            raise ValueError("Preview image unavailable for detection.")
        detected_box = watermark_detector(preview_image)
        if detected_box == (0, 0, 0, 0):
            raise ValueError("Detector could not identify a watermark region. Provide mask coordinates manually.")
        return detected_box

    raise ValueError("Provide mask coordinates or enable auto-detection.")


def _process_image_bytes(
    data: bytes,
    *,
    manual_mask_text: str,
    auto_detect_mask: bool,
    transparent_output: bool,
    force_format: Optional[str],
):
    original_image = _load_image_from_bytes(data)
    mask_box = _resolve_mask_box(original_image, manual_mask_text, auto_detect_mask)

    result_image, output_format = remove_watermark(
        image=original_image,
        transparent=transparent_output,
        force_format=force_format,
        mask_box=mask_box,
    )

    return original_image, result_image, output_format, mask_box


def _extract_preview_from_video(path: Path) -> Image.Image:
    capture = cv2.VideoCapture(str(path))
    try:
        success, frame = capture.read()
        if not success or frame is None:
            raise ValueError("Unable to read the first frame from the uploaded video.")
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    finally:
        capture.release()


def _process_uploaded_video(
    data: bytes,
    original_name: str,
    *,
    manual_mask_text: str,
    auto_detect_mask: bool,
    transparent_output: bool,
    force_format: Optional[str],
    frame_step_value: int,
    target_fps_value: float,
):
    temp_dir = Path(tempfile.mkdtemp(prefix="wmr_video_"))
    input_path = temp_dir / original_name
    with open(input_path, "wb") as temp_file:
        temp_file.write(data)

    preview_image = _extract_preview_from_video(input_path)
    mask_box = _resolve_mask_box(preview_image, manual_mask_text, auto_detect_mask)

    output_stub = temp_dir / "processed"
    result_path = process_image_or_video(
        input_path,
        output_stub,
        mask_box=mask_box,
        transparent=transparent_output,
        force_format=force_format,
        frame_step=frame_step_value,
        target_fps=target_fps_value,
    )

    with open(result_path, "rb") as processed_file:
        processed_bytes = processed_file.read()

    shutil.rmtree(temp_dir, ignore_errors=True)
    return result_path.name, processed_bytes, mask_box


def _is_image_name(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTENSIONS


def _is_video_name(name: str) -> bool:
    return Path(name).suffix.lower() in VIDEO_EXTENSIONS


if process_button:
    if uploaded_file is None:
        st.warning("Please upload an image or video first.")
    else:
        try:
            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name

            if _is_image_name(filename):
                force_format = None if image_format_choice == "Original" else image_format_choice.upper()
                with st.spinner("Processing image..."):
                    original_image, result_image, output_format, mask_box = _process_image_bytes(
                        file_bytes,
                        manual_mask_text=manual_mask_input,
                        auto_detect_mask=auto_detect,
                        transparent_output=transparent,
                        force_format=force_format,
                    )

                col_original.subheader("Original")
                col_original.image(original_image, caption=f"Mask: {mask_box}")

                col_result.subheader("Result")
                col_result.image(result_image, caption=f"Output format: {output_format}")

                buffer = BytesIO()
                result_image.save(buffer, format=output_format)
                st.download_button(
                    "Download processed image",
                    buffer.getvalue(),
                    file_name=f"{Path(filename).stem}_no_watermark.{output_format.lower()}",
                    mime=f"image/{output_format.lower()}",
                )

            elif _is_video_name(filename):
                force_format = None if video_format_choice == "Original" else video_format_choice.upper()
                with st.spinner("Processing video. This may take a while..."):
                    output_name, processed_bytes, mask_box = _process_uploaded_video(
                        file_bytes,
                        filename,
                        manual_mask_text=manual_mask_input,
                        auto_detect_mask=auto_detect,
                        transparent_output=transparent,
                        force_format=force_format,
                        frame_step_value=frame_step,
                        target_fps_value=target_fps,
                    )

                col_original.subheader("Original")
                col_original.video(file_bytes)
                col_original.caption(f"Mask: {mask_box}")

                col_result.subheader("Result")
                col_result.video(processed_bytes)

                st.download_button(
                    "Download processed video",
                    processed_bytes,
                    file_name=output_name,
                    mime="video/mp4" if output_name.lower().endswith(".mp4") else "application/octet-stream",
                )
            else:
                st.error("Unsupported file type. Please upload a supported image or video.")
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
