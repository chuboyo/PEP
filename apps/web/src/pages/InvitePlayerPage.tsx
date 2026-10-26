import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useInvitePlayerMutation, useTeamQuery } from "../queries/teams";

export function InvitePlayerPage() {
  const { teamId = "" } = useParams();
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isCoach = me?.memberships.some(
    (m) => m.role === "COACH" && m.status === "active",
  );
  const teamQuery = useTeamQuery(teamId, !!isCoach && !!teamId);
  const inviteMutation = useInvitePlayerMutation(teamId);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isCoach) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isCoach, navigate]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setInviteLink(null);
    setCopied(false);
    inviteMutation.mutate(
      {
        name,
        email,
        phone_e164: phone.trim() ? phone.trim() : undefined,
      },
      {
        onSuccess: (result) => {
          setInviteLink(result.invite_link);
          setName("");
          setEmail("");
          setPhone("");
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

  if (!hasToken || mePending || !isCoach) {
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
        ? "Could not invite player"
        : null;

  const teamName = teamQuery.data?.name;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Register player</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to={`/teams/${teamId}`}>
              {teamName ?? "Team"}
            </Link>
            <Link className="btn btn--ghost" to="/teams">
              All teams
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

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
          <label className="field">
            <span>Phone (E.164, optional)</span>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+15551234567"
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
            {inviteMutation.isPending ? "Inviting…" : "Invite player"}
          </button>
        </form>

        {inviteLink ? (
          <div className="invite-box">
            <p className="label">Player invite link</p>
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
