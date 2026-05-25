import React, { useState } from 'react';
import { cn } from '../utils/cn';

export interface SwitchProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'size'> {
  size?: 'default' | 'sm';
  onCheckedChange?: (checked: boolean) => void;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  (
    {
      className,
      size = 'default',
      checked: controlledChecked,
      defaultChecked,
      onCheckedChange,
      onChange,
      ...props
    },
    ref
  ) => {
    const [localChecked, setLocalChecked] = useState(defaultChecked ?? false);
    const isControlled = controlledChecked !== undefined;
    const checked = isControlled ? controlledChecked : localChecked;

    const handleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
      const nextChecked = e.target.checked;
      if (!isControlled) {
        setLocalChecked(nextChecked);
      }
      onCheckedChange?.(nextChecked);
      onChange?.(e);
    };

    return (
      <label
        data-slot="switch"
        data-size={size}
        data-checked={checked ? 'true' : undefined}
        data-unchecked={!checked ? 'true' : undefined}
        className={cn(
          'peer relative inline-flex shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-all outline-none',
          size === 'default' ? 'h-[18.4px] w-[32px]' : 'h-[14px] w-[24px]',
          checked ? 'bg-primary' : 'bg-input dark:bg-input/80',
          'focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50',
          'aria-disabled:cursor-not-allowed aria-disabled:opacity-50',
          className
        )}
      >
        <input
          ref={ref}
          type="checkbox"
          checked={checked}
          onChange={handleToggle}
          className="sr-only"
          {...props}
        />
        <span
          data-slot="switch-thumb"
          className={cn(
            'pointer-events-none block rounded-full bg-background ring-0 transition-transform',
            size === 'default' ? 'size-4' : 'size-3',
            checked ? 'translate-x-[calc(100%-2px)]' : 'translate-x-0'
          )}
        />
      </label>
    );
  }
);

Switch.displayName = 'Switch';

// Expose both names since options panels or other imports might use CSwitch or Switch.
export const CSwitch = Switch;
export type CSwitchProps = SwitchProps;