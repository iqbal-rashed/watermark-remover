export type MediaType = 'image' | 'video';
export type AppState = 'idle' | 'editing' | 'processing' | 'done';
export type FillMode = 'inpaint' | 'transparent' | 'white' | 'black' | 'blur';
export type SelectionMethod = 'draw' | 'auto' | 'manual';

export interface MaskBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface MediaInfo {
  file: File;
  url: string;
  type: MediaType;
  naturalWidth: number;
  naturalHeight: number;
  duration?: number;
}

export interface ProcessOptions {
  fillMode: FillMode;
  outputFormat: string;
  videoQuality: number;
  maxBboxPercent: number;
}