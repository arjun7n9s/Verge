import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-accent text-bg hover:bg-accent/90 border-accent/30 active:bg-accent/80',
  secondary:
    'bg-panel-2 text-ink hover:bg-line/50 border-line active:bg-line/70',
  ghost:
    'bg-transparent text-ink-dim hover:text-ink hover:bg-panel-2 border-transparent active:bg-line/30',
  danger:
    'bg-imminent/10 text-imminent hover:bg-imminent/20 border-imminent/30 active:bg-imminent/30',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-7 px-2.5 text-xs gap-1.5 rounded',
  md: 'h-8 px-3 text-sm gap-2 rounded',
  lg: 'h-9 px-4 text-base gap-2 rounded-md',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'secondary',
      size = 'md',
      loading = false,
      icon,
      children,
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={clsx(
          'inline-flex items-center justify-center',
          'border font-medium',
          'transition-[color,background-color,border-color,transform] duration-fast',
          'active:scale-[0.98]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          'cursor-pointer select-none',
          variantStyles[variant],
          sizeStyles[size],
          isDisabled && 'opacity-50 cursor-not-allowed pointer-events-none',
          className
        )}
        disabled={isDisabled}
        {...props}
      >
        {loading ? (
          <Loader2
            className="h-4 w-4 animate-spin"
            aria-hidden="true"
          />
        ) : icon ? (
          <span className="shrink-0" aria-hidden="true">
            {icon}
          </span>
        ) : null}
        {children && <span>{children}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
