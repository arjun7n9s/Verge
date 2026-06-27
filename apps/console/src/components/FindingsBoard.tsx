import type { FindingState, RiskFinding } from "@verge/schema";
import { FindingCard } from "./FindingCard";

// The operator's working surface is a board by lifecycle state (spec §4.5),
// not a notification feed. Columns mirror the state machine.
const COLUMNS: { state: FindingState; label: string }[] = [
  { state: "new", label: "New" },
  { state: "acknowledged", label: "Acknowledged" },
  { state: "in-progress", label: "In progress" },
  { state: "snoozed", label: "Snoozed" },
  { state: "escalated", label: "Escalated" },
  { state: "resolved", label: "Resolved" },
];

export function FindingsBoard({
  findings,
  onChange,
}: {
  findings: RiskFinding[];
  onChange: () => void;
}) {
  return (
    <div className="board">
      {COLUMNS.map(({ state, label }) => {
        const items = findings.filter((f) => f.state === state);
        return (
          <section className="column" key={state}>
            <h2 className="column-head">
              {label} <span className="count">{items.length}</span>
            </h2>
            {items.map((f) => (
              <FindingCard key={f.findingId} f={f} onChange={onChange} />
            ))}
          </section>
        );
      })}
    </div>
  );
}
