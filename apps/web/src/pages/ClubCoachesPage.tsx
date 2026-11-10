import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import {
  useDeactivateCoachMutation,
  useInviteCoachMutation,
  useOrganizationCoachesQuery,
} from "../queries/organizations";

export function ClubCoachesPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const clubAdminMembership = me?.memberships.find(
    (m) => m.role === "CLUB_ADMIN" && m.status === "active",
  );
  const organizationId = clubAdminMembership?.organization_id ?? "";
  const inviteMutation = useInviteCoachMutation(organizationId);
  const deactivateMutation = useDeactivateCoachMutation(organizationId);
  const coachesQuery = useOrganizationCoachesQuery(
    organizationId,
    !!clubAdminMembership,
  );

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !clubAdminMembership) {
      navigate("/");
    }
  }, [hasToken, me, mePending, clubAdminMembership, navigate]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!organizationId) {
      return;
    }
    setInviteLink(null);
    setCopied(false);
    inviteMutation.mutate(
      { name, email },
      {
        onSuccess: (result) => {
          setInviteLink(result.invite_link);
          setName("");
          setEmail("");
        },
      },
    );
  }

  async function copyLink() {
    if (!inviteLink) {
      return;
    }
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
  }

  if (!hasToken || mePending || !clubAdminMembership) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const errorMessage =
    inviteMutation.error instanceof Error
      ? inviteMutation.error.message
      : inviteMutation.isError
        ? "Could not invite coach"
        : deactivateMutation.error instanceof Error
          ? deactivateMutation.error.message
          : deactivateMutation.isError
            ? "Could not deactivate coach"
            : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Coaches</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/club">
              Club home
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <p className="lede">Register a coach for your club</p>
        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            <span>Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          {errorMessage ? (
            <p className="alert" role="alert">
              {errorMessage}
            </p>
          ) : null}
          <button
            className="btn btn--primary"
            type="submit"
            disabled={inviteMutation.isPending}
          >
            {inviteMutation.isPending ? "Inviting…" : "Invite coach"}
          </button>
        </form>

        {inviteLink ? (
          <div className="invite-box">
            <p className="label">Coach invite link</p>
            <p className="invite-link">{inviteLink}</p>
            <button className="btn btn--ghost" type="button" onClick={copyLink}>
              {copied ? "Copied" : "Copy link"}
            </button>
          </div>
        ) : null}

        <h2 className="section-title">Active coaches</h2>
        {coachesQuery.isPending ? (
          <p className="muted">Loading coaches…</p>
        ) : coachesQuery.isError ? (
          <p className="alert" role="alert">
            Could not load coaches
          </p>
        ) : (coachesQuery.data?.length ?? 0) === 0 ? (
          <p className="muted">No coaches yet.</p>
        ) : (
          <ul className="meta-list">
            {coachesQuery.data?.map((coach) => (
              <li key={coach.user_id}>
                <span className="label">{coach.status}</span>
                <span className="value">{coach.name}</span>
                <span className="muted">{coach.email}</span>
                <button
                  className="btn btn--ghost"
                  type="button"
                  disabled={
                    deactivateMutation.isPending &&
                    deactivateMutation.variables === coach.user_id
                  }
                  onClick={() => deactivateMutation.mutate(coach.user_id)}
                >
                  Deactivate
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
