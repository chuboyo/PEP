import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import {
  useQuestionnairesQuery,
  useUpdateQuestionnaireMutation,
} from "../queries/questionnaires";
import { QuestionnaireForm } from "./QuestionnaireForm";

export function EditQuestionnairePage() {
  const { questionnaireId = "" } = useParams();
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const listQuery = useQuestionnairesQuery(!!isCoach);
  const updateMutation = useUpdateQuestionnaireMutation();

  const questionnaire = listQuery.data?.find((q) => q.id === questionnaireId);

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

  if (listQuery.isPending) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  if (listQuery.isError) {
    return (
      <main className="shell shell--center">
        <div className="panel panel--wide">
          <p className="alert" role="alert">
            Could not load questionnaires
          </p>
          <Link className="btn btn--ghost" to="/questionnaires">
            All questionnaires
          </Link>
        </div>
      </main>
    );
  }

  if (!questionnaire) {
    return (
      <main className="shell shell--center">
        <div className="panel panel--wide">
          <p className="alert" role="alert">
            Questionnaire not found
          </p>
          <Link className="btn btn--ghost" to="/questionnaires">
            All questionnaires
          </Link>
        </div>
      </main>
    );
  }

  const errorMessage =
    updateMutation.error instanceof Error
      ? updateMutation.error.message
      : updateMutation.isError
        ? "Could not update questionnaire"
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Edit questionnaire</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/questionnaires">
              All questionnaires
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {questionnaire.locked_at ? (
          <p className="muted">
            This version is locked. Saving creates a new version.
          </p>
        ) : null}

        <QuestionnaireForm
          key={questionnaire.id}
          initialName={questionnaire.name}
          initialDescription={questionnaire.description ?? ""}
          initialQuestions={questionnaire.questions}
          submitLabel={
            questionnaire.locked_at ? "Save as new version" : "Save changes"
          }
          pending={updateMutation.isPending}
          errorMessage={errorMessage}
          onSubmit={(input) => {
            updateMutation.mutate(
              {
                id: questionnaire.id,
                input: {
                  name: input.name,
                  description: input.description || null,
                  questions: input.questions,
                },
              },
              {
                onSuccess: (updated) => {
                  navigate(`/questionnaires/${updated.id}/edit`);
                },
              },
            );
          }}
        />
      </div>
    </main>
  );
}
