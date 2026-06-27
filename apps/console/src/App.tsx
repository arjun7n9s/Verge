import { useCallback, useEffect, useState } from "react";
import type { RiskFinding } from "@verge/schema";
import { api } from "./api";
import { FindingsBoard } from "./components/FindingsBoard";
import { SensorRibbon } from "./components/SensorRibbon";

export default function App() {
  const [findings, setFindings] = useState<RiskFinding[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api
      .findings()
      .then((f) => {
        setFindings(f);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    refresh();
    const h = setInterval(refresh, 3000);
    return () => clearInterval(h);
  }, [refresh]);

  return (
    <div className="app">
      <header className="topbar">
        <span className="wordmark">Verge</span>
        <span className="tagline">lead-time intelligence · operator console</span>
      </header>
      <SensorRibbon />
      {error && <div className="error">API unreachable ({error}). Is the gateway up on :8000?</div>}
      <FindingsBoard findings={findings} onChange={refresh} />
    </div>
  );
}
