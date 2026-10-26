import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { acceptInvite, fetchMe, login } from "../api/auth";
import { logoutApi } from "../api/client";
import { getAccessToken, setTokens } from "../auth";

export const meQueryKey = ["me"] as const;

/** Drop cached /me so the next session cannot show a previous user. */
export function clearMeQuery(queryClient: QueryClient): void {
  queryClient.removeQueries({ queryKey: meQueryKey });
}

export function useMeQuery() {
  const hasToken = !!getAccessToken();

  return useQuery({
    queryKey: meQueryKey,
    queryFn: fetchMe,
    enabled: hasToken,
  });
}

export function useLoginMutation() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      await queryClient.invalidateQueries({ queryKey: meQueryKey });
      navigate("/");
    },
  });
}

export function useLogoutMutation() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: logoutApi,
    onSuccess: () => {
      clearMeQuery(queryClient);
      navigate("/login");
    },
  });
}

export function useAcceptInviteMutation() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: ({ token, password }: { token: string; password: string }) =>
      acceptInvite(token, password),
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      clearMeQuery(queryClient);
      await queryClient.invalidateQueries({ queryKey: meQueryKey });
      navigate("/");
    },
  });
}
