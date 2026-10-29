import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import type { AttentionFlag } from "../api/dashboard";
import { getAccessToken } from "../auth";
import {
  CompletionChart,
  QuestionStatChart,
} from "../components/DashboardCharts";
import { useMeQuery } from "../queries/auth";
import { useTeamDashboardQuery } from "../queries/dashboard";
import { useTeamsQuery } from "../queries/teams";

function flagLabel(flag: AttentionFlag): string {
  if (flag.type === "high_rating_streak") {
    return `High ratings on ${flag.question_id ?? "question"}`;
  }
  return "No response on last two due occurrences";
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const teamsQuery = useTeamsQuery(!!isCoach);

  const teamIdFromUrl = searchParams.get("team_id") ?? "";
  const [teamId, setTeamId] = useState(teamIdFromUrl);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isCoach) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isCoach, navigate]);

  useEffect(() => {
    if (teamIdFromUrl) {
      setTeamId(teamIdFromUrl);
      return;
    }
    if (!teamId && (teamsQuery.data?.length ?? 0) > 0) {
      const first = teamsQuery.data![0].id;
      setTeamId(first);
      setSearchParams({ team_id: first }, { replace: true });
    }
  }, [teamId, teamIdFromUrl, teamsQuery.data, setSearchParams]);

  const dashboardQuery = useTeamDashboardQuery(teamId, !!isCoach && !!teamId);

  function onTeamChange(nextTeamId: string) {
    setTeamId(nextTeamId);
    setSearchParams(nextTeamId ? { team_id: nextTeamId } : {}, { replace: true });
  }

  if (!hasToken || mePending || !isCoach) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const dashboard = dashboardQuery.data;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide panel--dashboard">
        <header className="topbar">
          <h1 className="brand">Dashboard</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/teams">
              Teams
            </Link>
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
          <p className="muted">
            No teams yet.{" "}
            <Link to="/teams/new">Create a team</Link> to open the dashboard.
          </p>
        ) : (
          <>
            <label className="field">
              <span className="label">Team</span>
              <select
                value={teamId}
                onChange={(event) => onTeamChange(event.target.value)}
              >
                {(teamsQuery.data ?? []).map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
            </label>

            {!teamId || dashboardQuery.isPending ? (
              <p className="muted">Loading…</p>
            ) : dashboardQuery.isError ? (
              <p className="alert" role="alert">
                Could not load dashboard
              </p>
            ) : !dashboard ? null : (
              <>
                <h2 className="section-title">Summary</h2>
                <p className="lede lede--tight">
                  {dashboard.questionnaire_name ?? "No assignment yet"}
                </p>
                <div className="chart-grid">
                  <CompletionChart
                    completed={dashboard.completion_count}
                    rosterSize={dashboard.roster_size}
                  />
                </div>

                {dashboard.question_stats.length > 0 ? (
                  <>
                    <h2 className="section-title">Question stats</h2>
                    <div className="chart-grid">
                      {dashboard.question_stats.map((stat) => (
                        <QuestionStatChart
                          key={stat.question_id}
                          stat={stat}
                          responseCount={dashboard.completion_count}
                          question={dashboard.questions_snapshot.find(
                            (q) => q.id === stat.question_id,
                          )}
                        />
                      ))}
                    </div>
                  </>
                ) : null}

                <h2 className="section-title">Attention flags</h2>
                {dashboard.flags.length === 0 ? (
                  <p className="muted">No flags.</p>
                ) : (
                  <ul className="meta-list">
                    {dashboard.flags.map((flag) => (
                      <li
                        key={`${flag.type}-${flag.player_id}-${flag.question_id ?? ""}`}
                      >
                        <span className="label">{flag.player_name}</span>
                        <span className="value">{flagLabel(flag)}</span>
                        <Link
                          className="btn btn--ghost"
                          to={`/players/${flag.player_id}`}
                        >
                          View
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}

                <h2 className="section-title">Players</h2>
                {dashboard.players.length === 0 ? (
                  <p className="muted">No assignment responses yet.</p>
                ) : (
                  <ul className="meta-list">
                    {dashboard.players.map((player) => (
                      <li key={player.player_id}>
                        <span className="label">{player.name}</span>
                        <span className="value">{player.status}</span>
                        {player.channel ? (
                          <span className="muted">{player.channel}</span>
                        ) : null}
                        <Link
                          className="btn btn--ghost"
                          to={`/players/${player.player_id}`}
                        >
                          Detail
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}
