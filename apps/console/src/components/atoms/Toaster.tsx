import { useToastStore } from '@/stores/toasts';
import { CircleCheck, CircleAlert, Info, X } from 'lucide-react';
import clsx from 'clsx';

const KIND_STYLE = {
  ok: { icon: CircleCheck, color: 'text-ok', border: 'border-ok/25' },
  error: { icon: CircleAlert, color: 'text-imminent', border: 'border-imminent/25' },
  info: { icon: Info, color: 'text-watch', border: 'border-watch/25' },
} as const;

export function Toaster() {
  const { toasts, dismiss } = useToastStore();
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 w-72 select-none"
      role="status"
      aria-live="polite"
    >
      {toasts.map((t) => {
        const meta = KIND_STYLE[t.kind];
        const Icon = meta.icon;
        return (
          <div
            key={t.id}
            className={clsx(
              'flex items-start gap-2 bg-panel border rounded-md px-3 py-2 shadow-lg shadow-bg/60',
              'animate-[toast-in_150ms_ease-out]',
              meta.border,
            )}
          >
            <Icon className={clsx('h-3.5 w-3.5 shrink-0 mt-0.5', meta.color)} />
            <span className="text-xs text-ink leading-normal flex-1">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="text-ink-dim hover:text-ink cursor-pointer shrink-0"
              aria-label="Dismiss"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
