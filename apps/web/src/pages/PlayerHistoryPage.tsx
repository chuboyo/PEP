import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import {
  PlayerRatingTrendCharts,
  PlayerSubmissionList,
} from "../components/PlayerHistoryCharts";
import { useMeQuery } from "../queries/auth";
import { usePlayerHistoryQuery } from "../queries/player";

export function PlayerHistoryPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isPlayer = me?.memberships.some(
    (m) => m.role === "PLAYER" && m.status === "active",
  );
  const historyQuery = usePlayerHistoryQuery(!!isPlayer);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isPlayer) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isPlayer, navigate]);

  if (!hasToken || mePending || !isPlayer) {
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
          <h1 className="brand">History</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/player">
              Pending
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {historyQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : historyQuery.isError ? (
          <p className="alert" role="alert">
            Could not load history
          </p>
        ) : historyQuery.data ? (
          <>
            <PlayerRatingTrendCharts
              trends={historyQuery.data.rating_trends}
            />

            <h2 className="section-title">Past submissions</h2>
            <PlayerSubmissionList
              submissions={historyQuery.data.submissions}
            />
          </>
        ) : null}
      </div>
    </main>
  );
}
