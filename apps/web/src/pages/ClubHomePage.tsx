import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { OrganizationMetricsPanel } from "../components/OrganizationMetricsPanel";
import { getAccessToken } from "../auth";
import { useMeQuery } from "../queries/auth";
import { useOrganizationMetricsQuery } from "../queries/organizations";

export function ClubHomePage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();
  const { data: me, isPending: mePending } = useMeQuery();
  const clubAdminMembership = me?.memberships.find(
    (m) => m.role === "CLUB_ADMIN" && m.status === "active",
  );
  const organizationId = clubAdminMembership?.organization_id ?? "";
  const metricsQuery = useOrganizationMetricsQuery(
    organizationId,
    !!clubAdminMembership,
  );

  useEffect(() => {
    if (!hasToken) {
      navigate("/login");
      return;
    }
    if (!mePending && me && !clubAdminMembership) {
      navigate("/");
    }
  }, [hasToken, me, mePending, clubAdminMembership, navigate]);

  if (!hasToken || mePending || !clubAdminMembership) {
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
          <h1 className="brand">Club</h1>
          <div className="nav-links">
            <Link className="btn btn--ghost" to="/club/coaches">
              Coaches
            </Link>
            <Link className="btn btn--ghost" to="/">
              Home
            </Link>
          </div>
        </header>

        <p className="lede">Club aggregates — no player answer drill-down</p>

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
