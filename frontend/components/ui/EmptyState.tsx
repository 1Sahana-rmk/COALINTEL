import React from 'react';
import { FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon = <FolderOpen className="h-10 w-10 text-[#9BA5A8]" />,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center rounded-lg bg-[#1C2226] border border-[#30383D] border-dashed shadow-sm',
        className
      )}
    >
      <div className="p-3 rounded-lg bg-[#242C30] mb-3 border border-[#30383D]">{icon}</div>
      <h4 className="text-base font-bold text-[#E8ECEB]">{title}</h4>
      <p className="text-xs text-[#9BA5A8] max-w-sm mt-1 mb-4 leading-relaxed">{description}</p>
      {action}
    </div>
  );
};
