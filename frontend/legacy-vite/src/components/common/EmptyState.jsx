import React from 'react';
import { Database } from 'lucide-react';

export const EmptyState = ({ icon: Icon = Database, title = 'No Data Found', description = 'There are no items to display right now.', action }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-800/40 border border-dashed border-slate-700 rounded-xl my-4">
      <div className="p-3 bg-slate-800 rounded-full text-slate-400 mb-3 border border-slate-700">
        <Icon className="w-8 h-8" />
      </div>
      <h4 className="text-base font-semibold text-white">{title}</h4>
      <p className="text-xs text-slate-400 max-w-sm mt-1 mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
