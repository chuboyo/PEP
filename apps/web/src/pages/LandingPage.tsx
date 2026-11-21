import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getAccessToken } from "../auth";

export function LandingPage() {
  const navigate = useNavigate();
  const hasToken = !!getAccessToken();

  useEffect(() => {
    if (hasToken) {
      navigate("/home", { replace: true });
    }
  }, [hasToken, navigate]);

  if (hasToken) {
    return null;
  }

  return (
    <main className="landing">
      <div className="landing__glow" aria-hidden="true" />
      <div className="landing__field" aria-hidden="true" />

      <header className="landing__top">
        <p className="landing__mark">Pep</p>
        <Link className="btn btn--ghost landing__top-link" to="/login">
          Sign in
        </Link>
      </header>

      <section className="landing__hero">
        <p className="landing__brand">Pep</p>
        <h1 className="landing__headline">
          Check-ins that keep the squad sharp
        </h1>
        <p className="landing__lede">
          Coaches send short wellbeing surveys in the app or on WhatsApp.
          Players answer in taps. Clubs see what matters.
        </p>
        <div className="landing__actions">
          <Link className="btn btn--primary landing__cta" to="/login">
            Sign in
          </Link>
          <Link className="landing__quiet" to="/privacy">
            Privacy
          </Link>
        </div>
      </section>

      <footer className="landing__foot">
        <span>For clubs · Invite only</span>
      </footer>
    </main>
  );
}
