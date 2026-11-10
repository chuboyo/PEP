import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createOrganization,
  deactivateCoach,
  deactivatePlayer,
  getOrganizationMetrics,
  inviteCoach,
  listCoaches,
  listOrganizations,
  type OrganizationCreateInput,
} from "../api/organizations";

export const organizationsQueryKey = ["organizations"] as const;

export function organizationMetricsQueryKey(organizationId: string) {
  return ["organizations", organizationId, "metrics"] as const;
}

export function organizationCoachesQueryKey(organizationId: string) {
  return ["organizations", organizationId, "coaches"] as const;
}

export function useOrganizationsQuery(enabled: boolean) {
  return useQuery({
    queryKey: organizationsQueryKey,
    queryFn: listOrganizations,
    enabled,
  });
}

export function useOrganizationMetricsQuery(
  organizationId: string,
  enabled: boolean,
) {
  return useQuery({
    queryKey: organizationMetricsQueryKey(organizationId),
    queryFn: () => getOrganizationMetrics(organizationId),
    enabled: enabled && !!organizationId,
  });
}

export function useOrganizationCoachesQuery(
  organizationId: string,
  enabled: boolean,
) {
  return useQuery({
    queryKey: organizationCoachesQueryKey(organizationId),
    queryFn: () => listCoaches(organizationId),
    enabled: enabled && !!organizationId,
  });
}

export function useCreateOrganizationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: OrganizationCreateInput) => createOrganization(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: organizationsQueryKey });
    },
  });
}

export function useInviteCoachMutation(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; email: string }) =>
      inviteCoach(organizationId, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationCoachesQueryKey(organizationId),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationMetricsQueryKey(organizationId),
      });
    },
  });
}

export function useDeactivateCoachMutation(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => deactivateCoach(organizationId, userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationCoachesQueryKey(organizationId),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationMetricsQueryKey(organizationId),
      });
    },
  });
}

export function useDeactivatePlayerMutation(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => deactivatePlayer(organizationId, userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["teams"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      await queryClient.invalidateQueries({ queryKey: ["players"] });
      await queryClient.invalidateQueries({
        queryKey: organizationMetricsQueryKey(organizationId),
      });
    },
  });
}
