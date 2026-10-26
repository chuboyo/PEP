import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useCreateTeamMutation } from "../queries/teams";

export function CreateTeamPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const createMutation = useCreateTeamMutation();
  const [name, setName] = useState("");

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isCoach) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isCoach, navigate]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate(name, {
      onSuccess: (team) => {
        navigate(`/teams/${team.id}`);
      },
    });
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
        ? "Could not create team"
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Create team</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/teams">
              All teams
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
          {errorMessage ? (
            <p className="alert" role="alert">
              {errorMessage}
            </p>
          ) : null}
          <button
            className="btn btn--primary"
            type="submit"
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? "Creating…" : "Create team"}
          </button>
        </form>
      </div>
    </main>
  );
}
