import React from 'react';
import { cn } from '../utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'default' | 'sm';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, size = 'default', ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="card"
        data-size={size}
        className={cn(
          'flex flex-col gap-4 overflow-hidden rounded-xl bg-card border border-border py-4 text-sm text-card-foreground data-[size=sm]:gap-3 data-[size=sm]:py-3',
          className
        )}
        {...props}
      />
    );
  }
);

Card.displayName = 'Card';

export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="card-header"
        className={cn('grid auto-rows-min items-start gap-1 px-4', className)}
        {...props}
      />
    );
  }
);

CardHeader.displayName = 'CardHeader';

export type CardTitleProps = React.HTMLAttributes<HTMLHeadingElement>;

export const CardTitle = React.forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ className, ...props }, ref) => {
    return (
      <h3
        ref={ref}
        data-slot="card-title"
        className={cn('text-base leading-snug font-medium', className)}
        {...props}
      />
    );
  }
);

CardTitle.displayName = 'CardTitle';

export type CardDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

export const CardDescription = React.forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ className, ...props }, ref) => {
    return (
      <p
        ref={ref}
        data-slot="card-description"
        className={cn('text-sm text-muted-foreground', className)}
        {...props}
      />
    );
  }
);

CardDescription.displayName = 'CardDescription';

export type CardActionProps = React.HTMLAttributes<HTMLDivElement>;

export const CardAction = React.forwardRef<HTMLDivElement, CardActionProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="card-action"
        className={cn('col-start-2 row-span-2 row-start-1 self-start justify-self-end', className)}
        {...props}
      />
    );
  }
);

CardAction.displayName = 'CardAction';

export type CardContentProps = React.HTMLAttributes<HTMLDivElement>;

export const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="card-content"
        className={cn('px-4', className)}
        {...props}
      />
    );
  }
);

CardContent.displayName = 'CardContent';

export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>;

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        data-slot="card-footer"
        className={cn('flex items-center rounded-b-xl border-t bg-muted/50 p-4', className)}
        {...props}
      />
    );
  }
);

CardFooter.displayName = 'CardFooter';