import React from 'react';

export const Card = ({ children, className = '', header, title, subtitle, action, footer }) => {
  return (
    <div className={`bg-slate-800/80 backdrop-blur border border-slate-700/80 rounded-xl shadow-lg flex flex-col overflow-hidden ${className}`}>
      {(title || header || action) && (
        <div className="px-5 py-4 border-b border-slate-700/60 flex items-center justify-between">
          {header ? (
            header
          ) : (
            <div>
              {title && <h3 className="text-base font-semibold text-white tracking-tight">{title}</h3>}
              {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
            </div>
          )}
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="p-5 flex-1">{children}</div>
      {footer && <div className="px-5 py-3 bg-slate-900/40 border-t border-slate-700/60 text-xs text-slate-400">{footer}</div>}
    </div>
  );
};
