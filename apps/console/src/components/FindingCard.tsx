import type { LeadTimeBand, RiskFinding } from "@verge/schema";
import { api } from "../api";

const BAND_CLASS: Record<LeadTimeBand, string> = {
  IMMINENT: "band-imminent",
  NEAR: "band-near",
  WATCH: "band-watch",
  UNKNOWN: "band-unknown",
};

export function FindingCard({ f, onChange }: { f: RiskFinding; onChange: () => void }) {
  const ack = () => api.transition(f.findingId, "acknowledged", "maya").then(onChange);
  const mark = (verdict: string) => api.feedback(f.findingId, verdict).then(onChange);

  return (
    <article className="card">
      <header className="card-head">
        <span className={`band ${BAND_CLASS[f.leadTimeBand]}`}>{f.leadTimeBand}</span>
        <span className="zone">{f.zoneId}</span>
        <span className="conf">conf {f.confidence.toFixed(2)}</span>
      </header>
      <h3 className="card-title">{f.title}</h3>

      {f.confidenceDegraded && (
        <p className="degraded">
          estimate degraded — {f.confidenceDegradedBy.join(", ")} suspect
        </p>
      )}
      {f.counterfactual && <p className="counterfactual">↳ {f.counterfactual}</p>}

      <div className="chips">
        {f.lineage.map((l) => (
          <span className="chip" key={l}>
            {l}
          </span>
        ))}
      </div>

      <footer className="card-actions">
        {f.state === "new" && (
          <button onClick={ack} className="btn">
            Acknowledge
          </button>
        )}
        <button onClick={() => mark("useful")} className="btn btn-quiet">
          useful
        </button>
        <button onClick={() => mark("false-alarm")} className="btn btn-quiet">
          false-alarm
        </button>
      </footer>
    </article>
  );
}
