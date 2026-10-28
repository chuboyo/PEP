import { ApiError, readError } from "./auth";
import { apiFetch } from "./client";
import type { Question } from "./questionnaires";

export type PlayerOccurrenceOut = {
  id: string;
  assignment_id: string;
  organization_id: string;
  player_id: string;
  status: string;
  due_at: string | null;
  window_start: string;
  questionnaire_name: string;
  questions: Question[];
  created_at: string;
};

export type OccurrenceResponseOut = {
  id: string;
  occurrence_id: string;
  organization_id: string;
  player_id: string;
  channel: string;
  answers: Record<string, unknown>;
  submitted_at: string;
};

export async function listMyOccurrences(): Promise<PlayerOccurrenceOut[]> {
  const response = await apiFetch("/api/v1/player/occurrences");
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as PlayerOccurrenceOut[];
}

export async function submitOccurrenceResponse(
  occurrenceId: string,
  answers: Record<string, unknown>,
): Promise<OccurrenceResponseOut> {
  const response = await apiFetch(
    `/api/v1/player/occurrences/${occurrenceId}/responses`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    },
  );
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as OccurrenceResponseOut;
}
