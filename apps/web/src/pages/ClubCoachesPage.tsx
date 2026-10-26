import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useInviteCoachMutation } from "../queries/organizations";

export function ClubCoachesPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const clubAdminMembership = me?.memberships.find(
    (m) => m.role === "CLUB_ADMIN" && m.status === "active",
  );
  const organizationId = clubAdminMembership?.organization_id ?? "";
  const inviteMutation = useInviteCoachMutation(organizationId);

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
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Coaches</h1>
          <Link className="btn btn--ghost" to="/">
            Home
          </Link>
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
      </div>
    </main>
  );
}
