import { MaskBox, FillMode } from '../components/types';
import { applyFill } from './imageProcessor';

/**
 * Process video frame-by-frame, applying watermark removal,
 * then encode using MediaRecorder.
 */
export async function processVideo(
videoUrl: string,
box: MaskBox,
fillMode: FillMode,
onProgress: (progress: number, message: string) => void)
: Promise<Blob> {
  // Load video
  const video = document.createElement('video');
  video.src = videoUrl;
  video.muted = true;
  video.playsInline = true;
  video.crossOrigin = 'anonymous';

  await new Promise<void>((resolve, reject) => {
    video.onloadedmetadata = () => resolve();
    video.onerror = () => reject(new Error('Failed to load video'));
  });

  const width = video.videoWidth;
  const height = video.videoHeight;
  const duration = video.duration;

  if (!width || !height) throw new Error('Invalid video dimensions');

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) throw new Error('Canvas context unavailable');

  // Pick a supported mime type
  const mimeCandidates = [
  'video/webm;codecs=vp9',
  'video/webm;codecs=vp8',
  'video/webm',
  'video/mp4'];

  let mimeType = '';
  for (const m of mimeCandidates) {
    if (
    typeof MediaRecorder !== 'undefined' &&
    MediaRecorder.isTypeSupported(m))
    {
      mimeType = m;
      break;
    }
  }
  if (!mimeType) throw new Error('No supported video format in this browser');

  const fps = 30;
  const stream: MediaStream = (canvas as any).captureStream(fps);

  // Try to add audio from original video
  try {
    const videoStream: MediaStream | undefined = (video as any).captureStream?.();
    if (videoStream) {
      const audioTracks = videoStream.getAudioTracks();
      audioTracks.forEach((t) => stream.addTrack(t));
    }
  } catch {

    // Audio not available; continue without it
  }
  const recorder = new MediaRecorder(stream, {
    mimeType,
    videoBitsPerSecond: 5_000_000
  });
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) chunks.push(e.data);
  };

  const stopped = new Promise<Blob>((resolve) => {
    recorder.onstop = () => resolve(new Blob(chunks, { type: mimeType }));
  });

  recorder.start();
  onProgress(0, 'Starting video processing...');

  // Process frame by frame via playback
  await video.play();

  let lastReport = 0;
  const drawFrame = () => {
    ctx.drawImage(video, 0, 0, width, height);
    const imageData = ctx.getImageData(0, 0, width, height);
    applyFill(imageData, box, fillMode);
    ctx.putImageData(imageData, 0, 0);

    const t = video.currentTime;
    const p = duration > 0 ? Math.min(99, t / duration * 100) : 0;
    if (p - lastReport >= 1) {
      lastReport = p;
      onProgress(
        p,
        `Processing frame at ${t.toFixed(1)}s / ${duration.toFixed(1)}s`
      );
    }
  };

  await new Promise<void>((resolve) => {
    let animId = 0;
    const tick = () => {
      if (video.ended || video.paused) {
        cancelAnimationFrame(animId);
        resolve();
        return;
      }
      drawFrame();
      animId = requestAnimationFrame(tick);
    };
    video.onended = () => {
      // Draw final frame
      drawFrame();
      cancelAnimationFrame(animId);
      resolve();
    };
    animId = requestAnimationFrame(tick);
  });

  onProgress(99, 'Finalizing video...');
  recorder.stop();

  const blob = await stopped;
  onProgress(100, 'Done');
  return blob;
}