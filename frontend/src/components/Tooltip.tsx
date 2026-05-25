import React, { createContext, useContext, useState } from 'react';
import { cn } from '../utils/cn';

interface TooltipContextType {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const TooltipContext = createContext<TooltipContextType | null>(null);

export const TooltipProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};

export interface TooltipProps {
  children: React.ReactNode;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export const Tooltip: React.FC<TooltipProps> = ({
  children,
  open: controlledOpen,
  defaultOpen = false,
  onOpenChange,
}) => {
  const [localOpen, setLocalOpen] = useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : localOpen;

  const setOpen = (val: boolean) => {
    if (!isControlled) {
      setLocalOpen(val);
    }
    onOpenChange?.(val);
  };

  return (
    <TooltipContext.Provider value={{ open, setOpen }}>
      <div className="relative inline-block">
        {children}
      </div>
    </TooltipContext.Provider>
  );
};

export type TooltipTriggerProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

export const TooltipTrigger = React.forwardRef<HTMLButtonElement, TooltipTriggerProps>(
  ({ className, onMouseEnter, onMouseLeave, ...props }, ref) => {
    const context = useContext(TooltipContext);
    if (!context) throw new Error('TooltipTrigger must be used inside Tooltip');
    const { setOpen } = context;

    return (
      <button
        ref={ref}
        type="button"
        data-slot="tooltip-trigger"
        onMouseEnter={(e) => {
          setOpen(true);
          onMouseEnter?.(e);
        }}
        onMouseLeave={(e) => {
          setOpen(false);
          onMouseLeave?.(e);
        }}
        className={cn(className)}
        {...props}
      />
    );
  }
);

TooltipTrigger.displayName = 'TooltipTrigger';

export type TooltipContentProps = React.HTMLAttributes<HTMLDivElement>;

export const TooltipContent = React.forwardRef<HTMLDivElement, TooltipContentProps>(
  ({ className, ...props }, ref) => {
    const context = useContext(TooltipContext);
    if (!context) throw new Error('TooltipContent must be used inside Tooltip');
    const { open } = context;

    if (!open) return null;

    return (
      <div
        ref={ref}
        data-slot="tooltip-content"
        className={cn(
          'absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 inline-flex w-fit max-w-xs items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-xs text-background shadow-md',
          className
        )}
        {...props}
      />
    );
  }
);

TooltipContent.displayName = 'TooltipContent';