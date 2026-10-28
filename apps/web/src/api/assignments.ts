import { ApiError, readError } from "./auth";
import { apiFetch } from "./client";
import type { Question } from "./questionnaires";

export type AssignmentOut = {
  id: string;
  organization_id: string;
  questionnaire_id: string;
  questions_snapshot: Question[];
  created_by: string;
  target_type: string;
  team_id: string | null;
  schedule: string;
  due_at: string | null;
  channel: string;
  created_at: string;
  occurrence_count: number;
};

export type AssignmentCreateInput = {
  questionnaire_id: string;
  target_type: "team" | "players";
  team_id?: string;
  player_ids?: string[];
  due_at: string;
  channel?: "in_app" | "whatsapp";
  schedule?: "once" | "daily" | "weekly";
};

export async function createAssignment(
  input: AssignmentCreateInput,
): Promise<AssignmentOut> {
  const response = await apiFetch("/api/v1/assignments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      channel: "in_app",
      schedule: "once",
      ...input,
    }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as AssignmentOut;
}
