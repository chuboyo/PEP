import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useTeamsQuery } from "../queries/teams";

export function TeamsPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const isClubAdmin = me?.memberships.some(
    (m) => m.role === "CLUB_ADMIN" && m.status === "active",
  );
  const canList = !!isCoach || !!isClubAdmin;
  const teamsQuery = useTeamsQuery(canList);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !canList) {
      navigate("/");
    }
  }, [hasToken, me, mePending, canList, navigate]);

  if (!hasToken || mePending || !canList) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Teams</h1>
          <div className="nav-links">
            {isCoach ? (
              <Link className="btn btn--primary" to="/teams/new">
                Create team
              </Link>
            ) : null}
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {teamsQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : teamsQuery.isError ? (
          <p className="alert" role="alert">
            Could not load teams
          </p>
        ) : (teamsQuery.data?.length ?? 0) === 0 ? (
          <p className="muted">No teams yet.</p>
        ) : (
          <ul className="meta-list">
            {teamsQuery.data?.map((team) => (
              <li key={team.id}>
                <span className="value">
                  {isCoach ? (
                    <Link to={`/teams/${team.id}`}>{team.name}</Link>
                  ) : (
                    team.name
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
