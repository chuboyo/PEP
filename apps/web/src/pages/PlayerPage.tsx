import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { PlayerOccurrenceOut } from "../api/player";
import type { Question } from "../api/questionnaires";
import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import {
  usePlayerOccurrencesQuery,
  useSubmitOccurrenceResponseMutation,
} from "../queries/player";

function AnswerFields({
  questions,
  answers,
  onChange,
}: {
  questions: Question[];
  answers: Record<string, unknown>;
  onChange: (id: string, value: unknown) => void;
}) {
  return (
    <>
      {questions.map((question) => (
        <label key={question.id} className="field">
          <span>
            {question.prompt}
            {question.required ? " *" : ""}
          </span>
          {question.type === "yes_no" ? (
            <select
              value={
                answers[question.id] === true
                  ? "yes"
                  : answers[question.id] === false
                    ? "no"
                    : ""
              }
              onChange={(e) => {
                if (e.target.value === "") {
                  onChange(question.id, undefined);
                  return;
                }
                onChange(question.id, e.target.value === "yes");
              }}
              required={question.required}
            >
              <option value="">Select…</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          ) : null}
          {question.type === "rating" ? (
            <select
              value={
                typeof answers[question.id] === "number"
                  ? String(answers[question.id])
                  : ""
              }
              onChange={(e) =>
                onChange(
                  question.id,
                  e.target.value ? Number(e.target.value) : undefined,
                )
              }
              required={question.required}
            >
              <option value="">Select…</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          ) : null}
          {question.type === "single_choice" ? (
            <select
              value={
                typeof answers[question.id] === "string"
                  ? String(answers[question.id])
                  : ""
              }
              onChange={(e) =>
                onChange(question.id, e.target.value || undefined)
              }
              required={question.required}
            >
              <option value="">Select…</option>
              {(question.options ?? []).map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          ) : null}
          {question.type === "short_text" ? (
            <input
              value={
                typeof answers[question.id] === "string"
                  ? String(answers[question.id])
                  : ""
              }
              maxLength={question.max_length ?? 280}
              onChange={(e) => onChange(question.id, e.target.value)}
              required={question.required}
            />
          ) : null}
        </label>
      ))}
    </>
  );
}

export function PlayerPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isPlayer = me?.memberships.some(
    (m) => m.role === "PLAYER" && m.status === "active",
  );
  const occurrencesQuery = usePlayerOccurrencesQuery(!!isPlayer);
  const submitMutation = useSubmitOccurrenceResponseMutation();

  const [activeId, setActiveId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isPlayer) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isPlayer, navigate]);

  const pending =
    occurrencesQuery.data?.filter((o) => o.status === "pending") ?? [];
  const completed =
    occurrencesQuery.data?.filter((o) => o.status === "completed") ?? [];
  const active: PlayerOccurrenceOut | undefined = pending.find(
    (o) => o.id === activeId,
  );

  function openOccurrence(occurrence: PlayerOccurrenceOut) {
    setActiveId(occurrence.id);
    setAnswers({});
    submitMutation.reset();
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!active) {
      return;
    }
    const payload: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(answers)) {
      if (value !== undefined) {
        payload[key] = value;
      }
    }
    submitMutation.mutate(
      { occurrenceId: active.id, answers: payload },
      {
        onSuccess: () => {
          setActiveId(null);
          setAnswers({});
        },
      },
    );
  }

  if (!hasToken || mePending || !isPlayer) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const errorMessage =
    submitMutation.error instanceof Error
      ? submitMutation.error.message
      : submitMutation.isError
        ? "Could not submit answers"
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">My questionnaires</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {occurrencesQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : occurrencesQuery.isError ? (
          <p className="alert" role="alert">
            Could not load questionnaires
          </p>
        ) : active ? (
          <form className="stack" onSubmit={onSubmit}>
            <h2 className="section-title">{active.questionnaire_name}</h2>
            <AnswerFields
              questions={active.questions}
              answers={answers}
              onChange={(id, value) =>
                setAnswers((prev) => {
                  const next = { ...prev };
                  if (value === undefined) {
                    delete next[id];
                  } else {
                    next[id] = value;
                  }
                  return next;
                })
              }
            />
            {errorMessage ? (
              <p className="alert" role="alert">
                {errorMessage}
              </p>
            ) : null}
            <div className="nav-links">
              <button
                className="btn btn--primary"
                type="submit"
                disabled={submitMutation.isPending}
              >
                {submitMutation.isPending ? "Submitting…" : "Submit"}
              </button>
              <button
                className="btn btn--ghost"
                type="button"
                onClick={() => {
                  setActiveId(null);
                  setAnswers({});
                  submitMutation.reset();
                }}
              >
                Back
              </button>
            </div>
          </form>
        ) : (
          <>
            <h2 className="section-title">Pending</h2>
            {pending.length === 0 ? (
              <p className="muted">No pending questionnaires.</p>
            ) : (
              <ul className="meta-list">
                {pending.map((occurrence) => (
                  <li key={occurrence.id}>
                    <span className="value">{occurrence.questionnaire_name}</span>
                    <button
                      className="btn btn--ghost"
                      type="button"
                      onClick={() => openOccurrence(occurrence)}
                    >
                      Answer
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <h2 className="section-title">Completed</h2>
            {completed.length === 0 ? (
              <p className="muted">None yet.</p>
            ) : (
              <ul className="meta-list">
                {completed.map((occurrence) => (
                  <li key={occurrence.id}>
                    <span className="value">{occurrence.questionnaire_name}</span>
                    <span className="muted">Completed</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </main>
  );
}
