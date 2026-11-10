import { ApiError, readError } from "./auth";
import { apiFetch } from "./client";

export type OrganizationListItem = {
  id: string;
  name: string;
  status: string;
  admin_email: string | null;
};

export type OrganizationCreated = {
  id: string;
  name: string;
  status: string;
  admin_email: string;
  invite_link: string;
};

export type CoachInviteCreated = {
  organization_id: string;
  email: string;
  invite_link: string;
};

export type OrganizationCreateInput = {
  name: string;
  admin_name: string;
  admin_email: string;
  sport?: string;
  country?: string;
  location?: string;
  contact_email?: string;
};

export async function listOrganizations(): Promise<OrganizationListItem[]> {
  const response = await apiFetch("/api/v1/organizations");
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as OrganizationListItem[];
}

export async function createOrganization(
  input: OrganizationCreateInput,
): Promise<OrganizationCreated> {
  const response = await apiFetch("/api/v1/organizations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as OrganizationCreated;
}

export async function inviteCoach(
  organizationId: string,
  input: { name: string; email: string },
): Promise<CoachInviteCreated> {
  const response = await apiFetch(`/api/v1/organizations/${organizationId}/coaches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as CoachInviteCreated;
}

export type OrganizationMetrics = {
  organization_id: string;
  coach_count: number;
  player_count: number;
  active_player_count: number;
  questionnaire_completed_count: number;
  questionnaire_occurrence_count: number;
  routine_counts: {
    assigned: number;
    in_progress: number;
    completed: number;
  };
};

export type CoachListItem = {
  user_id: string;
  name: string;
  email: string;
  status: string;
};

export async function getOrganizationMetrics(
  organizationId: string,
): Promise<OrganizationMetrics> {
  const response = await apiFetch(
    `/api/v1/organizations/${organizationId}/metrics`,
  );
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as OrganizationMetrics;
}

export async function listCoaches(
  organizationId: string,
): Promise<CoachListItem[]> {
  const response = await apiFetch(
    `/api/v1/organizations/${organizationId}/coaches`,
  );
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as CoachListItem[];
}

export async function deactivateCoach(
  organizationId: string,
  userId: string,
): Promise<void> {
  const response = await apiFetch(
    `/api/v1/organizations/${organizationId}/coaches/${userId}/deactivate`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
}

export async function deactivatePlayer(
  organizationId: string,
  userId: string,
): Promise<void> {
  const response = await apiFetch(
    `/api/v1/organizations/${organizationId}/players/${userId}/deactivate`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
}
