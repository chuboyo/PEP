import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { remindOccurrence } from "../api/assignments";
import { getPlayerDetail, getTeamDashboard } from "../api/dashboard";

export function dashboardQueryKey(teamId: string, questionnaireId?: string) {
  return ["dashboard", teamId, questionnaireId ?? null] as const;
}

export function playerDetailQueryKey(playerId: string) {
  return ["players", playerId] as const;
}

export function useTeamDashboardQuery(
  teamId: string,
  enabled: boolean,
  questionnaireId?: string,
) {
  return useQuery({
    queryKey: dashboardQueryKey(teamId, questionnaireId),
    queryFn: () => getTeamDashboard(teamId, questionnaireId),
    enabled: enabled && !!teamId,
  });
}

export function usePlayerDetailQuery(playerId: string, enabled: boolean) {
  return useQuery({
    queryKey: playerDetailQueryKey(playerId),
    queryFn: () => getPlayerDetail(playerId),
    enabled: enabled && !!playerId,
  });
}

export function useRemindOccurrenceMutation(teamId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (occurrenceId: string) => remindOccurrence(occurrenceId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["dashboard", teamId],
      });
    },
  });
}
