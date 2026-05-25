import { MaskBox } from '../components/types';

type ProgressCb = (progress: number, message: string) => void;

const yieldToBrowser = () =>
new Promise<void>((resolve) => setTimeout(resolve, 0));

/**
 * Heuristic watermark detector: finds the region with highest edge density,
 * biased toward image corners (where watermarks typically sit).
 * No ML — runs entirely on Canvas in the browser.
 */
export async function detectWatermark(
imageUrl: string,
maxBboxPercent = 10,
onProgress?: ProgressCb)
: Promise<MaskBox | null> {
  onProgress?.(2, 'Loading image…');
  const img = await loadImage(imageUrl);
  const W = img.naturalWidth;
  const H = img.naturalHeight;

  // Downscale for fast analysis
  const SCALE = Math.min(1, 400 / Math.max(W, H));
  const sw = Math.max(64, Math.floor(W * SCALE));
  const sh = Math.max(64, Math.floor(H * SCALE));

  const canvas = document.createElement('canvas');
  canvas.width = sw;
  canvas.height = sh;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) return null;

  ctx.drawImage(img, 0, 0, sw, sh);
  const { data } = ctx.getImageData(0, 0, sw, sh);

  onProgress?.(15, 'Building edge map…');
  await yieldToBrowser();

  // Build grayscale + edge map (simple gradient magnitude)
  const gray = new Float32Array(sw * sh);
  for (let i = 0; i < sw * sh; i++) {
    const idx = i * 4;
    gray[i] = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
  }
  const edge = new Float32Array(sw * sh);
  for (let y = 1; y < sh - 1; y++) {
    for (let x = 1; x < sw - 1; x++) {
      const i = y * sw + x;
      const gx = gray[i + 1] - gray[i - 1];
      const gy = gray[i + sw] - gray[i - sw];
      edge[i] = Math.sqrt(gx * gx + gy * gy);
    }
  }

  onProgress?.(35, 'Computing integral image…');
  await yieldToBrowser();

  // Integral image for fast box-sum queries
  const integ = new Float64Array((sw + 1) * (sh + 1));
  for (let y = 1; y <= sh; y++) {
    let rowSum = 0;
    for (let x = 1; x <= sw; x++) {
      rowSum += edge[(y - 1) * sw + (x - 1)];
      integ[y * (sw + 1) + x] = integ[(y - 1) * (sw + 1) + x] + rowSum;
    }
  }
  const sumBox = (x1: number, y1: number, x2: number, y2: number) =>
  integ[y2 * (sw + 1) + x2] -
  integ[y1 * (sw + 1) + x2] -
  integ[y2 * (sw + 1) + x1] +
  integ[y1 * (sw + 1) + x1];

  onProgress?.(45, 'Scanning for candidate regions…');
  await yieldToBrowser();

  // Search sliding windows. Try a few aspect ratios that match typical watermarks.
  const maxArea = sw * sh * (maxBboxPercent / 100);
  const aspects = [1, 1.5, 2, 3, 4, 0.7, 0.5];

  let bestScore = -Infinity;
  let bestBox: {x1: number;y1: number;x2: number;y2: number;} | null = null;

  for (let ai = 0; ai < aspects.length; ai++) {
    const a = aspects[ai];
    const w = Math.min(sw - 2, Math.max(20, Math.floor(Math.sqrt(maxArea * a))));
    const h = Math.min(sh - 2, Math.max(20, Math.floor(w / a)));
    if (w >= sw || h >= sh) continue;

    const step = Math.max(4, Math.floor(Math.min(w, h) / 4));

    for (let y = 0; y + h < sh; y += step) {
      for (let x = 0; x + w < sw; x += step) {
        const sum = sumBox(x, y, x + w, y + h);
        const area = w * h;
        const density = sum / area;

        const cx = x + w / 2;
        const cy = y + h / 2;
        const cornerDist = Math.min(
          Math.hypot(cx, cy),
          Math.hypot(sw - cx, cy),
          Math.hypot(cx, sh - cy),
          Math.hypot(sw - cx, sh - cy)
        );
        const cornerBias = 1 - cornerDist / Math.hypot(sw, sh);

        const score = density * (1 + 0.4 * cornerBias);

        if (score > bestScore) {
          bestScore = score;
          bestBox = { x1: x, y1: y, x2: x + w, y2: y + h };
        }
      }
    }

    const p = 45 + Math.round((ai + 1) / aspects.length * 35);
    onProgress?.(p, `Evaluating ratio ${a.toFixed(1)}…`);
    await yieldToBrowser();
  }

  if (!bestBox) {
    onProgress?.(100, 'No region found');
    return null;
  }

  onProgress?.(85, 'Refining region…');
  await yieldToBrowser();

  const tightenThreshold = bestScore * 0.5;
  const { x1, y1, x2, y2 } = bestBox;
  let tx1 = x2,
    ty1 = y2,
    tx2 = x1,
    ty2 = y1;
  for (let y = y1; y < y2; y++) {
    for (let x = x1; x < x2; x++) {
      if (edge[y * sw + x] > tightenThreshold) {
        if (x < tx1) tx1 = x;
        if (x > tx2) tx2 = x;
        if (y < ty1) ty1 = y;
        if (y > ty2) ty2 = y;
      }
    }
  }
  if (tx2 > tx1 && ty2 > ty1) {
    const padX = Math.max(2, Math.floor((tx2 - tx1) * 0.08));
    const padY = Math.max(2, Math.floor((ty2 - ty1) * 0.08));
    tx1 = Math.max(0, tx1 - padX);
    ty1 = Math.max(0, ty1 - padY);
    tx2 = Math.min(sw - 1, tx2 + padX);
    ty2 = Math.min(sh - 1, ty2 + padY);
  } else {
    tx1 = x1;
    ty1 = y1;
    tx2 = x2;
    ty2 = y2;
  }

  onProgress?.(100, 'Done');

  return {
    x1: Math.round(tx1 / sw * W),
    y1: Math.round(ty1 / sh * H),
    x2: Math.round(tx2 / sw * W),
    y2: Math.round(ty2 / sh * H)
  };
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = url;
  });
}

/**
 * For video, extract a representative frame, then run image-based detection on it.
 */
export async function detectWatermarkInVideo(
videoUrl: string,
maxBboxPercent = 10,
onProgress?: ProgressCb)
: Promise<MaskBox | null> {
  onProgress?.(1, 'Extracting frame…');
  const video = document.createElement('video');
  video.src = videoUrl;
  video.muted = true;
  video.playsInline = true;
  video.crossOrigin = 'anonymous';

  await new Promise<void>((resolve, reject) => {
    video.onloadedmetadata = () => resolve();
    video.onerror = () => reject(new Error('Failed to load video'));
  });

  await new Promise<void>((resolve) => {
    video.currentTime = Math.min(0.5, video.duration * 0.1);
    video.onseeked = () => resolve();
  });

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.drawImage(video, 0, 0);

  const frameUrl = canvas.toDataURL('image/png');
  return detectWatermark(frameUrl, maxBboxPercent, onProgress);
}