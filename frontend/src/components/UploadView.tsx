import React, { useCallback, useState, useRef } from 'react';
import { Upload, FileImage, FileVideo } from 'lucide-react';
import { toast } from 'sonner';
interface UploadViewProps {
  onUpload: (file: File) => void;
}
export function UploadView({ onUpload }: UploadViewProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const handleFile = useCallback(
    (file: File) => {
      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');
      if (!isImage && !isVideo) {
        toast.error('Unsupported file type. Please upload an image or video.');
        return;
      }
      onUpload(file);
    },
    [onUpload]
  );
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };
  return (
    <div className="flex-1 flex items-center justify-center p-6 bg-muted/30">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <h1 className="font-heading text-3xl font-semibold tracking-tight mb-2">
            Remove watermarks from images & videos
          </h1>
          <p className="text-muted-foreground">
            Upload your media to get started. Drag a region over the watermark,
            then export.
          </p>
        </div>

        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
          }}
          className={`
            rounded-2xl border-2 border-dashed transition-all cursor-pointer
            flex flex-col items-center justify-center gap-4 p-12 min-h-[320px]
            ${isDragging ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-border hover:border-primary/40 hover:bg-accent/30 bg-card'}
          `}>
          
          <input
            ref={inputRef}
            type="file"
            accept="image/*,video/*"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFile(e.target.files[0]);
              e.target.value = '';
            }} />
          

          <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
            <Upload className="w-7 h-7" />
          </div>

          <div className="text-center">
            <p className="font-semibold text-lg mb-1">
              {isDragging ? 'Drop to upload' : 'Drop a file or click to browse'}
            </p>
            <p className="text-sm text-muted-foreground">
              Supports JPG, PNG, WEBP, MP4, WEBM, MOV — up to 2GB
            </p>
          </div>

          <div className="flex gap-2 mt-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted px-2.5 py-1 rounded-full">
              <FileImage className="w-3 h-3" /> Image
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted px-2.5 py-1 rounded-full">
              <FileVideo className="w-3 h-3" /> Video
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-8 text-center">
          <div className="space-y-1">
            <div className="text-xs font-semibold text-foreground">
              1. Upload
            </div>
            <p className="text-xs text-muted-foreground">Drop image or video</p>
          </div>
          <div className="space-y-1">
            <div className="text-xs font-semibold text-foreground">
              2. Select
            </div>
            <p className="text-xs text-muted-foreground">
              Drag to crop watermark
            </p>
          </div>
          <div className="space-y-1">
            <div className="text-xs font-semibold text-foreground">
              3. Export
            </div>
            <p className="text-xs text-muted-foreground">
              Download cleaned file
            </p>
          </div>
        </div>
      </div>
    </div>);

}