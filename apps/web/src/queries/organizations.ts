import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createOrganization,
  inviteCoach,
  listOrganizations,
  type OrganizationCreateInput,
} from "../api/organizations";

export const organizationsQueryKey = ["organizations"] as const;

export function useOrganizationsQuery(enabled: boolean) {
  return useQuery({
    queryKey: organizationsQueryKey,
    queryFn: listOrganizations,
    enabled,
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
  return useMutation({
    mutationFn: (input: { name: string; email: string }) =>
      inviteCoach(organizationId, input),
  });
}
