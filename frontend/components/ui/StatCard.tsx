import React from 'react';
import { Card } from './Card';
import { cn } from '@/lib/utils/cn';

interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon: React.ReactNode;
  subtitle?: string;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  variant?: 'default' | 'primary' | 'danger' | 'success';
  className?: string;
  loading?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  unit,
  icon,
  subtitle,
  trend,
  variant = 'default',
  className,
  loading = false,
}) => {
  const variantStyles = {
    default: 'border-[#30383D] hover:border-[#C58B3A]/40',
    primary: 'border-[#C58B3A]/40 bg-[#1C2226] hover:border-[#C58B3A]/70 shadow-sm',
    danger: 'border-[#C94B45]/40 bg-[#1C2226] hover:border-[#C94B45]/70 shadow-sm',
    success: 'border-[#4F8A62]/40 bg-[#1C2226] hover:border-[#4F8A62]/70 shadow-sm',
  };

  const iconBgStyles = {
    default: 'bg-[#151A1D] border-[#30383D] text-[#C58B3A]',
    primary: 'bg-[#C58B3A]/15 border-[#C58B3A]/30 text-[#C58B3A]',
    danger: 'bg-[#C94B45]/15 border-[#C94B45]/30 text-[#C94B45]',
    success: 'bg-[#4F8A62]/15 border-[#4F8A62]/30 text-[#4F8A62]',
  };

  return (
    <Card
      className={cn(
        'relative overflow-hidden group transition-all duration-200 ease-out bg-[#1C2226] border p-4 hover:-translate-y-0.5',
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0 flex-1">
          <p className="text-[11px] font-semibold text-[#9BA5A8] uppercase tracking-wider truncate font-sans">
            {title}
          </p>
          {loading ? (
            <div className="h-8 w-24 animate-pulse rounded bg-[#242C30] my-1" />
          ) : (
            <div className="flex items-baseline space-x-1.5 flex-wrap">
              <span className="text-2xl font-bold text-[#E8ECEB] tracking-tight font-sans">
                {value}
              </span>
              {unit && <span className="text-[11px] font-bold text-[#C58B3A] uppercase font-mono">{unit}</span>}
            </div>
          )}
        </div>

        <div className={cn('p-2 rounded-lg border shrink-0 transition-transform duration-200 group-hover:scale-105', iconBgStyles[variant])}>
          {icon}
        </div>
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 pt-2.5 border-t border-[#30383D] flex items-center justify-between text-xs gap-2">
          {subtitle && <span className="text-[11px] text-[#9BA5A8] truncate leading-tight">{subtitle}</span>}
          {trend && (
            <span
              className={cn(
                'font-semibold px-1.5 py-0.5 rounded font-mono text-[10px] shrink-0',
                trend.isPositive
                  ? 'text-[#4F8A62] bg-[#4F8A62]/15 border border-[#4F8A62]/30'
                  : 'text-[#C94B45] bg-[#C94B45]/15 border border-[#C94B45]/30'
              )}
            >
              {trend.value}
            </span>
          )}
        </div>
      )}
    </Card>
  );
};
