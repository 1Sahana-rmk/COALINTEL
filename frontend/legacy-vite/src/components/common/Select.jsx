import React, { forwardRef } from 'react';

export const Select = forwardRef(({ label, options = [], error, helperText, className = '', ...props }, ref) => {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          {label}
        </label>
      )}
      <select
        ref={ref}
        className={`w-full bg-slate-900/90 border ${
          error ? 'border-rose-500' : 'border-slate-700 focus:border-amber-500'
        } rounded-lg text-slate-100 text-sm px-3.5 py-2 transition-colors focus:outline-none focus:ring-1 focus:ring-amber-500 ${className}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-100">
            {opt.label}
          </option>
        ))}
      </select>
      {error ? (
        <span className="text-xs text-rose-400 font-medium">{error}</span>
      ) : helperText ? (
        <span className="text-xs text-slate-500">{helperText}</span>
      ) : null}
    </div>
  );
});
