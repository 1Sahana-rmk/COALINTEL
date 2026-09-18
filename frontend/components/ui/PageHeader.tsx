import React from 'react';
import { Breadcrumbs, BreadcrumbItem } from './Breadcrumbs';
import { cn } from '@/lib/utils/cn';

interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  breadcrumbs,
  badge,
  actions,
  className,
}) => {
  return (
    <div className={cn('flex flex-col gap-3 pb-6 border-b border-[#30383D] mb-6', className)}>
      {breadcrumbs && <Breadcrumbs items={breadcrumbs} />}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-[#E8ECEB] font-sans">
              {title}
            </h1>
            {badge}
          </div>
          {description && <p className="text-xs lg:text-sm text-[#9BA5A8] max-w-4xl 2xl:max-w-5xl font-normal leading-relaxed">{description}</p>}
        </div>

        {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
      </div>
    </div>
  );
};
