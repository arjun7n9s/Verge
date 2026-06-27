import { useEffect, useState } from "react";
import { api, type Health, type Ribbon } from "../api";

// The always-visible health ribbon (spec §4.7) + degradation banner (§10.6).
export function SensorRibbon() {
  const [ribbon, setRibbon] = useState<Ribbon | null>(null);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    const tick = () => {
      api.ribbon().then(setRibbon).catch(() => {});
      api.health().then(setHealth).catch(() => {});
    };
    tick();
    const h = setInterval(tick, 5000);
    return () => clearInterval(h);
  }, []);

  return (
    <div className="ribbon">
      <span className="ribbon-health">{ribbon?.text ?? "connecting…"}</span>
      <span className="ribbon-spacer" />
      {health && health.llm.degraded && (
        <span className="badge badge-degraded">AI narrative: degraded</span>
      )}
      {health && (
        <span className={`badge ${health.audit.verified ? "badge-ok" : "badge-degraded"}`}>
          audit {health.audit.verified ? "verified" : "FAILED"} · {health.audit.entries}
        </span>
      )}
    </div>
  );
}
