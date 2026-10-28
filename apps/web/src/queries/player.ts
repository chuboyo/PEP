import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listMyOccurrences, submitOccurrenceResponse } from "../api/player";

export const playerOccurrencesQueryKey = ["player", "occurrences"] as const;

export function usePlayerOccurrencesQuery(enabled: boolean) {
  return useQuery({
    queryKey: playerOccurrencesQueryKey,
    queryFn: listMyOccurrences,
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
    },
  });
}
