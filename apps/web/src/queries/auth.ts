import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { fetchMe, login } from "../api/auth";
import { logoutApi } from "../api/client";
import { getAccessToken, setTokens } from "../auth";

export const meQueryKey = ["me"] as const;

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
      queryClient.removeQueries({ queryKey: meQueryKey });
      navigate("/login");
    },
  });
}
