import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createRoutine,
  listRoutines,
  updateRoutineStatus,
  type RoutineCreateInput,
} from "../api/routines";

export const routinesQueryKey = ["routines"] as const;

export function useRoutinesQuery(enabled: boolean) {
  return useQuery({
    queryKey: routinesQueryKey,
    queryFn: listRoutines,
    enabled,
  });
}

export function useCreateRoutineMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RoutineCreateInput) => createRoutine(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: routinesQueryKey });
    },
  });
}

export function useUpdateRoutineStatusMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      assignmentId,
      status,
    }: {
      assignmentId: string;
      status: "in_progress" | "completed";
    }) => updateRoutineStatus(assignmentId, status),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: routinesQueryKey });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
