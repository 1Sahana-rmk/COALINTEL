import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export const ErrorState = ({ title = 'Failed to Load Data', message = 'An unexpected error occurred while communicating with backend APIs.', onRetry }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-rose-950/20 border border-rose-500/30 rounded-xl my-4">
      <div className="p-3 bg-rose-950/60 rounded-full text-rose-400 mb-3 border border-rose-500/40">
        <AlertCircle className="w-8 h-8" />
      </div>
      <h4 className="text-base font-semibold text-rose-200">{title}</h4>
      <p className="text-xs text-rose-300 max-w-md mt-1 mb-4">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={onRetry}>
          Retry Request
        </Button>
      )}
    </div>
  );
};
