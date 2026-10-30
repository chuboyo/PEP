import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useCreateRoutineMutation } from "../queries/routines";
import { useTeamsQuery } from "../queries/teams";

type ExerciseDraft = { name: string; duration_minutes: string };

export function CreateRoutinePage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const teamsQuery = useTeamsQuery(!!isCoach);
  const createMutation = useCreateRoutineMutation();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [objective, setObjective] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("25");
  const [intensity, setIntensity] = useState("");
  const [frequency, setFrequency] = useState("");
  const [instructions, setInstructions] = useState("");
  const [startDate, setStartDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [endDate, setEndDate] = useState("");
  const [teamId, setTeamId] = useState("");
  const [exercises, setExercises] = useState<ExerciseDraft[]>([
    { name: "", duration_minutes: "10" },
  ]);
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
    if (!teamId && (teamsQuery.data?.length ?? 0) > 0) {
      setTeamId(teamsQuery.data![0].id);
    }
  }, [teamId, teamsQuery.data]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSuccessCount(null);
    const parsedExercises = exercises
      .map((ex) => ({
        name: ex.name.trim(),
        duration_minutes: Number(ex.duration_minutes),
      }))
      .filter((ex) => ex.name && ex.duration_minutes > 0);
    if (parsedExercises.length === 0) {
      return;
    }
    createMutation.mutate(
      {
        name: name.trim(),
        description: description.trim(),
        objective: objective.trim(),
        exercises: parsedExercises,
        duration_minutes: Number(durationMinutes),
        intensity: intensity.trim() || null,
        frequency: frequency.trim() || null,
        start_date: startDate,
        end_date: endDate || null,
        instructions: instructions.trim() || null,
        team_id: teamId,
      },
      {
        onSuccess: (result) => {
          setSuccessCount(result.assignment_count);
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
        ? "Could not create routine"
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">New routine</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/routines">
              Routines
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            <span>Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={2}
            />
          </label>
          <label className="field">
            <span>Objective</span>
            <input
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              required
            />
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
            <span>Total duration (minutes)</span>
            <input
              type="number"
              min={1}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Start date</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>End date (optional)</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Intensity (optional)</span>
            <input
              value={intensity}
              onChange={(e) => setIntensity(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Frequency (optional)</span>
            <input
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Instructions (optional)</span>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={2}
            />
          </label>

          <h2 className="section-title">Exercises</h2>
          {exercises.map((exercise, index) => (
            <div className="inline-controls" key={index}>
              <label className="field">
                <span>Name</span>
                <input
                  value={exercise.name}
                  onChange={(e) => {
                    const next = [...exercises];
                    next[index] = { ...next[index], name: e.target.value };
                    setExercises(next);
                  }}
                  required
                />
              </label>
              <label className="field">
                <span>Minutes</span>
                <input
                  type="number"
                  min={1}
                  value={exercise.duration_minutes}
                  onChange={(e) => {
                    const next = [...exercises];
                    next[index] = {
                      ...next[index],
                      duration_minutes: e.target.value,
                    };
                    setExercises(next);
                  }}
                  required
                />
              </label>
            </div>
          ))}
          <button
            className="btn btn--ghost btn--control"
            type="button"
            onClick={() =>
              setExercises([
                ...exercises,
                { name: "", duration_minutes: "10" },
              ])
            }
          >
            Add exercise
          </button>

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
            disabled={createMutation.isPending || !teamId || !name.trim()}
          >
            {createMutation.isPending ? "Creating…" : "Create routine"}
          </button>
        </form>
      </div>
    </main>
  );
}
