import { useState, useCallback, useEffect, useRef } from 'react';
import { AppState, MediaType, MediaInfo, MaskBox, ProcessOptions, SelectionMethod } from '../components/types';
import { uploadFile, getPreviewUrl, getDownloadUrl, streamDetect, streamProcess } from '../utils/api';
import { toast } from 'sonner';

export function useWatermarkApp() {
  const [appState, setAppState] = useState<AppState>('idle');
  const [media, setMedia] = useState<MediaInfo | null>(null);
  const [box, setBox] = useState<MaskBox | null>(null);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [resultFilename, setResultFilename] = useState<string>('');
  const [selectionMethod, setSelectionMethod] = useState<SelectionMethod>('draw');
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionProgress, setDetectionProgress] = useState(0);
  const [detectionStatus, setDetectionStatus] = useState('');
  const [options, setOptions] = useState<ProcessOptions>({
    fillMode: 'inpaint',
    outputFormat: 'png',
    videoQuality: 80,
    maxBboxPercent: 10,
  });

  // file_id from the backend after upload
  const fileIdRef = useRef<string | null>(null);
  const urlsRef = useRef<string[]>([]);
  const cleanupRef = useRef<(() => void) | null>(null);

  const trackUrl = (url: string) => { urlsRef.current.push(url); return url; };

  useEffect(() => {
    return () => {
      urlsRef.current.forEach((u) => URL.revokeObjectURL(u));
      cleanupRef.current?.();
    };
  }, []);

  // ── Upload ─────────────────────────────────────────────────────────────────

  const handleUpload = useCallback(async (file: File) => {
    const isVideo = file.type.startsWith('video/');
    const isImage = file.type.startsWith('image/');
    if (!isVideo && !isImage) {
      toast.error('Unsupported file type');
      return;
    }

    // Keep a local blob URL for immediate preview while upload runs
    const localUrl = trackUrl(URL.createObjectURL(file));
    const type: MediaType = isVideo ? 'video' : 'image';

    try {
      // Get dimensions from local URL
      let naturalWidth = 0, naturalHeight = 0;
      if (type === 'image') {
        const dims = await new Promise<{ w: number; h: number }>((res, rej) => {
          const img = new Image();
          img.onload = () => res({ w: img.naturalWidth, h: img.naturalHeight });
          img.onerror = rej;
          img.src = localUrl;
        });
        naturalWidth = dims.w;
        naturalHeight = dims.h;
        setOptions((o) => ({ ...o, outputFormat: 'png' }));
      } else {
        const dims = await new Promise<{ w: number; h: number; d: number }>((res, rej) => {
          const v = document.createElement('video');
          v.preload = 'metadata';
          v.muted = true;
          v.src = localUrl;
          v.onloadedmetadata = () => res({ w: v.videoWidth, h: v.videoHeight, d: v.duration });
          v.onerror = rej;
        });
        naturalWidth = dims.w;
        naturalHeight = dims.h;
        setOptions((o) => ({ ...o, outputFormat: 'mp4' }));
      }

      // Upload to backend
      toast.info('Uploading...');
      const result = await uploadFile(file);
      fileIdRef.current = result.file_id;

      // Use backend preview URL for the actual media display
      const serverUrl = getPreviewUrl(result.file_id);

      const info: MediaInfo = {
        file,
        url: serverUrl,
        type,
        naturalWidth,
        naturalHeight,
      };

      setMedia(info);
      setBox(null);
      setSelectionMethod('draw');
      setAppState('editing');
      toast.success(`${type === 'image' ? 'Image' : 'Video'} loaded`);
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || 'Failed to load file');
    }
  }, []);

  // ── Auto-detect ────────────────────────────────────────────────────────────

  const handleAutoDetect = useCallback(async () => {
    const fileId = fileIdRef.current;
    if (!fileId) { toast.error('Upload a file first'); return; }

    setIsDetecting(true);
    setDetectionProgress(0);
    setDetectionStatus('Preparing…');

    cleanupRef.current?.();

    await new Promise<void>((resolve) => {
      const cleanup = streamDetect(fileId, options.maxBboxPercent, (event) => {
        setDetectionProgress(event.progress);
        setDetectionStatus(event.status);

        if (event.error) {
          toast.error(event.status || 'Detection failed');
          setIsDetecting(false);
          setDetectionProgress(0);
          setDetectionStatus('');
          resolve();
          return;
        }

        if (event.box) {
          const [x1, y1, x2, y2] = event.box;
          if (x1 === 0 && y1 === 0 && x2 === 0 && y2 === 0) {
            toast.warning('Could not auto-detect watermark. Try Draw or Manual.');
          } else {
            setBox({ x1, y1, x2, y2 });
            toast.success('Watermark detected');
          }
          setIsDetecting(false);
          setDetectionProgress(0);
          setDetectionStatus('');
          resolve();
        }
      });
      cleanupRef.current = () => { cleanup(); resolve(); };
    });
  }, [options.maxBboxPercent]);

  // ── Manual box ─────────────────────────────────────────────────────────────

  const handleManualBox = useCallback(
    (text: string) => {
      if (!media) return false;
      const parts = text.split(',').map((s) => parseInt(s.trim(), 10));
      if (parts.length !== 4 || parts.some(isNaN)) {
        toast.error('Format must be: x1, y1, x2, y2');
        return false;
      }
      const [x1, y1, x2, y2] = parts;
      if (x2 <= x1 || y2 <= y1) {
        toast.error('x2 must be > x1, y2 must be > y1');
        return false;
      }
      setBox({
        x1: Math.max(0, Math.min(media.naturalWidth, x1)),
        y1: Math.max(0, Math.min(media.naturalHeight, y1)),
        x2: Math.max(0, Math.min(media.naturalWidth, x2)),
        y2: Math.max(0, Math.min(media.naturalHeight, y2)),
      });
      toast.success('Region set');
      return true;
    },
    [media]
  );

  // ── Process ────────────────────────────────────────────────────────────────

  const handleProcess = useCallback(async () => {
    const fileId = fileIdRef.current;
    if (!fileId || !box) {
      toast.error('Select a watermark region first');
      return;
    }
    const w = box.x2 - box.x1, h = box.y2 - box.y1;
    if (w < 2 || h < 2) {
      toast.error('Selection is too small');
      return;
    }

    setAppState('processing');
    setProgress(0);
    setStatusText('Starting...');

    const maskBoxStr = `${box.x1},${box.y1},${box.x2},${box.y2}`;
    const transparent = options.fillMode === 'transparent';

    // Map frontend format to backend
    const formatMap: Record<string, string> = { png: 'PNG', jpg: 'JPG', webp: 'WEBP', mp4: 'MP4', avi: 'AVI' };
    const forceFormat = formatMap[options.outputFormat?.toLowerCase()] ?? undefined;

    await new Promise<void>((resolve) => {
      const cleanup = streamProcess(
        {
          fileId,
          maskBox: maskBoxStr,
          transparent,
          forceFormat,
          maxBboxPercent: options.maxBboxPercent,
        },
        (event) => {
          setProgress(event.progress);
          setStatusText(event.status);

          if (event.error) {
            toast.error(event.status || 'Processing failed');
            setAppState('editing');
            resolve();
            return;
          }

          if (event.output_id) {
            const downloadUrl = getDownloadUrl(event.output_id);
            setResultUrl(downloadUrl);
            setResultFilename(event.filename || 'result');
            setProgress(100);
            setAppState('done');
            toast.success('Done! Ready to download.');
            resolve();
          }
        }
      );
      cleanupRef.current = () => { cleanup(); resolve(); };
    });
  }, [box, options]);

  // ── Reset ──────────────────────────────────────────────────────────────────

  const handleReset = useCallback(() => {
    cleanupRef.current?.();
    fileIdRef.current = null;
    setAppState('idle');
    setMedia(null);
    setBox(null);
    setResultUrl(null);
    setResultFilename('');
    setProgress(0);
    setStatusText('');
    setSelectionMethod('draw');
    setIsDetecting(false);
    setDetectionProgress(0);
    setDetectionStatus('');
  }, []);

  return {
    appState, media, box, setBox, options, setOptions, progress, statusText,
    resultUrl, resultFilename, selectionMethod, setSelectionMethod,
    isDetecting, detectionProgress, detectionStatus,
    handleUpload, handleAutoDetect, handleManualBox, handleProcess, handleReset,
  };
}
