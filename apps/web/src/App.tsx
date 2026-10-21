import { useEffect, useState } from "react";

import type { paths } from "./api/schema";

type HealthResponse =
  paths["/api/v1/health"]["get"]["responses"]["200"]["content"]["application/json"];

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function App() {
  const [status, setStatus] = useState<string>("loading…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const response = await fetch(`${apiUrl}/api/v1/health`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const body = (await response.json()) as HealthResponse;
        if (!cancelled) {
          setStatus(body.status);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setStatus("unavailable");
        }
      }
    }

    void loadHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>Pep</h1>
      <p>
        API health: <strong>{status}</strong>
      </p>
      {error ? <p role="alert">Could not reach API: {error}</p> : null}
    </main>
  );
}
