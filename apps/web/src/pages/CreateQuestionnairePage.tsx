import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { Question } from "../api/questionnaires";
import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import {
  useCreateQuestionnaireMutation,
  useQuestionnaireTemplatesQuery,
} from "../queries/questionnaires";
import { QuestionnaireForm } from "./QuestionnaireForm";

export function CreateQuestionnairePage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const templatesQuery = useQuestionnaireTemplatesQuery(!!isCoach);
  const createMutation = useCreateQuestionnaireMutation();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [formKey, setFormKey] = useState(0);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isCoach) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isCoach, navigate]);

  function cloneTemplate(templateKey: string) {
    const template = templatesQuery.data?.find((t) => t.key === templateKey);
    if (!template) {
      return;
    }
    setName(template.name);
    setDescription(template.description ?? "");
    setQuestions(template.questions);
    setTemplateId(template.id);
    setFormKey((k) => k + 1);
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
        ? "Could not create questionnaire"
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">New questionnaire</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/questionnaires">
              All questionnaires
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <h2 className="section-title">Clone a template</h2>
        {templatesQuery.isPending ? (
          <p className="muted">Loading templates…</p>
        ) : templatesQuery.isError ? (
          <p className="alert" role="alert">
            Could not load templates
          </p>
        ) : (
          <ul className="meta-list">
            {templatesQuery.data?.map((template) => (
              <li key={template.id}>
                <span className="value">{template.name}</span>
                <span className="muted">{template.description}</span>
                <button
                  className="btn btn--ghost"
                  type="button"
                  onClick={() => cloneTemplate(template.key)}
                >
                  Clone
                </button>
              </li>
            ))}
          </ul>
        )}

        <h2 className="section-title">Questionnaire</h2>
        <QuestionnaireForm
          key={formKey}
          initialName={name}
          initialDescription={description}
          initialQuestions={questions}
          submitLabel="Create questionnaire"
          pending={createMutation.isPending}
          errorMessage={errorMessage}
          onSubmit={(input) => {
            createMutation.mutate(
              {
                name: input.name,
                description: input.description || null,
                questions: input.questions,
                template_id: templateId,
              },
              {
                onSuccess: () => {
                  navigate("/questionnaires");
                },
              },
            );
          }}
        />
      </div>
    </main>
  );
}
