import { ApiError, readError } from "./auth";
import { apiFetch } from "./client";

export type TeamOut = {
  id: string;
  organization_id: string;
  name: string;
};

export type TeamMemberOut = {
  user_id: string;
  name: string;
  email: string;
  role: string | null;
  phone_e164: string | null;
};

export type TeamDetailOut = TeamOut & {
  members: TeamMemberOut[];
};

export type PlayerInviteCreated = {
  organization_id: string;
  team_id: string;
  email: string;
  invite_link: string;
};

export async function listTeams(): Promise<TeamOut[]> {
  const response = await apiFetch("/api/v1/teams");
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as TeamOut[];
}

export async function createTeam(name: string): Promise<TeamOut> {
  const response = await apiFetch("/api/v1/teams", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as TeamOut;
}

export async function getTeam(teamId: string): Promise<TeamDetailOut> {
  const response = await apiFetch(`/api/v1/teams/${teamId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as TeamDetailOut;
}

export async function invitePlayer(
  teamId: string,
  input: { name: string; email: string; phone_e164?: string },
): Promise<PlayerInviteCreated> {
  const response = await apiFetch(`/api/v1/teams/${teamId}/players`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as PlayerInviteCreated;
}
