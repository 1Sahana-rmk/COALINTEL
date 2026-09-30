'use client';

import React from 'react';
import { Breadcrumbs, BreadcrumbItem } from './Breadcrumbs';
import { cn } from '@/lib/utils/cn';
import { useLanguage } from '@/context/LanguageContext';

interface PageHeaderProps {
  title: string;
  titleKey?: string;
  description?: string;
  descriptionKey?: string;
  breadcrumbs?: BreadcrumbItem[];
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  titleKey,
  description,
  descriptionKey,
  breadcrumbs,
  badge,
  actions,
  className,
}) => {
  const { t } = useLanguage();
  const displayTitle = titleKey ? t(titleKey, title) : title;
  const displayDescription = descriptionKey ? t(descriptionKey, description) : description;
  return (
    <div className={cn('flex flex-col gap-3 pb-6 border-b border-[#30383D] mb-6', className)}>
      {breadcrumbs && <Breadcrumbs items={breadcrumbs} />}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-[#E8ECEB] font-sans">
              {displayTitle}
            </h1>
            {badge}
          </div>
          {displayDescription && <p className="text-xs lg:text-sm text-[#9BA5A8] max-w-4xl 2xl:max-w-5xl font-normal leading-relaxed">{displayDescription}</p>}
        </div>

        {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
      </div>
    </div>
  );
};
