import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useOrganizationsQuery } from "../queries/organizations";

export function AdminClubsListPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isSuperadmin = me?.platform_role === "SUPERADMIN";
  const clubsQuery = useOrganizationsQuery(!!isSuperadmin);

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !isSuperadmin) {
      navigate("/");
    }
  }, [hasToken, me, mePending, isSuperadmin, navigate]);

  if (!hasToken || mePending || !isSuperadmin) {
    return (
      <main className="shell shell--center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  return (
    <main className="shell shell--center">
      <div className="panel panel--wide">
        <header className="topbar">
          <h1 className="brand">Clubs</h1>
          <div className="nav-links">
            <Link className="btn btn--primary" to="/admin/clubs/new">
              Create club
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        {clubsQuery.isPending ? (
          <p className="muted">Loading…</p>
        ) : clubsQuery.isError ? (
          <p className="alert" role="alert">
            Could not load clubs
          </p>
        ) : (clubsQuery.data?.length ?? 0) === 0 ? (
          <p className="muted">No clubs yet.</p>
        ) : (
          <ul className="meta-list">
            {clubsQuery.data?.map((club) => (
              <li key={club.id}>
                <span className="label">{club.status}</span>
                <span className="value">{club.name}</span>
                <span className="muted">{club.admin_email ?? "No admin"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
