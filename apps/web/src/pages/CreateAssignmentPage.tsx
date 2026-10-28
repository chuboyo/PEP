import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useCreateAssignmentMutation } from "../queries/assignments";
import { useMeQuery } from "../queries/auth";
import { useQuestionnairesQuery } from "../queries/questionnaires";
import { useTeamsQuery } from "../queries/teams";

export function CreateAssignmentPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const questionnairesQuery = useQuestionnairesQuery(!!isCoach);
  const teamsQuery = useTeamsQuery(!!isCoach);
  const createMutation = useCreateAssignmentMutation();

  const [questionnaireId, setQuestionnaireId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [successCount, setSuccessCount] = useState<number | null>(null);

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
    if (!questionnaireId && (questionnairesQuery.data?.length ?? 0) > 0) {
      setQuestionnaireId(questionnairesQuery.data![0].id);
    }
  }, [questionnaireId, questionnairesQuery.data]);

  useEffect(() => {
    if (!teamId && (teamsQuery.data?.length ?? 0) > 0) {
      setTeamId(teamsQuery.data![0].id);
    }
  }, [teamId, teamsQuery.data]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSuccessCount(null);
    // datetime-local is wall time in the browser's timezone; convert to UTC ISO.
    const due = new Date(dueAt);
    if (Number.isNaN(due.getTime())) {
      return;
    }
    createMutation.mutate(
      {
        questionnaire_id: questionnaireId,
        target_type: "team",
        team_id: teamId,
        due_at: due.toISOString(),
        channel: "in_app",
        schedule: "once",
      },
      {
        onSuccess: (result) => {
          setSuccessCount(result.occurrence_count);
        },
      },
    );
  }

  if (!hasToken || mePending || !isCoach) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const errorMessage =
    createMutation.error instanceof Error
      ? createMutation.error.message
      : createMutation.isError
        ? "Could not create assignment"
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Assign questionnaire</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            <span>Questionnaire</span>
            <select
              value={questionnaireId}
              onChange={(e) => setQuestionnaireId(e.target.value)}
              required
            >
              {(questionnairesQuery.data ?? []).map((q) => (
                <option key={q.id} value={q.id}>
                  {q.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Team</span>
            <select
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              required
            >
              {(teamsQuery.data ?? []).map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Due at (your local timezone)</span>
            <input
              type="datetime-local"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
              required
            />
          </label>
          {errorMessage ? (
            <p className="alert" role="alert">
              {errorMessage}
            </p>
          ) : null}
          {successCount !== null ? (
            <p className="muted">
              Assigned to {successCount} player
              {successCount === 1 ? "" : "s"}.
            </p>
          ) : null}
          <button
            className="btn btn--primary"
            type="submit"
            disabled={
              createMutation.isPending || !questionnaireId || !teamId || !dueAt
            }
          >
            {createMutation.isPending ? "Assigning…" : "Assign"}
          </button>
        </form>
      </div>
    </main>
  );
}
