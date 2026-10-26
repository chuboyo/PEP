import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/auth";
import { clearTokens, getAccessToken } from "../auth";
import { clearMeQuery, useLogoutMutation, useMeQuery } from "../queries/auth";

export function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const hasToken = !!getAccessToken();
  const { data: me, isPending, isError, error } = useMeQuery();
  const logoutMutation = useLogoutMutation();

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
    }
  }, [hasToken, navigate]);

  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) {
      clearTokens();
      clearMeQuery(queryClient);
      navigate("/login");
    }
  }, [error, navigate, queryClient]);

  const membershipRole = me?.memberships[0]?.role;
  const isSuperadmin = me?.platform_role === "SUPERADMIN";
  const isClubAdmin = me?.memberships.some(
    (m) => m.role === "CLUB_ADMIN" && m.status === "active",
  );
  const showError =
    isError && !(error instanceof ApiError && error.status === 401);

  if (!hasToken) {
    return null;
  }

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Pep</h1>
          {me ? (
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
            >
              Log out
            </button>
          ) : null}
        </header>

        {showError ? (
          <p className="alert" role="alert">
            {error instanceof Error ? error.message : "Failed to load profile"}
          </p>
        ) : null}

        {me ? (
          <>
            <ul className="meta-list">
              <li>
                <span className="label">Name</span>
                <span className="value">{me.name}</span>
              </li>
              <li>
                <span className="label">Platform role</span>
                <span className="value">{me.platform_role ?? "none"}</span>
              </li>
              {membershipRole ? (
                <li>
                  <span className="label">Membership role</span>
                  <span className="value">{membershipRole}</span>
                </li>
              ) : null}
            </ul>
            <nav className="nav-links">
              {isSuperadmin ? (
                <>
                  <Link className="btn btn--primary" to="/admin/clubs">
                    All clubs
                  </Link>
                  <Link className="btn btn--ghost" to="/admin/clubs/new">
                    Create club
                  </Link>
                </>
              ) : null}
              {isClubAdmin ? (
                <Link className="btn btn--primary" to="/club/coaches">
                  Register coaches
                </Link>
              ) : null}
            </nav>
          </>
        ) : isPending ? (
          <p className="muted">Loading…</p>
        ) : null}
      </div>
    </main>
  );
}
