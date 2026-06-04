import React, { useCallback, useEffect, useState, useRef } from "react";
import { MaskBox, MediaType } from "./types";
interface CropSelectorProps {
  mediaType: MediaType;
  mediaUrl: string;
  naturalWidth: number;
  naturalHeight: number;
  box: MaskBox | null;
  onBoxChange: (box: MaskBox) => void;
  drawingEnabled: boolean;
  isDetecting?: boolean;
  detectionProgress?: number;
  detectionStatus?: string;
}
type DragMode =
  | "none"
  | "create"
  | "move"
  | "resize-nw"
  | "resize-ne"
  | "resize-sw"
  | "resize-se";
export function CropSelector({
  mediaType,
  mediaUrl,
  naturalWidth,
  naturalHeight,
  box,
  onBoxChange,
  drawingEnabled,
  isDetecting = false,
  detectionProgress = 0,
  detectionStatus = "",
}: CropSelectorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mediaWrapRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [displayDims, setDisplayDims] = useState({
    width: 0,
    height: 0,
  });
  const [dragMode, setDragMode] = useState<DragMode>("none");
  const dragStartRef = useRef<{
    mx: number;
    my: number;
    box: MaskBox | null;
  }>({
    mx: 0,
    my: 0,
    box: null,
  });
  const updateDisplayDims = useCallback(() => {
    if (mediaWrapRef.current) {
      const el = mediaWrapRef.current.querySelector(
        "img, video",
      ) as HTMLElement | null;
      if (el) {
        const rect = el.getBoundingClientRect();
        setDisplayDims({
          width: rect.width,
          height: rect.height,
        });
      }
    }
  }, []);
  useEffect(() => {
    updateDisplayDims();
    window.addEventListener("resize", updateDisplayDims);
    return () => window.removeEventListener("resize", updateDisplayDims);
  }, [updateDisplayDims, mediaUrl]);
  // Convert displayed pixel coords -> natural image coords
  const toNatural = (
    px: number,
    py: number,
  ): {
    x: number;
    y: number;
  } => {
    if (displayDims.width === 0 || displayDims.height === 0)
      return {
        x: 0,
        y: 0,
      };
    return {
      x: Math.round((px / displayDims.width) * naturalWidth),
      y: Math.round((py / displayDims.height) * naturalHeight),
    };
  };
  // Convert natural -> displayed pixels (for rendering the box)
  const boxStyle = (() => {
    if (!box || displayDims.width === 0) return null;
    const sx = displayDims.width / naturalWidth;
    const sy = displayDims.height / naturalHeight;
    return {
      left: `${box.x1 * sx}px`,
      top: `${box.y1 * sy}px`,
      width: `${(box.x2 - box.x1) * sx}px`,
      height: `${(box.y2 - box.y1) * sy}px`,
    };
  })();
  const getMouseInMedia = (
    e: React.MouseEvent | MouseEvent,
  ): {
    x: number;
    y: number;
  } | null => {
    const wrap = mediaWrapRef.current?.querySelector(
      "img, video",
    ) as HTMLElement | null;
    if (!wrap) return null;
    const rect = wrap.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
    return {
      x,
      y,
    };
  };
  const onMouseDown = (e: React.MouseEvent, mode: DragMode) => {
    e.preventDefault();
    e.stopPropagation();
    const pos = getMouseInMedia(e);
    if (!pos) return;
    dragStartRef.current = {
      mx: pos.x,
      my: pos.y,
      box: box
        ? {
            ...box,
          }
        : null,
    };
    setDragMode(mode);
  };
  const onMediaMouseDown = (e: React.MouseEvent) => {
    if (dragMode !== "none") return;
    if (!drawingEnabled) return;
    const pos = getMouseInMedia(e);
    if (!pos) return;
    const nat = toNatural(pos.x, pos.y);
    // Start a new box
    const newBox: MaskBox = {
      x1: nat.x,
      y1: nat.y,
      x2: nat.x,
      y2: nat.y,
    };
    onBoxChange(newBox);
    dragStartRef.current = {
      mx: pos.x,
      my: pos.y,
      box: newBox,
    };
    setDragMode("create");
  };
  useEffect(() => {
    if (dragMode === "none") return;
    const onMove = (e: MouseEvent) => {
      const pos = getMouseInMedia(e);
      if (!pos) return;
      const start = dragStartRef.current;
      const dx = pos.x - start.mx;
      const dy = pos.y - start.my;
      const sx = displayDims.width / naturalWidth;
      const sy = displayDims.height / naturalHeight;
      const ndx = dx / sx;
      const ndy = dy / sy;
      if (dragMode === "create" && start.box) {
        const nat = toNatural(pos.x, pos.y);
        onBoxChange({
          x1: Math.min(start.box.x1, nat.x),
          y1: Math.min(start.box.y1, nat.y),
          x2: Math.max(start.box.x1, nat.x),
          y2: Math.max(start.box.y1, nat.y),
        });
      } else if (dragMode === "move" && start.box) {
        const w = start.box.x2 - start.box.x1;
        const h = start.box.y2 - start.box.y1;
        let nx1 = Math.round(start.box.x1 + ndx);
        let ny1 = Math.round(start.box.y1 + ndy);
        nx1 = Math.max(0, Math.min(naturalWidth - w, nx1));
        ny1 = Math.max(0, Math.min(naturalHeight - h, ny1));
        onBoxChange({
          x1: nx1,
          y1: ny1,
          x2: nx1 + w,
          y2: ny1 + h,
        });
      } else if (start.box && dragMode.startsWith("resize-")) {
        let { x1, y1, x2, y2 } = start.box;
        if (dragMode === "resize-nw") {
          x1 = Math.round(x1 + ndx);
          y1 = Math.round(y1 + ndy);
        }
        if (dragMode === "resize-ne") {
          x2 = Math.round(x2 + ndx);
          y1 = Math.round(y1 + ndy);
        }
        if (dragMode === "resize-sw") {
          x1 = Math.round(x1 + ndx);
          y2 = Math.round(y2 + ndy);
        }
        if (dragMode === "resize-se") {
          x2 = Math.round(x2 + ndx);
          y2 = Math.round(y2 + ndy);
        }
        // Normalize
        const nx1 = Math.max(0, Math.min(x1, x2));
        const ny1 = Math.max(0, Math.min(y1, y2));
        const nx2 = Math.min(naturalWidth, Math.max(x1, x2));
        const ny2 = Math.min(naturalHeight, Math.max(y1, y2));
        onBoxChange({
          x1: nx1,
          y1: ny1,
          x2: nx2,
          y2: ny2,
        });
      }
    };
    const onUp = () => setDragMode("none");
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragMode, displayDims, naturalWidth, naturalHeight, onBoxChange]);
  const handleSize = 12;
  const handles: {
    mode: DragMode;
    style: React.CSSProperties;
    cursor: string;
  }[] = [
    {
      mode: "resize-nw",
      style: {
        left: -handleSize / 2,
        top: -handleSize / 2,
      },
      cursor: "nwse-resize",
    },
    {
      mode: "resize-ne",
      style: {
        right: -handleSize / 2,
        top: -handleSize / 2,
      },
      cursor: "nesw-resize",
    },
    {
      mode: "resize-sw",
      style: {
        left: -handleSize / 2,
        bottom: -handleSize / 2,
      },
      cursor: "nesw-resize",
    },
    {
      mode: "resize-se",
      style: {
        right: -handleSize / 2,
        bottom: -handleSize / 2,
      },
      cursor: "nwse-resize",
    },
  ];

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full flex items-center justify-center select-none overflow-hidden"
      style={{
        backgroundImage:
          "linear-gradient(45deg, hsl(var(--muted)) 25%, transparent 25%), linear-gradient(-45deg, hsl(var(--muted)) 25%, transparent 25%), linear-gradient(45deg, transparent 75%, hsl(var(--muted)) 75%), linear-gradient(-45deg, transparent 75%, hsl(var(--muted)) 75%)",
        backgroundSize: "20px 20px",
        backgroundPosition: "0 0, 0 10px, 10px -10px, -10px 0px",
        backgroundColor: "var(--muted)",
      }}
    >
      <div
        ref={mediaWrapRef}
        className="relative inline-block shadow-lg"
        style={{
          maxWidth: "100%",
          maxHeight: "100%",
        }}
      >
        {mediaType === "image" ? (
          <img
            src={mediaUrl}
            alt="Source"
            className={`block max-w-full max-h-[calc(100vh-260px)] ${drawingEnabled ? "cursor-crosshair" : "cursor-default"}`}
            draggable={false}
            onLoad={updateDisplayDims}
            onMouseDown={onMediaMouseDown}
          />
        ) : (
          <video
            ref={videoRef}
            src={mediaUrl}
            controls={false}
            muted
            playsInline
            className={`block max-w-full max-h-[calc(100vh-260px)] ${drawingEnabled ? "cursor-crosshair" : "cursor-default"}`}
            onLoadedMetadata={updateDisplayDims}
            onMouseDown={onMediaMouseDown}
          />
        )}

        {boxStyle && (
          <div
            className="absolute border-2 border-red-500 bg-red-500/10"
            style={{
              ...boxStyle,
              boxShadow: "0 0 0 9999px rgba(0,0,0,0.35)",
              cursor: dragMode === "move" ? "grabbing" : "grab",
            }}
            onMouseDown={(e) => onMouseDown(e, "move")}
          >
            {/* Animated dashed inner border */}
            <div className="absolute inset-0 border border-dashed border-white/80 pointer-events-none" />

            {/* Corner handles */}
            {handles.map((h) => (
              <div
                key={h.mode}
                onMouseDown={(e) => onMouseDown(e, h.mode)}
                style={{
                  position: "absolute",
                  width: handleSize,
                  height: handleSize,
                  cursor: h.cursor,
                  ...h.style,
                }}
                className="bg-white border-2 border-red-500 rounded-sm hover:scale-125 transition-transform"
              />
            ))}

            {/* Coordinate label */}
            <div className="absolute -top-7 left-0 bg-red-500 text-white text-[10px] font-mono px-1.5 py-0.5 rounded whitespace-nowrap pointer-events-none">
              {Math.round(box!.x2 - box!.x1)} × {Math.round(box!.y2 - box!.y1)}
            </div>
          </div>
        )}
      </div>

      {!box && drawingEnabled && !isDetecting && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-foreground text-background text-xs px-3 py-1.5 rounded-full font-medium pointer-events-none animate-pulse">
          Drag on the {mediaType} to select the watermark area
        </div>
      )}
      {!box && !drawingEnabled && !isDetecting && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-foreground text-background text-xs px-3 py-1.5 rounded-full font-medium pointer-events-none">
          Use the side panel to select the watermark area
        </div>
      )}

      {/* Auto-detect overlay */}
      {isDetecting && (
        <div className="absolute inset-0 bg-background/70 backdrop-blur-[2px] flex items-center justify-center z-20 pointer-events-auto">
          <div className="bg-card border border-border rounded-xl shadow-xl px-6 py-5 w-[min(420px,calc(100%-2rem))]">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                <svg
                  className="w-4 h-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold">Detecting watermark</div>
                <div className="text-xs text-muted-foreground truncate">
                  {detectionStatus || "Analyzing…"}
                </div>
              </div>
              <div className="text-xs font-mono text-muted-foreground tabular-nums">
                {Math.round(detectionProgress)}%
              </div>
            </div>
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-200 ease-out"
                style={{
                  width: `${Math.max(2, detectionProgress)}%`,
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
