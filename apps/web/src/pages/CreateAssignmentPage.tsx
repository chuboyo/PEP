import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useCreateAssignmentMutation } from "../queries/assignments";
import { useMeQuery } from "../queries/auth";
import { useQuestionnairesQuery } from "../queries/questionnaires";
import { useTeamsQuery } from "../queries/teams";

function localDateInputValue(date = new Date()): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

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
  const [channel, setChannel] = useState<"in_app" | "whatsapp">("in_app");
  const [schedule, setSchedule] = useState<"once" | "daily" | "weekly">(
    "once",
  );
  const [startsOn, setStartsOn] = useState(localDateInputValue);
  const [endsOn, setEndsOn] = useState("");
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

  const isRecurring = schedule === "daily" || schedule === "weekly";

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSuccessCount(null);
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
        channel,
        schedule,
        starts_on: isRecurring ? startsOn : undefined,
        ends_on: isRecurring && endsOn ? endsOn : undefined,
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
            <span>Schedule</span>
            <select
              value={schedule}
              onChange={(e) =>
                setSchedule(e.target.value as "once" | "daily" | "weekly")
              }
            >
              <option value="once">Once</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
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
          {isRecurring ? (
            <>
              <label className="field">
                <span>Starts on</span>
                <input
                  type="date"
                  value={startsOn}
                  onChange={(e) => setStartsOn(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Ends on (optional)</span>
                <input
                  type="date"
                  value={endsOn}
                  onChange={(e) => setEndsOn(e.target.value)}
                />
              </label>
            </>
          ) : null}
          <label className="field">
            <span>Channel</span>
            <select
              value={channel}
              onChange={(e) =>
                setChannel(e.target.value as "in_app" | "whatsapp")
              }
            >
              <option value="in_app">In app</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
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
              createMutation.isPending ||
              !questionnaireId ||
              !teamId ||
              !dueAt ||
              (isRecurring && !startsOn)
            }
          >
            {createMutation.isPending ? "Assigning…" : "Assign"}
          </button>
        </form>
      </div>
    </main>
  );
}
