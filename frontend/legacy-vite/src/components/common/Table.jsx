import React from 'react';

export const Table = ({ headers = [], children, className = '' }) => {
  return (
    <div className={`w-full overflow-x-auto border border-slate-700/80 rounded-xl bg-slate-800/60 ${className}`}>
      <table className="w-full text-left text-sm text-slate-300 border-collapse">
        <thead className="bg-slate-900/80 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-700">
          <tr>
            {headers.map((header, idx) => (
              <th key={idx} className="px-4 py-3.5 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/50">{children}</tbody>
      </table>
    </div>
  );
};
