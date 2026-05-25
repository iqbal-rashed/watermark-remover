import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
import { cn } from '../utils/cn';

interface SheetContextType {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const SheetContext = createContext<SheetContextType | null>(null);

export interface SheetProps {
  children: React.ReactNode;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export const Sheet: React.FC<SheetProps> = ({
  children,
  open: controlledOpen,
  defaultOpen = false,
  onOpenChange,
}) => {
  const [localOpen, setLocalOpen] = useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : localOpen;

  const setOpen = useCallback((val: boolean) => {
    if (!isControlled) {
      setLocalOpen(val);
    }
    onOpenChange?.(val);
  }, [isControlled, onOpenChange]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        setOpen(false);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, setOpen]);

  return (
    <SheetContext.Provider value={{ open, setOpen }}>
      {children}
    </SheetContext.Provider>
  );
};

export type SheetTriggerProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

export const SheetTrigger = React.forwardRef<HTMLButtonElement, SheetTriggerProps>(
  ({ className, onClick, ...props }, ref) => {
    const context = useContext(SheetContext);
    if (!context) throw new Error('SheetTrigger must be used inside Sheet');
    const { setOpen } = context;

    return (
      <button
        ref={ref}
        type="button"
        data-slot="sheet-trigger"
        onClick={(e) => {
          setOpen(true);
          onClick?.(e);
        }}
        className={cn(className)}
        {...props}
      />
    );
  }
);

SheetTrigger.displayName = 'SheetTrigger';

export type SheetCloseProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

export const SheetClose = React.forwardRef<HTMLButtonElement, SheetCloseProps>(
  ({ className, onClick, ...props }, ref) => {
    const context = useContext(SheetContext);
    if (!context) throw new Error('SheetClose must be used inside Sheet');
    const { setOpen } = context;

    return (
      <button
        ref={ref}
        type="button"
        data-slot="sheet-close"
        onClick={(e) => {
          setOpen(false);
          onClick?.(e);
        }}
        className={cn(className)}
        {...props}
      />
    );
  }
);

SheetClose.displayName = 'SheetClose';

export interface SheetContentProps extends React.HTMLAttributes<HTMLDivElement> {
  side?: 'top' | 'right' | 'bottom' | 'left';
  showCloseButton?: boolean;
}

export const SheetContent = React.forwardRef<HTMLDivElement, SheetContentProps>(
  ({ className, side = 'right', showCloseButton = true, children, ...props }, ref) => {
    const context = useContext(SheetContext);
    if (!context) throw new Error('SheetContent must be used inside Sheet');
    const { open, setOpen } = context;

    if (!open) return null;

    const sideStyles = {
      right: 'inset-y-0 right-0 h-full w-3/4 border-l sm:max-w-sm',
      left: 'inset-y-0 left-0 h-full w-3/4 border-r sm:max-w-sm',
      top: 'inset-x-0 top-0 h-auto border-b',
      bottom: 'inset-x-0 bottom-0 h-auto border-t',
    };

    return (
      <>
        {/* Backdrop Overlay */}
        <div
          className="fixed inset-0 z-50 bg-black/10 supports-[backdrop-filter]:backdrop-blur-[2px]"
          onClick={() => setOpen(false)}
        />
        {/* Drawer Panel */}
        <div
          ref={ref}
          data-slot="sheet-content"
          data-side={side}
          className={cn(
            'fixed z-50 flex flex-col gap-4 bg-background text-sm shadow-lg transition-transform duration-300',
            sideStyles[side],
            className
          )}
          {...props}
        >
          {children}
          {showCloseButton && (
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="absolute top-3 right-3 inline-flex size-7 items-center justify-center rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="size-4" />
              <span className="sr-only">Close</span>
            </button>
          )}
        </div>
      </>
    );
  }
);

SheetContent.displayName = 'SheetContent';

export type SheetHeaderProps = React.HTMLAttributes<HTMLDivElement>;

export const SheetHeader = React.forwardRef<HTMLDivElement, SheetHeaderProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="sheet-header"
        className={cn('flex flex-col gap-0.5 p-4', className)}
        {...props}
      />
    );
  }
);

SheetHeader.displayName = 'SheetHeader';

export type SheetFooterProps = React.HTMLAttributes<HTMLDivElement>;

export const SheetFooter = React.forwardRef<HTMLDivElement, SheetFooterProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="sheet-footer"
        className={cn('mt-auto flex flex-col gap-2 p-4', className)}
        {...props}
      />
    );
  }
);

SheetFooter.displayName = 'SheetFooter';

export type SheetTitleProps = React.HTMLAttributes<HTMLHeadingElement>;

export const SheetTitle = React.forwardRef<HTMLHeadingElement, SheetTitleProps>(
  ({ className, ...props }, ref) => {
    return (
      <h2
        ref={ref}
        data-slot="sheet-title"
        className={cn('text-base font-medium text-foreground', className)}
        {...props}
      />
    );
  }
);

SheetTitle.displayName = 'SheetTitle';

export type SheetDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

export const SheetDescription = React.forwardRef<HTMLParagraphElement, SheetDescriptionProps>(
  ({ className, ...props }, ref) => {
    return (
      <p
        ref={ref}
        data-slot="sheet-description"
        className={cn('text-sm text-muted-foreground', className)}
        {...props}
      />
    );
  }
);

SheetDescription.displayName = 'SheetDescription';