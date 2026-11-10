import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { OrganizationMetricsPanel } from "../components/OrganizationMetricsPanel";
import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useOrganizationMetricsQuery } from "../queries/organizations";

export function AdminClubMetricsPage() {
  const { organizationId = "" } = useParams();
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const isSuperadmin = me?.platform_role === "SUPERADMIN";
  const metricsQuery = useOrganizationMetricsQuery(
    organizationId,
    !!isSuperadmin && !!organizationId,
  );

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
          <h1 className="brand">Club metrics</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/admin/clubs">
              All clubs
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <p className="lede">Aggregate counts only — no player drill-down</p>

        {metricsQuery.isPending ? (
          <p className="muted">Loading metrics…</p>
        ) : metricsQuery.isError ? (
          <p className="alert" role="alert">
            Could not load metrics
          </p>
        ) : metricsQuery.data ? (
          <OrganizationMetricsPanel metrics={metricsQuery.data} />
        ) : null}
      </div>
    </main>
  );
}
