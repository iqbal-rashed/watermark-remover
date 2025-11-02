
# @click.command()
# @click.argument("input_path", type=click.Path(exists=True))
# @click.argument("output_path", type=click.Path())
# @click.option("--overwrite", is_flag=True, help="Overwrite existing files in bulk mode.")
# @click.option("--transparent", is_flag=True, help="Make watermark regions transparent instead of removing.")
# @click.option("--force-format", type=click.Choice(["PNG", "WEBP", "JPG", "MP4", "AVI"], case_sensitive=False), default=None, help="Force output format. Defaults to input format.")
# @click.option("--mask-box", default=None, help="Override watermark bounding box as 'x1,y1,x2,y2'.")
# @click.option("--frame-step", default=1, type=int, help="Process every Nth frame (1=all frames, 2=every other frame)")
# @click.option("--target-fps", default=0.0, type=float, help="Target output FPS (0=same as input)")
# def main(input_path: str, output_path: str, overwrite: bool, transparent: bool, force_format: str, mask_box: str, frame_step: int, target_fps: float):
#     # Input validation
#     if frame_step < 1:
#         logger.error("frame_step must be >= 1")
#         sys.exit(1)
#     if target_fps < 0:
#         logger.error("target_fps must be >= 0")
#         sys.exit(1)

#     if mask_box:
#         try:
#             mask_box_tuple = parse_mask_box(mask_box)
#         except ValueError as exc:
#             logger.error(f"Invalid mask box: {exc}")
#             sys.exit(1)
#     else:
#         mask_box_tuple = DEFAULT_MASK_BOX

#     input_path = Path(input_path)
#     output_path = Path(output_path)

#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     print(f"Using device: {device}")

#     if not transparent:
#         model_manager = ModelManager(name="lama", device=device)
#         logger.info("LaMa model loaded")
#     else:
#         model_manager = None

#     if input_path.is_dir():
#         if not output_path.exists():
#             output_path.mkdir(parents=True)

#         # Include video files in the search
#         images = list(input_path.glob("*.[jp][pn]g")) + list(input_path.glob("*.webp"))
#         videos = list(input_path.glob("*.mp4")) + list(input_path.glob("*.avi")) + list(input_path.glob("*.mov")) + list(input_path.glob("*.mkv"))
#         files = images + videos
#         total_files = len(files)

#         for idx, file_path in enumerate(tqdm.tqdm(files, desc="Processing files")):
#             output_file = output_path / file_path.name
#             handle_one(file_path, output_file, model_manager, transparent, force_format, mask_box_tuple, overwrite, frame_step, target_fps)
#             progress = int((idx + 1) / total_files * 100) if total_files else 100
#             print(f"input_path:{file_path}, output_path:{output_file}, overall_progress:{progress}")
#     else:
#         output_file = output_path
#         if is_video_file(input_path) and output_path.suffix.lower() not in ['.mp4', '.avi', '.mov', '.mkv']:
#             # Ensure video output has proper extension
#             if force_format and force_format.upper() in ["MP4", "AVI"]:
#                 output_file = output_path.with_suffix(f".{force_format.lower()}")
#             else:
#                 output_file = output_path.with_suffix(".mp4")  # Default to mp4

#         handle_one(input_path, output_file, model_manager, transparent, force_format, mask_box_tuple, overwrite, frame_step, target_fps)
#         print(f"input_path:{input_path}, output_path:{output_file}, overall_progress:100")


# if __name__ == "__main__":
#     main()

# def is_video_file(file_path):
#     """Check if the file is a video based on its extension"""
#     video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
#     return Path(file_path).suffix.lower() in video_extensions


# def is_image_file(file_path):
#     """Check if the file is an image based on its extension"""
#     image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff']
#     return Path(file_path).suffix.lower() in image_extensions


# def process_video(input_path, output_path, model_manager, transparent, force_format, mask_box, frame_step=1, target_fps=0.0):
#     """Process a video file by extracting frames, removing watermarks, and reconstructing the video"""
#     cap = cv2.VideoCapture(str(input_path))
#     if not cap.isOpened():
#         logger.error(f"Error opening video file: {input_path}")
#         return

#     # Get video properties
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     fps_out = target_fps if target_fps > 0 else fps
#     width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
#     # Determine output format
#     if force_format:
#         output_format = force_format.upper()
#     else:
#         output_format = "MP4"  # Default to MP4 for videos
    
