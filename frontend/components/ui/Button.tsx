import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      type = 'button',
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0E1113] disabled:opacity-50 disabled:cursor-not-allowed select-none';

    const variants = {
      primary:
        'bg-[#C58B3A] hover:bg-[#D6A052] text-[#0E1113] font-semibold shadow-sm focus:ring-[#C58B3A] active:scale-[0.99]',
      secondary:
        'bg-[#242C30] hover:bg-[#30383D] text-[#E8ECEB] border border-[#30383D] focus:ring-[#C58B3A] active:scale-[0.99]',
      outline:
        'bg-transparent hover:bg-[#C58B3A]/10 text-[#C58B3A] hover:text-[#D6A052] border border-[#C58B3A]/60 focus:ring-[#C58B3A] active:scale-[0.99]',
      ghost:
        'bg-transparent hover:bg-[#242C30] text-[#9BA5A8] hover:text-[#E8ECEB] focus:ring-[#30383D] active:scale-[0.99]',
      danger:
        'bg-[#C94B45] hover:bg-[#C94B45]/90 text-[#E8ECEB] font-semibold shadow-sm focus:ring-[#C94B45] active:scale-[0.99]',
    };

    const sizes = {
      sm: 'text-xs px-3 py-1.5 gap-1.5',
      md: 'text-sm px-4 py-2 gap-2',
      lg: 'text-base px-6 py-2.5 gap-2.5',
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-current" />
        ) : (
          leftIcon
        )}
        <span>{children}</span>
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
