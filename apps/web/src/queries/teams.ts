import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createTeam, getTeam, invitePlayer, listTeams } from "../api/teams";

export const teamsQueryKey = ["teams"] as const;

export function teamQueryKey(teamId: string) {
  return ["teams", teamId] as const;
}

export function useTeamsQuery(enabled: boolean) {
  return useQuery({
    queryKey: teamsQueryKey,
    queryFn: listTeams,
    enabled,
  });
}

export function useTeamQuery(teamId: string, enabled: boolean) {
  return useQuery({
    queryKey: teamQueryKey(teamId),
    queryFn: () => getTeam(teamId),
    enabled: enabled && !!teamId,
  });
}

export function useCreateTeamMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => createTeam(name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: teamsQueryKey });
    },
  });
}

export function useInvitePlayerMutation(teamId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; email: string; phone_e164?: string }) =>
      invitePlayer(teamId, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: teamQueryKey(teamId) });
    },
  });
}
