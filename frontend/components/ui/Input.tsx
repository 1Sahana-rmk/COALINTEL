import React from 'react';
import { cn } from '@/lib/utils/cn';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, leftIcon, rightIcon, id, disabled, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-semibold uppercase tracking-wider text-[#E8ECEB]">
            {label}
          </label>
        )}

        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 text-[#9BA5A8] pointer-events-none flex items-center">
              {leftIcon}
            </div>
          )}

          <input
            id={inputId}
            ref={ref}
            disabled={disabled}
            className={cn(
              'w-full rounded-lg bg-[#151A1D] border border-[#30383D] px-3.5 py-2.5 text-sm text-[#E8ECEB] placeholder:text-[#9BA5A8]/70 shadow-sm transition-colors duration-150',
              'focus:outline-none focus:border-[#C58B3A] focus:ring-1 focus:ring-[#C58B3A]',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-[#0E1113]',
              leftIcon && 'pl-10',
              rightIcon && 'pr-10',
              error && 'border-[#C94B45] focus:border-[#C94B45] focus:ring-[#C94B45]',
              className
            )}
            {...props}
          />

          {rightIcon && (
            <div className="absolute right-3 text-[#9BA5A8] flex items-center">
              {rightIcon}
            </div>
          )}
        </div>

        {error ? (
          <p className="text-xs font-medium text-[#C94B45] mt-1 flex items-center gap-1">{error}</p>
        ) : helperText ? (
          <p className="text-xs text-[#9BA5A8] mt-1">{helperText}</p>
        ) : null}
      </div>
    );
  }
);
Input.displayName = 'Input';
