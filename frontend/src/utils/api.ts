/** HTTP + SSE API client for the FastAPI backend. */

const BASE = "";  // same origin

// ── Types ────────────────────────────────────────────────────────────────────

export interface SetupStatus {
  complete: boolean;
  gpu_available: boolean;
  torch_installed: boolean;
  transformers_installed: boolean;
  florence_downloaded: boolean;
}

export interface SetupEvent {
  step?: string;
  status: string;
  progress: number;
  done_step?: boolean;
  all_done?: boolean;
  error?: boolean;
  skipped?: boolean;
}

export interface UploadResult {
  file_id: string;
  type: "image" | "video";
  name: string;
}

export interface DetectEvent {
  status: string;
  progress: number;
  box?: [number, number, number, number];
  error?: boolean;
}

export interface ProcessEvent {
  status: string;
  progress: number;
  output_id?: string;
  filename?: string;
  error?: boolean;
}

export interface UpdateInfo {
  update_available: boolean;
  current_version: string;
  latest_version?: string;
  release_name?: string;
  release_notes?: string;
  download_url?: string;
  error?: string;
}

// ── Setup ────────────────────────────────────────────────────────────────────

export async function getSetupStatus(): Promise<SetupStatus> {
  const res = await fetch(`${BASE}/api/setup/status`);
  if (!res.ok) throw new Error(`Setup status failed: ${res.status}`);
  return res.json();
}

export function streamSetup(
  gpu: boolean,
  onEvent: (e: SetupEvent) => void,
): () => void {
  const url = `${BASE}/api/setup/install?gpu=${gpu}`;
  const es = new EventSource(url);
  es.onmessage = (e) => {
    try {
      const data: SetupEvent = JSON.parse(e.data);
      onEvent(data);
      if (data.all_done || data.error) es.close();
    } catch {
      // ignore parse errors
    }
  };
  es.onerror = () => {
    onEvent({ status: "Connection error", progress: 0, error: true });
    es.close();
  };
  return () => es.close();
}

// ── Files ────────────────────────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/files/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export function getPreviewUrl(fileId: string): string {
  return `${BASE}/api/files/preview/${fileId}`;
}

export function getDownloadUrl(fileId: string): string {
  return `${BASE}/api/files/download/${fileId}`;
}

// ── Detection ─────────────────────────────────────────────────────────────────

export function streamDetect(
  fileId: string,
  maxBboxPercent: number,
  onEvent: (e: DetectEvent) => void,
): () => void {
  const url = `${BASE}/api/detect?file_id=${encodeURIComponent(fileId)}&max_bbox_percent=${maxBboxPercent}`;
  const es = new EventSource(url);
  es.onmessage = (e) => {
    try {
      const data: DetectEvent = JSON.parse(e.data);
      onEvent(data);
      if (data.box !== undefined || data.error) es.close();
    } catch {
      // ignore
    }
  };
  es.onerror = () => {
    onEvent({ status: "Connection error", progress: 0, error: true });
    es.close();
  };
  return () => es.close();
}

// ── Processing ───────────────────────────────────────────────────────────────

export interface ProcessOptions {
  fileId: string;
  maskBox: string;
  transparent?: boolean;
  forceFormat?: string;
  frameStep?: number;
  targetFps?: number;
  maxBboxPercent?: number;
}

export function streamProcess(
  opts: ProcessOptions,
  onEvent: (e: ProcessEvent) => void,
): () => void {
  const params = new URLSearchParams({
    file_id: opts.fileId,
    mask_box: opts.maskBox,
    transparent: String(opts.transparent ?? false),
    frame_step: String(opts.frameStep ?? 1),
    target_fps: String(opts.targetFps ?? 0),
    max_bbox_percent: String(opts.maxBboxPercent ?? 10),
  });
  if (opts.forceFormat) params.set("force_format", opts.forceFormat);

  const url = `${BASE}/api/process?${params}`;
  const es = new EventSource(url);
  es.onmessage = (e) => {
    try {
      const data: ProcessEvent = JSON.parse(e.data);
      onEvent(data);
      if (data.output_id || data.error) es.close();
    } catch {
      // ignore
    }
  };
  es.onerror = () => {
    onEvent({ status: "Connection error", progress: 0, error: true });
    es.close();
  };
  return () => es.close();
}

// ── Updates ──────────────────────────────────────────────────────────────────

export async function checkForUpdates(): Promise<UpdateInfo> {
  const res = await fetch(`${BASE}/api/update/check`);
  if (!res.ok) throw new Error(`Update check failed: ${res.status}`);
  return res.json();
}

export function streamUpdateDownload(
  downloadUrl: string,
  onEvent: (e: { progress: number; status: string; ready?: boolean; path?: string; error?: boolean }) => void,
): () => void {
  const url = `${BASE}/api/update/download?download_url=${encodeURIComponent(downloadUrl)}`;
  const es = new EventSource(url);
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
      if (data.ready || data.error) es.close();
    } catch {
      // ignore
    }
  };
  es.onerror = () => {
    onEvent({ progress: 0, status: "Connection error", error: true });
    es.close();
  };
  return () => es.close();
}

export async function applyUpdate(path: string): Promise<void> {
  await fetch(`${BASE}/api/update/apply?path=${encodeURIComponent(path)}`, { method: "POST" });
}
