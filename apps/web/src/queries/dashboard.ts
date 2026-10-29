import { useQuery } from "@tanstack/react-query";

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
