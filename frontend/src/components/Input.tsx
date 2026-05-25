import React from 'react';
import { cn } from '../utils/cn';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        data-slot="input"
        className={cn(
          'h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-[3px] aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:disabled:bg-input/80',
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';

export type InputGroupProps = React.HTMLAttributes<HTMLDivElement>;

export const InputGroup = React.forwardRef<HTMLDivElement, InputGroupProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="input-group"
        role="group"
        className={cn(
          'relative flex h-8 w-full min-w-0 items-center rounded-lg border border-input transition-colors outline-none has-[:disabled]:bg-input/50 has-[:disabled]:opacity-50 has-[:focus-visible]:border-ring has-[:focus-visible]:ring-[3px] has-[:focus-visible]:ring-ring/50 dark:bg-input/30',
          className
        )}
        {...props}
      />
    );
  }
);

InputGroup.displayName = 'InputGroup';

export interface InputGroupAddonProps extends React.HTMLAttributes<HTMLDivElement> {
  align?: 'inline-start' | 'inline-end';
}

export const InputGroupAddon = React.forwardRef<HTMLDivElement, InputGroupAddonProps>(
  ({ className, align = 'inline-start', ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="input-group-addon"
        data-align={align}
        className={cn(
          'flex h-auto cursor-text items-center justify-center gap-2 py-1.5 text-sm font-medium text-muted-foreground select-none [&>svg:not([class*=\'size-\'])]:size-4',
          align === 'inline-start' ? 'order-first pl-2' : 'order-last pr-2',
          className
        )}
        {...props}
      />
    );
  }
);

InputGroupAddon.displayName = 'InputGroupAddon';

export type InputGroupInputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const InputGroupInput = React.forwardRef<HTMLInputElement, InputGroupInputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        data-slot="input-group-control"
        className={cn(
          'flex-1 h-full bg-transparent px-2.5 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      />
    );
  }
);

InputGroupInput.displayName = 'InputGroupInput';