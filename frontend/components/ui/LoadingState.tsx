import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

interface LoadingStateProps {
  label?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  label = 'Loading operational data...',
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center space-y-4 rounded-lg bg-[#1C2226]/50 border border-[#30383D]/60 animate-fade-in',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="relative flex items-center justify-center">
        <div className="absolute h-10 w-10 rounded-full border border-[#C58B3A]/20 animate-ping" />
        <Loader2 className="h-6 w-6 animate-spin text-[#C58B3A]" />
      </div>
      <p className="text-xs font-mono text-[#9BA5A8] uppercase tracking-widest">{label}</p>
    </div>
  );
};
