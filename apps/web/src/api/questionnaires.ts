import { ApiError, readError } from "./auth";
import { apiFetch } from "./client";

export type QuestionType = "yes_no" | "rating" | "single_choice" | "short_text";

export type ChoiceOption = {
  id: string;
  label: string;
};

export type Question = {
  id: string;
  prompt: string;
  type: QuestionType;
  required: boolean;
  min?: number;
  max?: number;
  options?: ChoiceOption[];
  max_length?: number;
};

export type QuestionnaireTemplateOut = {
  id: string;
  key: string;
  name: string;
  description: string | null;
  questions: Question[];
  schema_version: number;
};

export type QuestionnaireOut = {
  id: string;
  organization_id: string;
  template_id: string | null;
  version: number;
  supersedes_id: string | null;
  name: string;
  description: string | null;
  questions: Question[];
  schema_version: number;
  created_by: string;
  locked_at: string | null;
  created_at: string;
};

export type QuestionnaireCreateInput = {
  name: string;
  description?: string | null;
  questions: Question[];
  template_id?: string | null;
};

export type QuestionnaireUpdateInput = {
  name?: string;
  description?: string | null;
  questions?: Question[];
};

export async function listQuestionnaireTemplates(): Promise<
  QuestionnaireTemplateOut[]
> {
  const response = await apiFetch("/api/v1/questionnaire-templates");
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as QuestionnaireTemplateOut[];
}

export async function listQuestionnaires(): Promise<QuestionnaireOut[]> {
  const response = await apiFetch("/api/v1/questionnaires");
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as QuestionnaireOut[];
}

export async function createQuestionnaire(
  input: QuestionnaireCreateInput,
): Promise<QuestionnaireOut> {
  const response = await apiFetch("/api/v1/questionnaires", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as QuestionnaireOut;
}

export async function updateQuestionnaire(
  id: string,
  input: QuestionnaireUpdateInput,
): Promise<QuestionnaireOut> {
  const response = await apiFetch(`/api/v1/questionnaires/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as QuestionnaireOut;
}
