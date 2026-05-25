import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { cn } from '../utils/cn';

interface SelectContextType {
  value: string;
  onValueChange: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
}

const SelectContext = createContext<SelectContextType | null>(null);

export interface SelectProps {
  children: React.ReactNode;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
}

export const Select: React.FC<SelectProps> = ({
  children,
  value: controlledValue,
  defaultValue,
  onValueChange,
}) => {
  const [localValue, setLocalValue] = useState(defaultValue ?? '');
  const [open, setOpen] = useState(false);
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : localValue;

  const containerRef = useRef<HTMLDivElement>(null);

  const handleValueChange = (val: string) => {
    if (!isControlled) {
      setLocalValue(val);
    }
    onValueChange?.(val);
    setOpen(false);
  };

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  return (
    <SelectContext.Provider value={{ value, onValueChange: handleValueChange, open, setOpen }}>
      <div
        ref={containerRef}
        data-slot="select"
        className="relative inline-block w-full"
      >
        {children}
      </div>
    </SelectContext.Provider>
  );
};

export interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'default' | 'sm';
}

export const SelectTrigger = React.forwardRef<HTMLButtonElement, SelectTriggerProps>(
  ({ className, size = 'default', children, ...props }, ref) => {
    const context = useContext(SelectContext);
    if (!context) throw new Error('SelectTrigger must be used inside Select');
    const { open, setOpen } = context;

    return (
      <button
        ref={ref}
        type="button"
        data-slot="select-trigger"
        data-size={size}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className={cn(
          'flex w-full items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent py-2 pr-2 pl-2.5 text-sm whitespace-nowrap transition-colors outline-none select-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30 dark:hover:bg-input/50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=\'size-\'])]:size-4',
          size === 'default' ? 'h-8' : 'h-7 rounded-md',
          className
        )}
        {...props}
      >
        {children}
        <ChevronDown className="pointer-events-none size-4 text-muted-foreground" />
      </button>
    );
  }
);

SelectTrigger.displayName = 'SelectTrigger';

export interface SelectValueProps {
  placeholder?: string;
}

export const SelectValue: React.FC<SelectValueProps> = ({ placeholder }) => {
  const context = useContext(SelectContext);
  if (!context) throw new Error('SelectValue must be used inside Select');
  const { value } = context;

  return (
    <span
      data-slot="select-value"
      data-placeholder={!value ? 'true' : undefined}
      className={cn(!value && 'text-muted-foreground')}
    >
      {value || placeholder}
    </span>
  );
};

export type SelectContentProps = React.HTMLAttributes<HTMLDivElement>;

export const SelectContent = React.forwardRef<HTMLDivElement, SelectContentProps>(
  ({ className, children, ...props }, ref) => {
    const context = useContext(SelectContext);
    if (!context) throw new Error('SelectContent must be used inside Select');
    const { open } = context;

    if (!open) return null;

    return (
      <div
        ref={ref}
        data-slot="select-content"
        className={cn(
          'absolute top-full left-0 z-50 mt-1 min-w-36 overflow-hidden rounded-lg bg-popover text-popover-foreground shadow-md ring-1 ring-foreground/10 border border-border p-1',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

SelectContent.displayName = 'SelectContent';

export interface SelectItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export const SelectItem = React.forwardRef<HTMLDivElement, SelectItemProps>(
  ({ className, children, value, ...props }, ref) => {
    const context = useContext(SelectContext);
    if (!context) throw new Error('SelectItem must be used inside Select');
    const { value: selectedValue, onValueChange } = context;
    const isSelected = selectedValue === value;

    return (
      <div
        ref={ref}
        data-slot="select-item"
        role="option"
        aria-selected={isSelected}
        onClick={() => onValueChange(value)}
        className={cn(
          'relative flex w-full cursor-default items-center gap-1.5 rounded-md py-1 pr-8 pl-1.5 text-sm outline-none select-none hover:bg-accent hover:text-accent-foreground',
          className
        )}
        {...props}
      >
        <span className="pointer-events-none absolute right-2 flex size-4 items-center justify-center">
          {isSelected && <Check className="size-4" />}
        </span>
        <span>{children}</span>
      </div>
    );
  }
);

SelectItem.displayName = 'SelectItem';

export type SelectGroupProps = React.HTMLAttributes<HTMLDivElement>;

export const SelectGroup = React.forwardRef<HTMLDivElement, SelectGroupProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="select-group"
        className={cn('p-1', className)}
        {...props}
      />
    );
  }
);

SelectGroup.displayName = 'SelectGroup';

export type SelectLabelProps = React.HTMLAttributes<HTMLDivElement>;

export const SelectLabel = React.forwardRef<HTMLDivElement, SelectLabelProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="select-label"
        className={cn('px-1.5 py-1 text-xs text-muted-foreground', className)}
        {...props}
      />
    );
  }
);

SelectLabel.displayName = 'SelectLabel';

export type SelectSeparatorProps = React.HTMLAttributes<HTMLDivElement>;

export const SelectSeparator = React.forwardRef<HTMLDivElement, SelectSeparatorProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="select-separator"
        className={cn('-mx-1 my-1 h-px bg-border', className)}
        {...props}
      />
    );
  }
);

SelectSeparator.displayName = 'SelectSeparator';