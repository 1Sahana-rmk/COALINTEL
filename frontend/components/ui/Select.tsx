import React from 'react';
import { cn } from '@/lib/utils/cn';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: readonly SelectOption[] | SelectOption[];
  error?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, options, error, id, disabled, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={selectId} className="block text-xs font-semibold uppercase tracking-wider text-[#E8ECEB]">
            {label}
          </label>
        )}

        <select
          id={selectId}
          ref={ref}
          disabled={disabled}
          className={cn(
            'w-full rounded-lg bg-[#151A1D] border border-[#30383D] px-3.5 py-2.5 text-sm text-[#E8ECEB] shadow-sm transition-colors duration-150',
            'focus:outline-none focus:border-[#C58B3A] focus:ring-1 focus:ring-[#C58B3A]',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-[#0E1113]',
            error && 'border-[#C94B45] focus:border-[#C94B45] focus:ring-[#C94B45]',
            className
          )}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#151A1D] text-[#E8ECEB] py-1">
              {opt.label}
            </option>
          ))}
        </select>

        {error && <p className="text-xs font-medium text-[#C94B45] mt-1">{error}</p>}
      </div>
    );
  }
);
Select.displayName = 'Select';
