import React, { useEffect, useState } from 'react';
import {
  MaskBox,
  ProcessOptions,
  MediaInfo,
  FillMode,
  SelectionMethod } from
'./types';
import { Label } from './Label';
import { Input } from './Input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue } from
'./Select';
import { Separator } from './Separator';
import { Button } from './Button';
import {
  Wand2,
  Trash2,
  FileImage,
  FileVideo,
  MousePointer2,
  Sparkles,
  Hash,
  Loader2 } from
'lucide-react';
import { ScrollArea } from './ScrollArea';
interface OptionsPanelProps {
  media: MediaInfo;
  box: MaskBox | null;
  setBox: (b: MaskBox) => void;
  options: ProcessOptions;
  setOptions: (o: ProcessOptions) => void;
  selectionMethod: SelectionMethod;
  setSelectionMethod: (m: SelectionMethod) => void;
  isDetecting: boolean;
  onAutoDetect: () => void;
  onManualBox: (text: string) => boolean;
  onProcess: () => void;
  onClearBox: () => void;
}
export function OptionsPanel({
  media,
  box,
  setBox,
  options,
  setOptions,
  selectionMethod,
  setSelectionMethod,
  isDetecting,
  onAutoDetect,
  onManualBox,
  onProcess,
  onClearBox
}: OptionsPanelProps) {
  const [manualText, setManualText] = useState('');
  useEffect(() => {
    if (box && selectionMethod === 'manual') {
      setManualText(`${box.x1}, ${box.y1}, ${box.x2}, ${box.y2}`);
    }
  }, [box, selectionMethod]);
  const updateCoord = (key: keyof MaskBox, raw: string) => {
    if (!box) return;
    const v = parseInt(raw, 10);
    if (isNaN(v)) return;
    const max =
    key === 'x1' || key === 'x2' ? media.naturalWidth : media.naturalHeight;
    setBox({
      ...box,
      [key]: Math.max(0, Math.min(max, v))
    });
  };
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };
  const methods: {
    v: SelectionMethod;
    label: string;
    icon: React.ReactNode;
  }[] = [
  {
    v: 'draw',
    label: 'Draw',
    icon: <MousePointer2 className="w-3.5 h-3.5" />
  },
  {
    v: 'auto',
    label: 'Auto',
    icon: <Sparkles className="w-3.5 h-3.5" />
  },
  {
    v: 'manual',
    label: 'Manual',
    icon: <Hash className="w-3.5 h-3.5" />
  }];

  return (
    <aside className="w-full lg:w-80 shrink-0 border-l border-border bg-card flex flex-col">
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-5">
          {/* File info */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {media.type === 'image' ?
              <FileImage className="w-3 h-3" /> :

              <FileVideo className="w-3 h-3" />
              }
              File
            </div>
            <div className="bg-muted/50 rounded-md p-3 space-y-1.5 text-xs">
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">Name</span>
                <span className="truncate font-medium" title={media.file.name}>
                  {media.file.name}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Size</span>
                <span className="font-mono">
                  {formatBytes(media.file.size)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Dimensions</span>
                <span className="font-mono">
                  {media.naturalWidth} × {media.naturalHeight}
                </span>
              </div>
              {media.duration &&
              <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration</span>
                  <span className="font-mono">
                    {media.duration.toFixed(1)}s
                  </span>
                </div>
              }
            </div>
          </div>

          <Separator />

          {/* Selection method */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Selection Method
            </h3>
            <div className="grid grid-cols-3 gap-1 bg-muted/50 p-1 rounded-md">
              {methods.map((m) =>
              <button
                key={m.v}
                onClick={() => setSelectionMethod(m.v)}
                className={`
                    flex items-center justify-center gap-1.5 text-xs py-1.5 rounded transition-colors
                    ${selectionMethod === m.v ? 'bg-background text-foreground shadow-sm font-medium' : 'text-muted-foreground hover:text-foreground'}
                  `}>
                
                  {m.icon}
                  {m.label}
                </button>
              )}
            </div>

            {/* Draw mode */}
            {selectionMethod === 'draw' &&
            <p className="text-[11px] text-muted-foreground bg-muted/50 rounded-md p-2.5 leading-relaxed">
                Click and drag on the {media.type} to draw a rectangle around
                the watermark. Drag corners to resize, drag center to move.
              </p>
            }

            {/* Auto mode */}
            {selectionMethod === 'auto' &&
            <div className="space-y-2.5">
                <div className="space-y-1.5">
                  <Label className="text-[11px] text-muted-foreground">
                    Max bounding box (%)
                  </Label>
                  <Input
                  type="number"
                  min={1}
                  max={50}
                  value={options.maxBboxPercent}
                  onChange={(e) =>
                  setOptions({
                    ...options,
                    maxBboxPercent: Math.max(
                      1,
                      Math.min(50, parseInt(e.target.value) || 10)
                    )
                  })
                  }
                  className="h-8 text-xs font-mono" />
                
                </div>
                <Button
                onClick={onAutoDetect}
                disabled={isDetecting}
                variant="outline"
                size="sm"
                className="w-full gap-1.5">
                
                  {isDetecting ?
                <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Detecting...
                    </> :

                <>
                      <Sparkles className="w-3.5 h-3.5" />
                      Detect Watermark
                    </>
                }
                </Button>
                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  Scans the {media.type === 'video' ? 'first frame' : 'image'}{' '}
                  for high-edge regions, biased toward corners.
                </p>
              </div>
            }

            {/* Manual mode */}
            {selectionMethod === 'manual' &&
            <div className="space-y-2">
                <Label className="text-[11px] text-muted-foreground">
                  Mask box (x1, y1, x2, y2)
                </Label>
                <Input
                placeholder="e.g. 120, 430, 980, 540"
                value={manualText}
                onChange={(e) => setManualText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onManualBox(manualText);
                }}
                className="font-mono text-xs h-8" />
              
                <Button
                onClick={() => onManualBox(manualText)}
                variant="outline"
                size="sm"
                className="w-full">
                
                  Apply Coordinates
                </Button>
              </div>
            }
          </div>

          <Separator />

          {/* Current selection */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Selection
              </h3>
              {box &&
              <button
                onClick={onClearBox}
                className="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1">
                
                  <Trash2 className="w-3 h-3" />
                  Clear
                </button>
              }
            </div>

            {box ?
            <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-[10px] text-muted-foreground">
                    X1
                  </Label>
                  <Input
                  type="number"
                  value={box.x1}
                  onChange={(e) => updateCoord('x1', e.target.value)}
                  className="font-mono h-8 text-xs" />
                
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px] text-muted-foreground">
                    Y1
                  </Label>
                  <Input
                  type="number"
                  value={box.y1}
                  onChange={(e) => updateCoord('y1', e.target.value)}
                  className="font-mono h-8 text-xs" />
                
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px] text-muted-foreground">
                    X2
                  </Label>
                  <Input
                  type="number"
                  value={box.x2}
                  onChange={(e) => updateCoord('x2', e.target.value)}
                  className="font-mono h-8 text-xs" />
                
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px] text-muted-foreground">
                    Y2
                  </Label>
                  <Input
                  type="number"
                  value={box.y2}
                  onChange={(e) => updateCoord('y2', e.target.value)}
                  className="font-mono h-8 text-xs" />
                
                </div>
              </div> :

            <p className="text-xs text-muted-foreground bg-muted/50 rounded-md p-3 text-center">
                No region selected yet.
              </p>
            }
          </div>

          <Separator />

          {/* Fill mode */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Fill Method
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {(
              [
              {
                v: 'inpaint',
                label: 'Smart Fill'
              },
              {
                v: 'blur',
                label: 'Average'
              },
              {
                v: 'white',
                label: 'White'
              },
              {
                v: 'black',
                label: 'Black'
              },
              ...(media.type === 'image' ?
              [
              {
                v: 'transparent',
                label: 'Transparent'
              }] :

              [])] as
              {
                v: FillMode;
                label: string;
              }[]).
              map((opt) =>
              <button
                key={opt.v}
                onClick={() =>
                setOptions({
                  ...options,
                  fillMode: opt.v
                })
                }
                className={`
                    text-xs py-2 px-3 rounded-md border transition-colors text-left
                    ${options.fillMode === opt.v ? 'border-primary bg-primary/10 text-foreground font-medium' : 'border-border bg-background hover:bg-accent text-muted-foreground'}
                  `}>
                
                  {opt.label}
                </button>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              {options.fillMode === 'inpaint' &&
              'Blends colors from surrounding pixels.'}
              {options.fillMode === 'blur' &&
              'Fills with average border color.'}
              {options.fillMode === 'white' &&
              'Fills the region with solid white.'}
              {options.fillMode === 'black' &&
              'Fills the region with solid black.'}
              {options.fillMode === 'transparent' &&
              'Makes region transparent (PNG only).'}
            </p>
          </div>

          <Separator />

          {/* Output */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Output
            </h3>
            <div className="space-y-2">
              <Label className="text-xs">Format</Label>
              <Select
                value={options.outputFormat}
                onValueChange={(v) =>
                setOptions({
                  ...options,
                  outputFormat: v
                })
                }>
                
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {media.type === 'image' ?
                  <>
                      <SelectItem value="png">PNG</SelectItem>
                      <SelectItem value="jpeg">JPEG</SelectItem>
                      <SelectItem value="webp">WEBP</SelectItem>
                    </> :

                  <SelectItem value="webm">WEBM</SelectItem>
                  }
                </SelectContent>
              </Select>
              {media.type === 'video' &&
              <p className="text-[11px] text-muted-foreground">
                  Output is encoded in browser as WEBM (VP8/VP9).
                </p>
              }
            </div>
          </div>
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-border bg-background">
        <Button
          onClick={onProcess}
          disabled={!box}
          className="w-full gap-2"
          size="lg">
          
          <Wand2 className="w-4 h-4" />
          Remove Watermark
        </Button>
        {!box &&
        <p className="text-[11px] text-muted-foreground text-center mt-2">
            Select a region to enable processing
          </p>
        }
      </div>
    </aside>);

}