import React from 'react';

export const Badge = ({ children, status, variant = 'default', size = 'sm', className = '' }) => {
  // Map validation status or document status to curated theme badges
  let style = 'bg-slate-800 text-slate-300 border-slate-700';

  const normalized = status ? String(status).toUpperCase() : String(variant).toUpperCase();

  if (['VALIDATED', 'APPROVED', 'PARSED', 'INDEXED', 'SUCCESS'].includes(normalized)) {
    style = 'bg-emerald-950/80 text-emerald-300 border-emerald-500/30';
  } else if (['WARNING_ARITHMETIC', 'PENDING', 'PROCESSING', 'DRAFT', 'WARNING'].includes(normalized)) {
    style = 'bg-amber-950/80 text-amber-300 border-amber-500/30';
  } else if (['CONFLICT_DETECTED', 'FAILED', 'REJECTED', 'ERROR'].includes(normalized)) {
    style = 'bg-rose-950/80 text-rose-300 border-rose-500/30';
  } else if (['UNVERIFIED', 'INFO'].includes(normalized)) {
    style = 'bg-blue-950/80 text-blue-300 border-blue-500/30';
  }

  const sizes = {
    xs: 'text-[10px] px-1.5 py-0.5 font-semibold',
    sm: 'text-xs px-2.5 py-0.5 font-medium',
    md: 'text-sm px-3 py-1 font-medium'
  };

  return (
    <span className={`inline-flex items-center tracking-wide rounded-full border ${style} ${sizes[size]} ${className}`}>
      {children || status}
    </span>
  );
};
