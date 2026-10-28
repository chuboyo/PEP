import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useQuestionnairesQuery } from "../queries/questionnaires";

export function QuestionnairesPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const questionnairesQuery = useQuestionnairesQuery(!!isCoach);

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
          <h1 className="brand">Questionnaires</h1>
          <div className="nav-links">
            <Link className="btn btn--primary" to="/questionnaires/new">
              New questionnaire
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {questionnairesQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : questionnairesQuery.isError ? (
          <p className="alert" role="alert">
            Could not load questionnaires
          </p>
        ) : (questionnairesQuery.data?.length ?? 0) === 0 ? (
          <p className="muted">No questionnaires yet.</p>
        ) : (
          <ul className="meta-list">
            {questionnairesQuery.data?.map((q) => (
              <li key={q.id}>
                <span className="label">v{q.version}</span>
                <span className="value">
                  <Link to={`/questionnaires/${q.id}/edit`}>{q.name}</Link>
                </span>
                <span className="muted">
                  {q.locked_at ? "Locked" : "Editable"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