#     # Create output video file
#     output_path = Path(output_path)
#     if output_path.is_dir():
#         output_file = output_path / f"{input_path.stem}_no_watermark.{output_format.lower()}"
#     else:
#         output_file = output_path.with_suffix(f".{output_format.lower()}")
    
#     # Create a temporary file to hold the processed video without audio
#     temp_dir = tempfile.mkdtemp()
#     temp_video_path = Path(temp_dir) / f"temp_no_audio.{output_format.lower()}"
    
#     # Set codec based on output format
#     if output_format.upper() == "MP4":
#         fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#     elif output_format.upper() == "AVI":
#         fourcc = cv2.VideoWriter_fourcc(*'XVID')
#     else:
#         fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Default to MP4
    
#     out = cv2.VideoWriter(str(temp_video_path), fourcc, fps_out, (width, height))
    
#     resolved_mask_box = ensure_mask_box(mask_box)

#     # Process each frame
#     with tqdm.tqdm(total=total_frames, desc="Processing video frames") as pbar:
#         frame_idx = 0
#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break
            
#             # Frame skip control
#             if frame_idx % frame_step != 0:
#                 frame_idx += 1
#                 pbar.update(1)
#                 progress = int((frame_idx / total_frames) * 100)
#                 print(f"Processing frame {frame_idx}/{total_frames}, progress:{progress}%")
#                 continue
            
#             # Convert frame to PIL Image
#             frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             pil_image = Image.fromarray(frame_rgb)
            
#             # Get watermark mask
#             mask_image = get_watermark_mask(pil_image, resolved_mask_box)
            
#             # Process frame
#             if transparent:
#                 # For video, we can't use transparency, so we'll fill with a color or background
#                 result_image = make_region_transparent(pil_image, mask_image)
#                 # Convert RGBA to RGB by filling transparent areas with white
#                 background = Image.new("RGB", result_image.size, (255, 255, 255))
#                 background.paste(result_image, mask=result_image.split()[3])
#                 result_image = background
#             else:
#                 if model_manager is None:
#                     raise RuntimeError("Model manager required when running inpainting mode.")
#                 lama_result = process_image_with_lama(np.array(pil_image), np.array(mask_image), model_manager)
#                 result_image = Image.fromarray(cv2.cvtColor(lama_result, cv2.COLOR_BGR2RGB))
            
#             # Convert back to OpenCV format and write to output video
#             frame_result = cv2.cvtColor(np.array(result_image), cv2.COLOR_RGB2BGR)
#             out.write(frame_result)
            
#             # Update progress
#             frame_idx += 1
#             pbar.update(1)
#             progress = int((frame_idx / total_frames) * 100)
#             print(f"Processing frame {frame_idx}/{total_frames}, progress:{progress}%")
    
#     # Release resources
#     cap.release()
#     out.release()
    
#     # Merge the processed video with the original audio track using FFmpeg
#     try:
#         logger.info("Merging processed video with original audio track...")
        
#         # Verify FFmpeg availability
#         try:
#             subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT)
#         except (subprocess.SubprocessError, FileNotFoundError):
#             logger.warning("FFmpeg is not available. The processed video will be exported without audio.")
#             shutil.copy(str(temp_video_path), str(output_file))
#         else:
#             # Use FFmpeg to combine the processed video stream with the original audio track
#             ffmpeg_cmd = [
#                 "ffmpeg", "-y",
#                 "-i", str(temp_video_path),  # Processed video without audio
#                 "-i", str(input_path),       # Original video including audio
#                 "-c:v", "copy",              # Copy the video stream without re-encoding
#                 "-c:a", "aac",               # Encode audio as AAC for wide compatibility
#                 "-map", "0:v:0",             # Select the processed video stream
#                 "-map", "1:a:0",             # Select the original audio stream
#                 "-shortest",                  # Trim output to the shortest input stream
#                 str(output_file)
#             ]
            
#             # Run the FFmpeg command
#             subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#             logger.info("Audio and video merge completed successfully.")
#     except Exception as e:
#         logger.error(f"Error while merging audio/video: {str(e)}")
#         # Fall back to the processed video without audio if merge fails
#         shutil.copy(str(temp_video_path), str(output_file))
#     finally:
#         # Clean up temporary files
#         try:
#             os.remove(str(temp_video_path))
#             os.rmdir(temp_dir)
#         except:
#             pass
    
#     logger.info(f"input_path:{input_path}, output_path:{output_file}, overall_progress:100")
#     return output_file
