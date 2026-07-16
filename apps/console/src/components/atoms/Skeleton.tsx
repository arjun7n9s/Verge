import clsx from 'clsx';

/* Loading placeholder — shaped like the content it stands in for.
   One pulse animation, no shimmer gradients. */

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={clsx('animate-pulse rounded bg-panel-2', className)}
    />
  );
}

export function FindingCardSkeleton() {
  return (
    <div className="surface-1 p-4 flex flex-col gap-3" aria-hidden="true">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-12" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-3 w-3/5" />
      <div className="flex gap-1.5">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-24" />
      </div>
    </div>
  );
}
