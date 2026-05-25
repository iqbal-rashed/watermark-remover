import React, { useState, createElement } from 'react';
import { Download, CheckCircle2, RotateCcw, Eye } from 'lucide-react';
import { Button } from './Button';
import { MediaType } from './types';
interface ResultViewProps {
  resultUrl: string;
  originalUrl: string;
  mediaType: MediaType;
  filename: string;
  onReset: () => void;
}
export function ResultView({
  resultUrl,
  originalUrl,
  mediaType,
  filename,
  onReset
}: ResultViewProps) {
  const [showOriginal, setShowOriginal] = useState(false);
  const displayUrl = showOriginal ? originalUrl : resultUrl;
  return (
    <div className="flex-1 flex flex-col bg-muted/30 overflow-hidden">
      {/* Top status bar */}
      <div className="border-b border-border bg-card px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-green-500/15 text-green-600 flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <span className="font-medium text-sm">Watermark removed</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onMouseDown={() => setShowOriginal(true)}
            onMouseUp={() => setShowOriginal(false)}
            onMouseLeave={() => setShowOriginal(false)}
            onTouchStart={() => setShowOriginal(true)}
            onTouchEnd={() => setShowOriginal(false)}
            className="gap-1.5">
            
            <Eye className="w-3.5 h-3.5" />
            Hold to compare
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onReset}
            className="gap-1.5">
            
            <RotateCcw className="w-3.5 h-3.5" />
            New
          </Button>
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => {
              const a = document.createElement('a');
              a.href = resultUrl;
              a.download = filename;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
            }}>
            
            <Download className="w-3.5 h-3.5" />
            Download
          </Button>
        </div>
      </div>

      {/* Media area */}
      <div
        className="flex-1 flex items-center justify-center p-6 overflow-hidden relative"
        style={{
          backgroundImage:
          'linear-gradient(45deg, hsl(var(--muted)) 25%, transparent 25%), linear-gradient(-45deg, hsl(var(--muted)) 25%, transparent 25%), linear-gradient(45deg, transparent 75%, hsl(var(--muted)) 75%), linear-gradient(-45deg, transparent 75%, hsl(var(--muted)) 75%)',
          backgroundSize: '20px 20px',
          backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px'
        }}>
        
        {mediaType === 'image' ?
        <img
          src={displayUrl}
          alt={showOriginal ? 'Original' : 'Cleaned'}
          className="max-w-full max-h-full object-contain shadow-lg" /> :


        <video
          key={displayUrl}
          src={displayUrl}
          controls
          autoPlay
          loop
          className="max-w-full max-h-full shadow-lg" />

        }

        {showOriginal &&
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-foreground text-background text-xs font-medium px-3 py-1 rounded-full">
            Original
          </div>
        }
      </div>
    </div>);

}