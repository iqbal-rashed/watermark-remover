import React from 'react';
import { Progress } from './Progress';
import { Wand2 } from 'lucide-react';
interface ProcessingStateProps {
  progress: number;
  statusText: string;
}
export function ProcessingState({
  progress,
  statusText
}: ProcessingStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-muted/30">
      <div className="w-full max-w-md flex flex-col items-center">
        <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-6">
          <Wand2 className="w-8 h-8 text-primary animate-pulse" />
        </div>

        <h2 className="text-xl font-heading font-semibold mb-2 text-center">
          Processing
        </h2>
        <p className="text-sm text-muted-foreground mb-8 text-center min-h-[20px]">
          {statusText}
        </p>

        <div className="w-full space-y-2">
          <Progress value={progress} className="h-2 w-full" />
          <div className="flex justify-between text-xs text-muted-foreground font-mono">
            <span>{Math.round(progress)}%</span>
            <span>100%</span>
          </div>
        </div>
      </div>
    </div>);

}