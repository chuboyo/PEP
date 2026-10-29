import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useTeamQuery } from "../queries/teams";

export function TeamDetailPage() {
  const { teamId = "" } = useParams();
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const teamQuery = useTeamQuery(teamId, !!isCoach && !!teamId);

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
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">{teamQuery.data?.name ?? "Team"}</h1>
          <div className="nav-links">
            <Link
              className="btn btn--primary"
              to={`/teams/${teamId}/players/new`}
            >
              Register player
            </Link>
            <Link
              className="btn btn--ghost"
              to={`/dashboard?team_id=${teamId}`}
            >
              Dashboard
            </Link>
            <Link className="btn btn--ghost" to="/teams">
              All teams
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <h2 className="section-title">Roster</h2>
        {teamQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : teamQuery.isError ? (
          <p className="alert" role="alert">
            Could not load team
          </p>
        ) : (teamQuery.data?.members.length ?? 0) === 0 ? (
          <p className="muted">No players yet.</p>
        ) : (
          <ul className="meta-list">
            {teamQuery.data?.members.map((member) => (
              <li key={member.user_id}>
                <span className="label">{member.role ?? "member"}</span>
                {member.role === "PLAYER" ? (
                  <Link
                    className="value"
                    to={`/players/${member.user_id}`}
                  >
                    {member.name}
                  </Link>
                ) : (
                  <span className="value">{member.name}</span>
                )}
                <span className="muted">{member.email}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
