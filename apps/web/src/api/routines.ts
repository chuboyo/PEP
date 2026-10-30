import { ApiError, readError } from "./auth";
import { apiFetch } from "./client";

export type ExerciseItem = {
  name: string;
  duration_minutes: number;
};

export type RoutineCreateInput = {
  name: string;
  description: string;
  objective: string;
  exercises: ExerciseItem[];
  duration_minutes: number;
  intensity?: string | null;
  frequency?: string | null;
  start_date: string;
  end_date?: string | null;
  instructions?: string | null;
  team_id?: string;
  player_ids?: string[];
};

export type RoutineOut = {
  id: string;
  organization_id: string;
  team_id: string | null;
  created_by: string;
  name: string;
  description: string;
  objective: string;
  exercises: ExerciseItem[];
  duration_minutes: number;
  intensity: string | null;
  frequency: string | null;
  start_date: string;
  end_date: string | null;
  instructions: string | null;
  created_at: string;
  assignment_count: number;
};

export type RoutineAssignmentOut = {
  id: string;
  routine_id: string;
  player_id: string;
  organization_id: string;
  status: "not_started" | "in_progress" | "completed";
  updated_at: string;
  routine_name: string;
  description: string;
  objective: string;
  exercises: ExerciseItem[];
  duration_minutes: number;
  intensity: string | null;
  frequency: string | null;
  start_date: string;
  end_date: string | null;
  instructions: string | null;
};

export function isRoutineAssignment(
  row: RoutineOut | RoutineAssignmentOut,
): row is RoutineAssignmentOut {
  return "routine_name" in row && "status" in row;
}

export async function createRoutine(
  input: RoutineCreateInput,
): Promise<RoutineOut> {
  const response = await apiFetch("/api/v1/routines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as RoutineOut;
}

export async function listRoutines(): Promise<
  Array<RoutineOut | RoutineAssignmentOut>
> {
  const response = await apiFetch("/api/v1/routines");
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as Array<RoutineOut | RoutineAssignmentOut>;
}

export async function updateRoutineStatus(
  assignmentId: string,
  status: "in_progress" | "completed",
): Promise<RoutineAssignmentOut> {
  const response = await apiFetch(
    `/api/v1/player/routines/${assignmentId}/status`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as RoutineAssignmentOut;
}
