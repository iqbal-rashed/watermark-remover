import React from 'react';
import { cn } from '../utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'secondary' | 'ghost' | 'destructive' | 'link';
  size?: 'default' | 'xs' | 'sm' | 'lg' | 'icon' | 'icon-xs' | 'icon-sm' | 'icon-lg';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', type = 'button', ...props }, ref) => {
    const variantStyles = {
      default: 'bg-primary text-primary-foreground hover:bg-primary/80',
      outline: 'border-border bg-background hover:bg-muted hover:text-foreground dark:border-input dark:bg-input/30 dark:hover:bg-input/50',
      secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
      ghost: 'hover:bg-muted hover:text-foreground dark:hover:bg-muted/50',
      destructive: 'bg-destructive/10 text-destructive hover:bg-destructive/20 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:hover:bg-destructive/30 dark:focus-visible:ring-destructive/40',
      link: 'text-primary underline-offset-4 hover:underline',
    };

    const sizeStyles = {
      default: 'h-8 gap-1.5 px-2.5 has-[[data-icon=inline-end]]:pr-2 has-[[data-icon=inline-start]]:pl-2',
      xs: 'h-6 gap-1 rounded-md px-2 text-xs has-[[data-icon=inline-end]]:pr-1.5 has-[[data-icon=inline-start]]:pl-1.5 [&_svg:not([class*=\'size-\'])]:size-3',
      sm: 'h-7 gap-1 rounded-md px-2.5 text-[0.8rem] has-[[data-icon=inline-end]]:pr-1.5 has-[[data-icon=inline-start]]:pl-1.5 [&_svg:not([class*=\'size-\'])]:size-3.5',
      lg: 'h-9 gap-1.5 px-2.5 has-[[data-icon=inline-end]]:pr-3 has-[[data-icon=inline-start]]:pl-3',
      icon: 'size-8',
      'icon-xs': 'size-6 rounded-md [&_svg:not([class*=\'size-\'])]:size-3',
      'icon-sm': 'size-7 rounded-md',
      'icon-lg': 'size-9',
    };

    return (
      <button
        ref={ref}
        type={type}
        data-slot="button"
        data-variant={variant}
        data-size={size}
        className={cn(
          'inline-flex items-center justify-center rounded-lg text-sm font-medium transition-colors outline-none focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50 active:translate-y-px [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=\'size-\'])]:size-4',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';

export type ButtonGroupProps = React.HTMLAttributes<HTMLDivElement>;

export const ButtonGroup = React.forwardRef<HTMLDivElement, ButtonGroupProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="button-group"
        className={cn('flex items-center', className)}
        {...props}
      />
    );
  }
);

ButtonGroup.displayName = 'ButtonGroup';