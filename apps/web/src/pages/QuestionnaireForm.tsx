import { useState, type FormEvent } from "react";

import type { Question, QuestionType } from "../api/questionnaires";

function emptyQuestion(type: QuestionType): Question {
  const base = {
    id: "",
    prompt: "",
    type,
    required: true,
  };
  if (type === "rating") {
    return { ...base, min: 1, max: 5 };
  }
  if (type === "single_choice") {
    return {
      ...base,
      options: [{ id: "option_a", label: "Option A" }],
    };
  }
  if (type === "short_text") {
    return { ...base, max_length: 280 };
  }
  return base;
}

function normalizeQuestions(questions: Question[]): Question[] {
  return questions.map((q) => {
    if (q.type === "rating") {
      return {
        id: q.id,
        prompt: q.prompt,
        type: "rating",
        required: q.required,
        min: 1,
        max: 5,
      };
    }
    if (q.type === "single_choice") {
      return {
        id: q.id,
        prompt: q.prompt,
        type: "single_choice",
        required: q.required,
        options: (q.options ?? []).map((o) => ({
          id: o.id,
          label: o.label,
        })),
      };
    }
    if (q.type === "short_text") {
      return {
        id: q.id,
        prompt: q.prompt,
        type: "short_text",
        required: q.required,
        max_length: q.max_length ?? 280,
      };
    }
    return {
      id: q.id,
      prompt: q.prompt,
      type: "yes_no",
      required: q.required,
    };
  });
}

type Props = {
  initialName?: string;
  initialDescription?: string;
  initialQuestions?: Question[];
  submitLabel: string;
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (input: {
    name: string;
    description: string;
    questions: Question[];
  }) => void;
};

export function QuestionnaireForm({
  initialName = "",
  initialDescription = "",
  initialQuestions = [],
  submitLabel,
  pending,
  errorMessage,
  onSubmit,
}: Props) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [questions, setQuestions] = useState<Question[]>(
    initialQuestions.length > 0 ? initialQuestions : [],
  );
  const [addType, setAddType] = useState<QuestionType>("yes_no");

  function updateQuestion(index: number, patch: Partial<Question>) {
    setQuestions((prev) =>
      prev.map((q, i) => (i === index ? { ...q, ...patch } : q)),
    );
  }

  function removeQuestion(index: number) {
    setQuestions((prev) => prev.filter((_, i) => i !== index));
  }

  function addQuestion() {
    setQuestions((prev) => [...prev, emptyQuestion(addType)]);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      name,
      description,
      questions: normalizeQuestions(questions),
    });
  }

  return (
    <form className="stack" onSubmit={handleSubmit}>
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
          rows={2}
        />
      </label>

      <h2 className="section-title">Questions</h2>
      {questions.length === 0 ? (
        <p className="muted">No questions yet. Add one below.</p>
      ) : null}

      {questions.map((question, index) => (
        <div key={index} className="stack">
          <label className="field">
            <span>Type</span>
            <select
              value={question.type}
              onChange={(e) => {
                const type = e.target.value as QuestionType;
                setQuestions((prev) =>
                  prev.map((q, i) =>
                    i === index
                      ? { ...emptyQuestion(type), id: q.id, prompt: q.prompt }
                      : q,
                  ),
                );
              }}
            >
              <option value="yes_no">Yes / No</option>
              <option value="rating">Rating (1–5)</option>
              <option value="single_choice">Single choice</option>
              <option value="short_text">Short text</option>
            </select>
          </label>
          <label className="field">
            <span>Id</span>
            <input
              value={question.id}
              onChange={(e) => updateQuestion(index, { id: e.target.value })}
              placeholder="sleep"
              required
            />
          </label>
          <label className="field">
            <span>Prompt</span>
            <input
              value={question.prompt}
              onChange={(e) =>
                updateQuestion(index, { prompt: e.target.value })
              }
              required
            />
          </label>
          <label className="field field--check">
            <input
              type="checkbox"
              checked={question.required}
              onChange={(e) =>
                updateQuestion(index, { required: e.target.checked })
              }
            />
            <span>Required</span>
          </label>

          {question.type === "single_choice" ? (
            <>
              {(question.options ?? []).map((option, optIndex) => (
                <div key={optIndex} className="stack">
                  <label className="field">
                    <span>Option id</span>
                    <input
                      value={option.id}
                      onChange={(e) => {
                        const options = [...(question.options ?? [])];
                        options[optIndex] = {
                          ...options[optIndex],
                          id: e.target.value,
                        };
                        updateQuestion(index, { options });
                      }}
                      required
                    />
                  </label>
                  <label className="field">
                    <span>Option label</span>
                    <input
                      value={option.label}
                      maxLength={24}
                      onChange={(e) => {
                        const options = [...(question.options ?? [])];
                        options[optIndex] = {
                          ...options[optIndex],
                          label: e.target.value,
                        };
                        updateQuestion(index, { options });
                      }}
                      required
                    />
                  </label>
                  <button
                    className="btn btn--ghost"
                    type="button"
                    onClick={() => {
                      const options = (question.options ?? []).filter(
                        (_, i) => i !== optIndex,
                      );
                      updateQuestion(index, { options });
                    }}
                  >
                    Remove option
                  </button>
                </div>
              ))}
              <button
                className="btn btn--ghost"
                type="button"
                onClick={() => {
                  const options = [
                    ...(question.options ?? []),
                    {
                      id: `option_${(question.options?.length ?? 0) + 1}`,
                      label: "New option",
                    },
                  ];
                  updateQuestion(index, { options });
                }}
              >
                Add option
              </button>
            </>
          ) : null}

          {question.type === "short_text" ? (
            <label className="field">
              <span>Max length</span>
              <input
                type="number"
                min={1}
                value={question.max_length ?? 280}
                onChange={(e) =>
                  updateQuestion(index, {
                    max_length: Number(e.target.value) || 280,
                  })
                }
              />
            </label>
          ) : null}

          <button
            className="btn btn--ghost"
            type="button"
            onClick={() => removeQuestion(index)}
          >
            Remove question
          </button>
        </div>
      ))}

      <div className="inline-controls">
        <label className="field">
          <span>Question type</span>
          <select
            value={addType}
            onChange={(e) => setAddType(e.target.value as QuestionType)}
          >
            <option value="yes_no">Yes / No</option>
            <option value="rating">Rating (1–5)</option>
            <option value="single_choice">Single choice</option>
            <option value="short_text">Short text</option>
          </select>
        </label>
        <button
          className="btn btn--ghost btn--control"
          type="button"
          onClick={addQuestion}
        >
          Add question
        </button>
      </div>

      {errorMessage ? (
        <p className="alert" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <button
        className="btn btn--primary"
        type="submit"
        disabled={pending || questions.length === 0}
      >
        {pending ? "Saving…" : submitLabel}
      </button>
    </form>
  );
}
