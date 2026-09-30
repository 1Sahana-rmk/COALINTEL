import React from 'react';
import { cn } from '@/lib/utils/cn';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'bordered' | 'dark';
  glow?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, children, variant = 'default', glow = false, ...props }, ref) => {
    const variants = {
      default: 'bg-[#1C2226] border border-[#30383D] shadow-sm text-[#E8ECEB]',
      elevated: 'bg-[#242C30] border border-[#30383D] shadow-sm text-[#E8ECEB]',
      bordered: 'bg-[#1C2226] border border-[#30383D] text-[#E8ECEB]',
      dark: 'bg-[#151A1D] border border-[#30383D] text-[#E8ECEB]',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg p-5 transition-colors duration-150',
          variants[variant],
          glow && 'border-[#C58B3A]/40',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = 'Card';

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('flex flex-col space-y-1.5 pb-4 border-b border-[#30383D]', className)} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className,
  children,
  ...props
}) => (
  <h3 className={cn('text-base font-bold text-[#E8ECEB] tracking-tight flex items-center gap-2', className)} {...props}>
    {children}
  </h3>
);

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  className,
  children,
  ...props
}) => (
  <p className={cn('text-xs text-[#9BA5A8] font-normal leading-relaxed', className)} {...props}>
    {children}
  </p>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('pt-4', className)} {...props}>
    {children}
  </div>
);
