import { ApiError, readError } from "./auth";
import { apiFetch } from "./client";
import type { Question } from "./questionnaires";

export type QuestionStat = {
  question_id: string;
  question_type: string;
  prompt: string;
  average: number | null;
  yes_count: number | null;
  option_counts: Record<string, number> | null;
};

export type DashboardPlayerRow = {
  player_id: string;
  name: string;
  status: string;
  submitted_at: string | null;
  channel: string | null;
  answers: Record<string, unknown> | null;
};

export type AttentionFlag = {
  type: "high_rating_streak" | "missed_streak";
  player_id: string;
  player_name: string;
  question_id: string | null;
};

export type RoutineCounts = {
  assigned: number;
  in_progress: number;
  completed: number;
};

export type TeamDashboard = {
  team_id: string;
  assignment_id: string | null;
  questionnaire_id: string | null;
  questionnaire_name: string | null;
  questions_snapshot: Question[];
  completion_count: number;
  roster_size: number;
  question_stats: QuestionStat[];
  players: DashboardPlayerRow[];
  flags: AttentionFlag[];
  routine_counts: RoutineCounts;
};

export type PlayerOccurrenceHistory = {
  occurrence_id: string;
  assignment_id: string;
  questionnaire_id: string;
  questionnaire_name: string;
  status: string;
  due_at: string | null;
  submitted_at: string | null;
  channel: string | null;
  answers: Record<string, unknown> | null;
  questions_snapshot: Question[];
};

export type PlayerDetail = {
  id: string;
  name: string;
  email: string;
  occurrences: PlayerOccurrenceHistory[];
};

export async function getTeamDashboard(
  teamId: string,
  questionnaireId?: string,
): Promise<TeamDashboard> {
  const params = new URLSearchParams();
  if (questionnaireId) {
    params.set("questionnaire_id", questionnaireId);
  }
  const query = params.toString();
  const path = `/api/v1/teams/${teamId}/dashboard${query ? `?${query}` : ""}`;
  const response = await apiFetch(path);
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as TeamDashboard;
}

export async function getPlayerDetail(playerId: string): Promise<PlayerDetail> {
  const response = await apiFetch(`/api/v1/players/${playerId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as PlayerDetail;
}
