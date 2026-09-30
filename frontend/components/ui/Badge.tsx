import React from 'react';
import { cn } from '@/lib/utils/cn';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'gold' | 'amber' | 'teal' | 'secondary';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  children,
  variant = 'default',
  size = 'md',
  ...props
}) => {
  const variants = {
    default: 'bg-[#242C30] text-[#E8ECEB] border-[#30383D]',
    secondary: 'bg-[#242C30] text-[#9BA5A8] border-[#30383D]',
    success: 'bg-[#4F8A62]/15 text-[#4F8A62] border-[#4F8A62]/30 font-semibold',
    warning: 'bg-[#D6A23A]/15 text-[#D6A23A] border-[#D6A23A]/30 font-semibold',
    danger: 'bg-[#C94B45]/15 text-[#C94B45] border-[#C94B45]/30 font-semibold',
    info: 'bg-[#54788A]/15 text-[#54788A] border-[#54788A]/30 font-semibold',
    gold: 'bg-[#C58B3A]/15 text-[#C58B3A] border-[#C58B3A]/30 font-semibold',
    amber: 'bg-[#C58B3A]/15 text-[#C58B3A] border-[#C58B3A]/30 font-semibold',
    teal: 'bg-[#54788A]/15 text-[#54788A] border-[#54788A]/30 font-semibold',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded border tracking-wide uppercase font-mono select-none',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
