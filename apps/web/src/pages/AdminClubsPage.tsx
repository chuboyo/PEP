import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useCreateOrganizationMutation } from "../queries/organizations";

export function AdminClubsPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isSuperadmin = me?.platform_role === "SUPERADMIN";
  const createMutation = useCreateOrganizationMutation();

  const [name, setName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isSuperadmin) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isSuperadmin, navigate]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setInviteLink(null);
    setCopied(false);
    createMutation.mutate(
      { name, admin_name: adminName, admin_email: adminEmail },
      {
        onSuccess: (result) => {
          setInviteLink(result.invite_link);
          setName("");
          setAdminName("");
          setAdminEmail("");
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

  if (!hasToken || mePending || !isSuperadmin) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const errorMessage =
    createMutation.error instanceof Error
      ? createMutation.error.message
      : createMutation.isError
        ? "Could not create club"
        : null;

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Create club</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/admin/clubs">
              All clubs
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            <span>Club name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Admin name</span>
            <input
              value={adminName}
              onChange={(e) => setAdminName(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Admin email</span>
            <input
              type="email"
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
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
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? "Creating…" : "Create club"}
          </button>
        </form>

        {inviteLink ? (
          <div className="invite-box">
            <p className="label">Club admin invite link</p>
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
