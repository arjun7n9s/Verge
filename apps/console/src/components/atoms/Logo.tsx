import clsx from 'clsx';

/* ── Verge logomark — "The lead" ─────────────────────────────────────
   A rising trace, the alert fired early (amber dot), the threshold line
   above, and the dashed projection between them. The gap between the dot
   and the line is the lead time — the product thesis as a mark.
   Structure inherits currentColor; the dot is always accent amber. */

interface LogoMarkProps {
  size?: number;
  className?: string;
}

export function LogoMark({ size = 20, className }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      role="img"
      aria-label="Verge"
      className={clsx('shrink-0', className)}
    >
      <line x1="4" y1="7" x2="28" y2="7" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
      <polyline
        points="4,26 11,22 16.5,17 21,12"
        stroke="currentColor"
        strokeWidth="2.6"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line
        x1="22.5" y1="10.6" x2="25.8" y2="8.4"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeDasharray="2 2.6"
        strokeLinecap="round"
        opacity="0.5"
      />
      <circle cx="21" cy="12" r="3.4" fill="var(--accent)" />
    </svg>
  );
}

interface LogoProps {
  size?: number;
  withTagline?: boolean;
  className?: string;
}

export function Logo({ size = 20, withTagline = false, className }: LogoProps) {
  return (
    <span className={clsx('inline-flex items-center gap-2 text-ink', className)}>
      <LogoMark size={size} />
      <span className="flex flex-col justify-center leading-none">
        <span className="font-mono font-semibold text-base tracking-[0.22em] text-ink">VERGE</span>
        {withTagline && (
          <span className="font-mono text-micro tracking-[0.14em] text-ink-dim mt-0.5">
            LEAD-TIME INTELLIGENCE
          </span>
        )}
      </span>
    </span>
  );
}
