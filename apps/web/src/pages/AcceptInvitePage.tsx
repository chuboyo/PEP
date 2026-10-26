import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAcceptInviteMutation } from "../queries/auth";

export function AcceptInvitePage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const acceptMutation = useAcceptInviteMutation();

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      return;
    }
    acceptMutation.mutate({ token, password });
  }

  const errorMessage =
    acceptMutation.error instanceof Error
      ? acceptMutation.error.message
      : acceptMutation.isError
        ? "Could not accept invite"
        : null;

  if (!token) {
    return (
      <main className="shell shell--center">
        <div className="panel">
          <h1 className="brand">Pep</h1>
          <p className="alert" role="alert">
            Missing invite token. Open the full invite link you were given.
          </p>
          <p className="muted">
            <Link to="/login">Sign in</Link>
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="shell shell--center">
      <div className="panel">
        <h1 className="brand">Pep</h1>
        <p className="lede">Set your password to join</p>
        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            <span>Password (min 8 characters)</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
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
            disabled={acceptMutation.isPending}
          >
            {acceptMutation.isPending ? "Saving…" : "Accept invite"}
          </button>
        </form>
      </div>
    </main>
  );
}
