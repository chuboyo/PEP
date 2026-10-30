import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  isRoutineAssignment,
  type RoutineAssignmentOut,
  type RoutineOut,
} from "../api/routines";
import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import {
  useRoutinesQuery,
  useUpdateRoutineStatusMutation,
} from "../queries/routines";

function nextStatus(
  status: RoutineAssignmentOut["status"],
): "in_progress" | "completed" | null {
  if (status === "not_started") {
    return "in_progress";
  }
  if (status === "in_progress") {
    return "completed";
  }
  return null;
}

function CoachRoutineList({ routines }: { routines: RoutineOut[] }) {
  if (routines.length === 0) {
    return <p className="muted">No routines yet.</p>;
  }
  return (
    <ul className="meta-list">
      {routines.map((routine) => (
        <li key={routine.id}>
          <span className="label">{routine.name}</span>
          <span className="value">{routine.objective}</span>
          <span className="muted">
            {routine.assignment_count} assignment
            {routine.assignment_count === 1 ? "" : "s"}
          </span>
        </li>
      ))}
    </ul>
  );
}

function PlayerRoutineList({
  assignments,
}: {
  assignments: RoutineAssignmentOut[];
}) {
  const updateMutation = useUpdateRoutineStatusMutation();

  if (assignments.length === 0) {
    return <p className="muted">No routines assigned.</p>;
  }

  return (
    <div className="occurrence-stack">
      {assignments.map((assignment) => {
        const advance = nextStatus(assignment.status);
        return (
          <article className="occurrence-card" key={assignment.id}>
            <header className="occurrence-card__header">
              <h3 className="chart-card__title">{assignment.routine_name}</h3>
              <span className="occurrence-card__status">
                {assignment.status.replace("_", " ")}
              </span>
            </header>
            <p className="chart-card__caption">{assignment.objective}</p>
            <ul className="meta-list">
              {assignment.exercises.map((exercise) => (
                <li key={`${assignment.id}-${exercise.name}`}>
                  <span className="label">{exercise.name}</span>
                  <span className="value">
                    {exercise.duration_minutes} min
                  </span>
                </li>
              ))}
            </ul>
            {advance ? (
              <button
                className="btn btn--primary"
                type="button"
                disabled={updateMutation.isPending}
                onClick={() =>
                  updateMutation.mutate({
                    assignmentId: assignment.id,
                    status: advance,
                  })
                }
              >
                {advance === "in_progress"
                  ? "Mark in progress"
                  : "Mark completed"}
              </button>
            ) : (
              <p className="muted">Completed</p>
            )}
          </article>
        );
      })}
    </div>
  );
}

export function RoutinesPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const isPlayer = me?.memberships.some(
    (m) => m.role === "PLAYER" && m.status === "active",
  );
  const routinesQuery = useRoutinesQuery(!!isCoach || !!isPlayer);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isCoach && !isPlayer) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isCoach, isPlayer, navigate]);

  if (!hasToken || mePending || (!isCoach && !isPlayer)) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const rows = routinesQuery.data ?? [];
  const coachRoutines = isCoach
    ? (rows.filter((row) => !isRoutineAssignment(row)) as RoutineOut[])
    : [];
  const playerAssignments = isPlayer
    ? (rows.filter((row) => isRoutineAssignment(row)) as RoutineAssignmentOut[])
    : [];

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Routines</h1>
          <div className="nav-links">
            {isCoach ? (
              <Link className="btn btn--primary" to="/routines/new">
                New routine
              </Link>
            ) : null}
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {routinesQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : routinesQuery.isError ? (
          <p className="alert" role="alert">
            Could not load routines
          </p>
        ) : isCoach ? (
          <CoachRoutineList routines={coachRoutines} />
        ) : (
          <PlayerRoutineList assignments={playerAssignments} />
        )}
      </div>
    </main>
  );
}
