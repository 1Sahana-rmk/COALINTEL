import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { cn } from '@/lib/utils/cn';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'System Alert',
  message,
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        'p-4 rounded-lg bg-danger/10 border border-danger/30 text-danger flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-danger shrink-0 mt-0.5" />
        <div>
          <h5 className="text-sm font-bold text-danger">{title}</h5>
          <p className="text-xs text-danger/90 mt-0.5">{message}</p>
        </div>
      </div>

      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} leftIcon={<RefreshCw className="h-3.5 w-3.5" />}>
          Retry
        </Button>
      )}
    </div>
  );
};
