import io
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import streamlit as st
from PIL import Image
from loguru import logger

from image_video import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, _process_single_image, process_image_or_video,_process_single_video
from remover import MaskBox, parse_mask_box


# Directories and logging
uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)


st.set_page_config(page_title="Watermark Remover", page_icon="🧼", layout="centered")
st.title("Watermark Remover")
st.caption("Upload an image or video, choose options, and get a cleaned output saved under 'uploads/'.")

media_type = st.radio("Media Type", ["Image", "Video"], horizontal=True)

if media_type == "Image":
    uploaded = st.file_uploader("Upload image", type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS])
else:
    uploaded = st.file_uploader("Upload video", type=[ext.lstrip(".") for ext in VIDEO_EXTENSIONS])

col1, col2 = st.columns(2)
with col1:
    auto_detect = st.checkbox("Auto-detect watermark", value=True)
with col2:
    transparent = st.checkbox("Make region transparent (PNG)", value=False, help="For images only; videos will fill transparent area with white.")
mask_text = None
max_bbox_percent= None
if not auto_detect:
    mask_text = st.text_input("Mask box (x1,y1,x2,y2)", placeholder="e.g. 120, 430, 980, 540")
else:
    max_bbox_percent = st.number_input("Max BoundingBox Percent", placeholder="e.g. 10", value=10)

if media_type == "Image":
    img_format = st.selectbox("Image output format", ["Original", "PNG", "WEBP", "JPG"], index=0)
    force_format = None if img_format == "Original" else img_format
else:
    vid_format = st.selectbox("Video output format", ["Original", "MP4", "AVI"], index=0)
    frame_step = st.number_input("Process every Nth frame", min_value=1, value=1, step=1)
    target_fps = st.number_input("Target FPS (0 = keep input)", min_value=0.0, value=0.0, step=1.0)
    force_format = None if vid_format == "Original" else vid_format
    
st.divider()


run_btn = st.button("Remove Watermark",type='secondary',use_container_width=True)

if run_btn:
    if not uploaded:
        st.error("Please upload a file first.")
        st.stop()

    with st.spinner("Processing. This may take a while..."):
        save_path = uploads_dir / uploaded.name
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
            
        if media_type == "Image":
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
                    st.download_button("Download", data=fp, file_name=out_path.name,type='primary',use_container_width=True)
            except Exception as e:
                st.error(f"Processing failed: {e}")
                st.stop()
        else:
            try:
                out_path = _process_single_video(
                    save_path,
                    uploads_dir,
                    mask_box=mask_text,
                    transparent=transparent,
                    force_format=force_format,
                    max_bbox_percent=max_bbox_percent,
                    frame_step=frame_step,
                    target_fps=target_fps
                    
                )
                st.video(str(out_path))
                with open(out_path, "rb") as fp:
                    st.download_button("Download", data=fp, file_name=out_path.name,type='primary',use_container_width=True)
            except Exception as e:
                st.error(f"Processing failed: {e}")
                st.stop()

