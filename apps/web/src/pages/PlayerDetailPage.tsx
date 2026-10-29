import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getAccessToken } from "../auth";
import {
  OccurrenceAnswersChart,
  RatingTrendCharts,
  StatusOverviewChart,
} from "../components/PlayerDetailCharts";
import { useMeQuery } from "../queries/auth";
import { usePlayerDetailQuery } from "../queries/dashboard";

export function PlayerDetailPage() {
  const { playerId = "" } = useParams();
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const detailQuery = usePlayerDetailQuery(playerId, !!isCoach && !!playerId);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isCoach) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isCoach, navigate]);

  if (!hasToken || mePending || !isCoach) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide panel--dashboard">
        <header className="topbar">
          <h1 className="brand">{detailQuery.data?.name ?? "Player"}</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/dashboard">
              Dashboard
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {detailQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : detailQuery.isError ? (
          <p className="alert" role="alert">
            Could not load player
          </p>
        ) : detailQuery.data ? (
          <>
            <p className="lede lede--tight">{detailQuery.data.email}</p>

            {detailQuery.data.occurrences.length === 0 ? (
              <p className="muted">No occurrences yet.</p>
            ) : (
              <>
                <div className="chart-grid">
                  <StatusOverviewChart
                    occurrences={detailQuery.data.occurrences}
                  />
                </div>

                <RatingTrendCharts
                  occurrences={detailQuery.data.occurrences}
                />

                <h2 className="section-title">Occurrence history</h2>
                <div className="occurrence-stack">
                  {detailQuery.data.occurrences.map((occurrence) => (
                    <article
                      className="occurrence-card"
                      key={occurrence.occurrence_id}
                    >
                      <header className="occurrence-card__header">
                        <h3 className="chart-card__title">
                          {occurrence.questionnaire_name}
                        </h3>
                        <span className="occurrence-card__status">
                          {occurrence.status}
                        </span>
                      </header>
                      <p className="chart-card__caption">
                        {occurrence.submitted_at
                          ? `Submitted ${new Date(occurrence.submitted_at).toLocaleString()}`
                          : occurrence.due_at
                            ? `Due ${new Date(occurrence.due_at).toLocaleString()}`
                            : "No due date"}
                        {occurrence.channel
                          ? ` · ${occurrence.channel}`
                          : null}
                      </p>
                      <OccurrenceAnswersChart occurrence={occurrence} />
                    </article>
                  ))}
                </div>
              </>
            )}
          </>
        ) : null}
      </div>
    </main>
  );
}
