import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  interactive?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ children, interactive = false, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'surface-1 p-4 hover-elevate',
          'transition-colors duration-fast',
          interactive && 'hover:bg-panel-2 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          className
        )}
        tabIndex={interactive ? 0 : undefined}
        role={interactive ? 'button' : undefined}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
