import React, { createContext, useContext, useState } from 'react';
import { cn } from '../utils/cn';

interface TabsContextType {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = createContext<TabsContextType | null>(null);

export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
}

export const Tabs = React.forwardRef<HTMLDivElement, TabsProps>(
  ({ className, defaultValue = '', value: controlledValue, onValueChange, children, ...props }, ref) => {
    const [localValue, setLocalValue] = useState(defaultValue);
    const isControlled = controlledValue !== undefined;
    const value = isControlled ? controlledValue : localValue;

    const handleValueChange = (val: string) => {
      if (!isControlled) {
        setLocalValue(val);
      }
      onValueChange?.(val);
    };

    return (
      <TabsContext.Provider value={{ value, onValueChange: handleValueChange }}>
        <div
          ref={ref}
          data-slot="tabs"
          className={cn('flex flex-col gap-2', className)}
          {...props}
        >
          {children}
        </div>
      </TabsContext.Provider>
    );
  }
);

Tabs.displayName = 'Tabs';

export interface TabsListProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline';
}

export const TabsList = React.forwardRef<HTMLDivElement, TabsListProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="tabs-list"
        data-variant={variant}
        role="tablist"
        className={cn(
          'inline-flex h-8 w-fit items-center justify-center rounded-lg p-[3px] text-muted-foreground',
          variant === 'default' ? 'bg-muted' : 'gap-1 bg-transparent rounded-none',
          className
        )}
        {...props}
      />
    );
  }
);

TabsList.displayName = 'TabsList';

export interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

export const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, ...props }, ref) => {
    const context = useContext(TabsContext);
    if (!context) throw new Error('TabsTrigger must be used inside Tabs');
    const { value: selectedValue, onValueChange } = context;
    const isActive = selectedValue === value;

    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        aria-selected={isActive}
        data-active={isActive ? 'true' : undefined}
        onClick={() => onValueChange(value)}
        className={cn(
          'relative inline-flex h-[calc(100%-1px)] flex-1 items-center justify-center gap-1.5 rounded-md border border-transparent px-1.5 py-0.5 text-sm font-medium whitespace-nowrap text-foreground/60 transition-all hover:text-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=\'size-\'])]:size-4',
          isActive && 'bg-background text-foreground shadow-sm dark:border-input dark:bg-input/30',
          className
        )}
        {...props}
      />
    );
  }
);

TabsTrigger.displayName = 'TabsTrigger';

export interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, ...props }, ref) => {
    const context = useContext(TabsContext);
    if (!context) throw new Error('TabsContent must be used inside Tabs');
    const { value: selectedValue } = context;

    if (selectedValue !== value) return null;

    return (
      <div
        ref={ref}
        data-slot="tabs-content"
        role="tabpanel"
        className={cn('flex-1 text-sm outline-none', className)}
        {...props}
      />
    );
  }
);

TabsContent.displayName = 'TabsContent';