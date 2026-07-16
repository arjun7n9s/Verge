import type { ReactNode } from 'react';
import clsx from 'clsx';

export function Kbd({ children, className }: { children: ReactNode; className?: string }) {
  return <kbd className={clsx('kbd', className)}>{children}</kbd>;
}
