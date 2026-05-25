import { MaskBox, FillMode } from '../components/types';

/**
 * Apply watermark removal to image data based on fill mode
 */
export function applyFill(
imageData: ImageData,
box: MaskBox,
fillMode: FillMode)
: ImageData {
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;

  // Clamp box
  const x1 = Math.max(0, Math.min(width, Math.floor(box.x1)));
  const y1 = Math.max(0, Math.min(height, Math.floor(box.y1)));
  const x2 = Math.max(0, Math.min(width, Math.floor(box.x2)));
  const y2 = Math.max(0, Math.min(height, Math.floor(box.y2)));

  if (x2 <= x1 || y2 <= y1) return imageData;

  if (fillMode === 'transparent') {
    for (let y = y1; y < y2; y++) {
      for (let x = x1; x < x2; x++) {
        const idx = (y * width + x) * 4;
        data[idx + 3] = 0;
      }
    }
    return imageData;
  }

  if (fillMode === 'white' || fillMode === 'black') {
    const v = fillMode === 'white' ? 255 : 0;
    for (let y = y1; y < y2; y++) {
      for (let x = x1; x < x2; x++) {
        const idx = (y * width + x) * 4;
        data[idx] = v;
        data[idx + 1] = v;
        data[idx + 2] = v;
        data[idx + 3] = 255;
      }
    }
    return imageData;
  }

  if (fillMode === 'blur') {
    // Box blur using border average
    let r = 0,
      g = 0,
      b = 0,
      count = 0;
    const sampleEdge = (sx: number, sy: number) => {
      if (sx < 0 || sx >= width || sy < 0 || sy >= height) return;
      const i = (sy * width + sx) * 4;
      r += data[i];
      g += data[i + 1];
      b += data[i + 2];
      count++;
    };
    for (let x = x1; x < x2; x++) {
      sampleEdge(x, y1 - 1);
      sampleEdge(x, y2);
    }
    for (let y = y1; y < y2; y++) {
      sampleEdge(x1 - 1, y);
      sampleEdge(x2, y);
    }
    if (count === 0) return imageData;
    r = Math.round(r / count);
    g = Math.round(g / count);
    b = Math.round(b / count);
    for (let y = y1; y < y2; y++) {
      for (let x = x1; x < x2; x++) {
        const idx = (y * width + x) * 4;
        data[idx] = r;
        data[idx + 1] = g;
        data[idx + 2] = b;
        data[idx + 3] = 255;
      }
    }
    return imageData;
  }

  // Default: inpaint — directional blend from 4 surrounding edges
  // Sample the row/col just outside the box and blend toward center
  const boxW = x2 - x1;
  const boxH = y2 - y1;

  for (let y = y1; y < y2; y++) {
    for (let x = x1; x < x2; x++) {
      const idx = (y * width + x) * 4;

      // Top sample
      const topY = Math.max(0, y1 - 1);
      const topIdx = (topY * width + x) * 4;
      // Bottom sample
      const botY = Math.min(height - 1, y2);
      const botIdx = (botY * width + x) * 4;
      // Left sample
      const leftX = Math.max(0, x1 - 1);
      const leftIdx = (y * width + leftX) * 4;
      // Right sample
      const rightX = Math.min(width - 1, x2);
      const rightIdx = (y * width + rightX) * 4;

      // Weights: closer edge = higher weight
      const wT = boxH > 0 ? (y2 - y) / boxH : 0.5;
      const wB = boxH > 0 ? (y - y1 + 1) / boxH : 0.5;
      const wL = boxW > 0 ? (x2 - x) / boxW : 0.5;
      const wR = boxW > 0 ? (x - x1 + 1) / boxW : 0.5;
      const totalW = wT + wB + wL + wR;

      data[idx] =
      (data[topIdx] * wT +
      data[botIdx] * wB +
      data[leftIdx] * wL +
      data[rightIdx] * wR) /
      totalW;
      data[idx + 1] =
      (data[topIdx + 1] * wT +
      data[botIdx + 1] * wB +
      data[leftIdx + 1] * wL +
      data[rightIdx + 1] * wR) /
      totalW;
      data[idx + 2] =
      (data[topIdx + 2] * wT +
      data[botIdx + 2] * wB +
      data[leftIdx + 2] * wL +
      data[rightIdx + 2] * wR) /
      totalW;
      data[idx + 3] = 255;
    }
  }

  return imageData;
}

/**
 * Process an image file and return a Blob of the cleaned image
 */
export async function processImage(
imageUrl: string,
box: MaskBox,
fillMode: FillMode,
outputFormat: string)
: Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      if (!ctx) return reject(new Error('Canvas context unavailable'));

      ctx.drawImage(img, 0, 0);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const processed = applyFill(imageData, box, fillMode);
      ctx.putImageData(processed, 0, 0);

      const mime =
      outputFormat === 'png' ?
      'image/png' :
      outputFormat === 'webp' ?
      'image/webp' :
      'image/jpeg';

      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);else
          reject(new Error('Failed to encode image'));
        },
        mime,
        outputFormat === 'jpeg' ? 0.95 : undefined
      );
    };
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = imageUrl;
  });
}