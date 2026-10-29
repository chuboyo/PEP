import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getPlayerHistory,
  listMyOccurrences,
  submitOccurrenceResponse,
} from "../api/player";

export const playerOccurrencesQueryKey = ["player", "occurrences"] as const;
export const playerHistoryQueryKey = ["player", "history"] as const;

export function usePlayerOccurrencesQuery(enabled: boolean) {
  return useQuery({
    queryKey: playerOccurrencesQueryKey,
    queryFn: listMyOccurrences,
    enabled,
  });
}

export function usePlayerHistoryQuery(enabled: boolean) {
  return useQuery({
    queryKey: playerHistoryQueryKey,
    queryFn: getPlayerHistory,
    enabled,
  });
}

export function useSubmitOccurrenceResponseMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      occurrenceId,
      answers,
    }: {
      occurrenceId: string;
      answers: Record<string, unknown>;
    }) => submitOccurrenceResponse(occurrenceId, answers),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: playerOccurrencesQueryKey,
      });
      await queryClient.invalidateQueries({
        queryKey: playerHistoryQueryKey,
      });
    },
  });
}
