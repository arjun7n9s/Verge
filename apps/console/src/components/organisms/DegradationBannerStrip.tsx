import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import { getDegradationStatus, type DegradationBanner } from '@/api/platform';

const SEVERITY_STYLE: Record<DegradationBanner['severity'], string> = {
  info: 'bg-accent/10 border-accent/20 text-accent',
  warn: 'bg-near/10 border-near/20 text-near',
  critical: 'bg-imminent/10 border-imminent/20 text-imminent',
};

export function DegradationBannerStrip() {
  const [banners, setBanners] = useState<DegradationBanner[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      getDegradationStatus()
        .then((body) => {
          if (!cancelled) setBanners(body.banners);
        })
        .catch(() => {
          if (!cancelled) setBanners([]);
        });
    };
    load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  if (banners.length === 0) return null;

  return (
    <div className="border-b border-line shrink-0">
      {banners.map((b) => (
        <div
          key={b.code}
          className={clsx(
            'text-xs font-mono py-1.5 px-4 flex items-center gap-2 border-b border-line/50 last:border-b-0 select-text',
            SEVERITY_STYLE[b.severity],
          )}
        >
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>{b.message}</span>
        </div>
      ))}
    </div>
  );
}
