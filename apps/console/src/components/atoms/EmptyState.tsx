import type { ReactNode } from 'react';
import clsx from 'clsx';

/* Designed empty state: icon, one calm sentence, optional action.
   Never a bare "no data". */

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, hint, action, className }: EmptyStateProps) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center gap-2 py-8 px-4 text-center select-none',
        'border border-dashed border-line rounded-md',
        className,
      )}
    >
      {icon && <span className="text-ink-dim/50 [&>svg]:h-6 [&>svg]:w-6">{icon}</span>}
      <span className="text-xs font-medium text-ink-dim">{title}</span>
      {hint && <span className="text-micro font-mono text-ink-dim/60 max-w-[36ch] leading-normal">{hint}</span>}
      {action}
    </div>
  );
}
