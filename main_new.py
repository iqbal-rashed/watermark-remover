import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# Fix tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import cv2
import numpy as np
import streamlit as st
from PIL import Image
from loguru import logger

from image_video import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, _process_single_image, _process_single_video
from remover import MaskBox, parse_mask_box


# Directories and logging
uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)


def extract_first_frame(video_path: Path) -> Optional[Image.Image]:
    """Extract the first frame from a video using OpenCV."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return None
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            logger.error("Failed to read first frame from video")
            return None
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    except Exception as e:
        logger.error(f"Failed to extract first frame: {e}")
        return None


def detect_watermark_on_frame(frame: Image.Image, max_bbox_percent: float = 10.0) -> Optional[MaskBox]:
    """Detect watermark on a frame and return the mask box."""
    try:
        from detector import watermark_detector
        mask_box = watermark_detector(frame, max_bbox_percent=max_bbox_percent)
        return mask_box
    except Exception as e:
        logger.error(f"Watermark detection failed: {e}")
        return None


def draw_mask_box_on_image(image: Image.Image, mask_box: MaskBox) -> Image.Image:
    """Draw a rectangle on the image showing the detected watermark region."""
    img_copy = image.copy()
    img_array = np.array(img_copy)
    x1, y1, x2, y2 = mask_box
    cv2.rectangle(img_array, (x1, y1), (x2, y2), (255, 0, 0), 3)
    return Image.fromarray(img_array)


# Page config
st.set_page_config(page_title="Watermark Remover", page_icon="🧼", layout="centered")

# Increase file upload size limit (default is 200MB, setting to 2GB)
st.config.set_option('server.maxUploadSize', 2048)

st.title("🧼 Watermark Remover")
st.caption("Upload an image or video, choose options, and get a cleaned output saved under 'uploads/'.")

# Initialize session state
if "video_preview_done" not in st.session_state:
    st.session_state.video_preview_done = False
if "confirmed_mask_box" not in st.session_state:
    st.session_state.confirmed_mask_box = None
if "preview_frame" not in st.session_state:
    st.session_state.preview_frame = None
if "video_save_path" not in st.session_state:
    st.session_state.video_save_path = None

# Media type selection
media_type = st.radio("Media Type", ["Image", "Video"], horizontal=True)

# Reset state when switching media type
if "last_media_type" not in st.session_state:
    st.session_state.last_media_type = media_type
if st.session_state.last_media_type != media_type:
    st.session_state.video_preview_done = False
    st.session_state.confirmed_mask_box = None
    st.session_state.preview_frame = None
    st.session_state.video_save_path = None
    st.session_state.last_media_type = media_type

# File uploader
if media_type == "Image":
    uploaded = st.file_uploader("Upload image", type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS])
else:
    uploaded = st.file_uploader("Upload video", type=[ext.lstrip(".") for ext in VIDEO_EXTENSIONS])

# Reset state when new file is uploaded
if uploaded:
    current_file_name = uploaded.name
    if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != current_file_name:
        st.session_state.video_preview_done = False
        st.session_state.confirmed_mask_box = None
        st.session_state.preview_frame = None
        st.session_state.video_save_path = None
        st.session_state.last_uploaded_file = current_file_name

# Options
col1, col2 = st.columns(2)
with col1:
    auto_detect = st.checkbox("Auto-detect watermark", value=True)
with col2:
    transparent = st.checkbox("Make region transparent (PNG)", value=False, 
                              help="For images only; videos will fill transparent area with white.")

mask_text = None
max_bbox_percent = None
if not auto_detect:
    mask_text = st.text_input("Mask box (x1,y1,x2,y2)", placeholder="e.g. 120, 430, 980, 540")
else:
    max_bbox_percent = st.number_input("Max BoundingBox Percent", placeholder="e.g. 10", value=10)

# Format options
if media_type == "Image":
    img_format = st.selectbox("Image output format", ["Original", "PNG", "WEBP", "JPG"], index=0)
    force_format = None if img_format == "Original" else img_format
else:
    vid_format = st.selectbox("Video output format", ["Original", "MP4", "AVI"], index=0)
    frame_step = st.number_input("Process every Nth frame", min_value=1, value=1, step=1)
    target_fps = st.number_input("Target FPS (0 = keep input)", min_value=0.0, value=0.0, step=1.0)
    force_format = None if vid_format == "Original" else vid_format

st.divider()

# IMAGE PROCESSING
if media_type == "Image":
    run_btn = st.button("Remove Watermark", type='secondary', use_container_width=True)
    
    if run_btn:
        if not uploaded:
            st.error("Please upload a file first.")
            st.stop()

        with st.spinner("Processing. This may take a while..."):
            save_path = uploads_dir / uploaded.name
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
                
            try:
                out_path = _process_single_image(
                    save_path,
                    uploads_dir,
                    mask_box=mask_text,
                    transparent=transparent,
                    force_format=force_format,
                    max_bbox_percent=max_bbox_percent
                )
                st.image(str(out_path))
                with open(out_path, "rb") as fp:
                    st.download_button("Download", data=fp, file_name=out_path.name, 
                                       type='primary', use_container_width=True)
            except Exception as e:
                st.error(f"Processing failed: {e}")
                st.stop()

# VIDEO PROCESSING WITH PREVIEW
else:
    # Step 1: Preview first frame
    if not st.session_state.video_preview_done:
        preview_btn = st.button("🔍 Preview First Frame & Detect Watermark", type='secondary', use_container_width=True)
        
        if preview_btn:
            if not uploaded:
                st.error("Please upload a video first.")
                st.stop()
            
            with st.spinner("Extracting first frame and detecting watermark..."):
                # Save video temporarily
                save_path = uploads_dir / uploaded.name
                with open(save_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                st.session_state.video_save_path = save_path
                
                # Extract first frame
                frame = extract_first_frame(save_path)
                if frame is None:
                    st.error("Failed to extract first frame from video.")
                    st.stop()
                
                st.session_state.preview_frame = frame
                
                # Detect watermark
                if auto_detect:
                    detected_box = detect_watermark_on_frame(frame, max_bbox_percent=max_bbox_percent or 10.0)
                    if detected_box:
                        st.session_state.confirmed_mask_box = detected_box
                    else:
                        st.warning("No watermark detected automatically. Please enter mask box manually.")
                elif mask_text:
                    try:
                        st.session_state.confirmed_mask_box = parse_mask_box(mask_text)
                    except Exception as e:
                        st.error(f"Invalid mask box format: {e}")
                        st.stop()
                
                st.session_state.video_preview_done = True
                st.rerun()
    
    # Step 2: Show preview and allow confirmation/adjustment
    if st.session_state.video_preview_done and st.session_state.preview_frame:
        st.subheader("📸 First Frame Preview")
        
        frame = st.session_state.preview_frame
        mask_box = st.session_state.confirmed_mask_box
        
        # Show frame with detected region
        if mask_box:
            preview_with_box = draw_mask_box_on_image(frame, mask_box)
            st.image(preview_with_box, caption=f"Detected watermark region: {mask_box}", use_container_width=True)
            
            # Allow manual adjustment
            st.write("**Adjust mask box if needed:**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                new_x1 = st.number_input("X1", value=mask_box[0], step=1)
            with col2:
                new_y1 = st.number_input("Y1", value=mask_box[1], step=1)
            with col3:
                new_x2 = st.number_input("X2", value=mask_box[2], step=1)
            with col4:
                new_y2 = st.number_input("Y2", value=mask_box[3], step=1)
            
            adjusted_mask_box = (int(new_x1), int(new_y1), int(new_x2), int(new_y2))
            
            # Show preview with adjusted box if changed
            if adjusted_mask_box != mask_box:
                adjusted_preview = draw_mask_box_on_image(frame, adjusted_mask_box)
                st.image(adjusted_preview, caption=f"Adjusted region: {adjusted_mask_box}", use_container_width=True)
                st.session_state.confirmed_mask_box = adjusted_mask_box
        else:
            st.image(frame, caption="First frame (no watermark detected)", use_container_width=True)
            st.warning("No watermark region detected. Please enter mask box manually below.")
            
            manual_mask = st.text_input("Enter mask box (x1,y1,x2,y2)", placeholder="e.g. 120, 430, 980, 540", key="manual_mask_input")
            if manual_mask:
                try:
                    parsed_box = parse_mask_box(manual_mask)
                    st.session_state.confirmed_mask_box = parsed_box
                    preview_with_box = draw_mask_box_on_image(frame, parsed_box)
                    st.image(preview_with_box, caption=f"Manual mask region: {parsed_box}", use_container_width=True)
                except Exception as e:
                    st.error(f"Invalid mask box: {e}")
        
        st.divider()
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            reset_btn = st.button("🔄 Reset & Re-detect", type='secondary', use_container_width=True)
        with col2:
            confirm_btn = st.button("✅ Confirm & Process Video", type='primary', use_container_width=True, 
                                    disabled=st.session_state.confirmed_mask_box is None)
        
        if reset_btn:
            st.session_state.video_preview_done = False
            st.session_state.confirmed_mask_box = None
            st.session_state.preview_frame = None
            st.rerun()
        
        if confirm_btn:
            if st.session_state.confirmed_mask_box is None:
                st.error("Please detect or enter a valid mask box first.")
                st.stop()
            
            with st.spinner("Processing entire video. This may take a while..."):
                try:
                    # Convert mask box to string format for the processing function
                    box = st.session_state.confirmed_mask_box
                    mask_box_str = f"{box[0]},{box[1]},{box[2]},{box[3]}"
                    
                    out_path = _process_single_video(
                        st.session_state.video_save_path,
                        uploads_dir,
                        mask_box=mask_box_str,
                        transparent=transparent,
                        force_format=force_format,
                        max_bbox_percent=None,  # Use confirmed mask box, not auto-detect
                        frame_step=frame_step,
                        target_fps=target_fps
                    )
                    
                    st.success("✅ Video processed successfully!")
                    st.video(str(out_path))
                    with open(out_path, "rb") as fp:
                        st.download_button("📥 Download Processed Video", data=fp, file_name=out_path.name, 
                                           type='primary', use_container_width=True)
                    
                    # Reset state after successful processing
                    st.session_state.video_preview_done = False
                    st.session_state.confirmed_mask_box = None
                    st.session_state.preview_frame = None
                    
                except Exception as e:
                    st.error(f"Processing failed: {e}")
                    logger.exception("Video processing error")
