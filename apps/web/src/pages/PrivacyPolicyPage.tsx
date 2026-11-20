import { Link } from "react-router-dom";

export function PrivacyPolicyPage() {
  return (
    <main className="shell">
      <article className="panel panel--wide legal">
        <p className="legal__brand">
          <Link to="/login">Pep</Link>
        </p>
        <h1>Privacy Policy</h1>
        <p className="muted legal__updated">Last updated: 20 November 2026</p>

        <p>
          Pep (“Pep”, “we”, “us”) is a club wellbeing and training check-in
          product. Clubs use Pep so coaches can invite players, send short
          questionnaires (in the app or via WhatsApp), review aggregated
          answers, and assign training routines. This policy explains what
          personal data Pep processes and why.
        </p>

        <h2>Who this applies to</h2>
        <p>
          This policy applies to club administrators, coaches, players, and
          platform operators who use Pep’s website or WhatsApp-connected
          surveys.
        </p>

        <h2>Data we collect</h2>
        <ul>
          <li>
            <strong>Account details:</strong> name, email address, and a
            hashed password (we do not store passwords in plain text).
          </li>
          <li>
            <strong>Phone number:</strong> if a player is set up for WhatsApp
            surveys, we store their number in E.164 format so we can match
            inbound WhatsApp messages to their account.
          </li>
          <li>
            <strong>Club and team context:</strong> organisation membership,
            role (for example club admin, coach, or player), and team
            membership.
          </li>
          <li>
            <strong>Questionnaire answers:</strong> responses players submit
            in the app or through WhatsApp interactive messages. Submitted
            answers are treated as permanent records for coaching and
            wellbeing follow-up within the club.
          </li>
          <li>
            <strong>Training routines:</strong> routines assigned by coaches
            and completion status marked by players.
          </li>
          <li>
            <strong>Technical data:</strong> authentication tokens, basic
            server logs needed to operate and secure the service, and
            WhatsApp delivery metadata (such as provider message identifiers)
            when WhatsApp is enabled.
          </li>
        </ul>

        <h2>How we use data</h2>
        <ul>
          <li>To create and manage club accounts and invitations.</li>
          <li>
            To deliver questionnaires and reminders in the app or via WhatsApp.
          </li>
          <li>
            To show coaches and club staff completion status, averages, and
            related dashboards for their organisation only.
          </li>
          <li>To assign and track training routines.</li>
          <li>To keep the service secure and working (authentication, abuse prevention, debugging).</li>
        </ul>

        <h2>WhatsApp</h2>
        <p>
          When a club uses WhatsApp surveys, Pep sends templates and interactive
          messages through Meta’s WhatsApp Business Platform and receives player
          button/list replies on our webhook. Meta processes message content
          according to Meta’s own terms and policies. Players should only be
          contacted on numbers their club has registered for this purpose.
          Typed free-text WhatsApp messages are not treated as survey answers
          in Pep.
        </p>

        <h2>Who can see your data</h2>
        <ul>
          <li>
            Data is scoped by organisation. Coaches and club admins see player
            information and responses for their club (and teams they manage),
            not for other clubs.
          </li>
          <li>
            Platform operators (superadmins) may access organisation-level
            administration features needed to run Pep.
          </li>
          <li>
            We use infrastructure providers (for example hosting and database
            services) to run Pep. They process data only to provide those
            services.
          </li>
          <li>
            We do not sell personal data. We do not use survey answers for
            advertising.
          </li>
        </ul>

        <h2>Legal basis (where GDPR applies)</h2>
        <p>
          Where the UK/EU GDPR applies, we typically rely on{" "}
          <strong>legitimate interests</strong> or{" "}
          <strong>contract / club instructions</strong> to operate invited
          accounts and coaching workflows, and on the club’s relationship with
          players for wellbeing check-ins. Clubs that invite players are
          responsible for ensuring they have an appropriate basis to collect
          phone numbers and questionnaire answers from their athletes.
        </p>

        <h2>Retention</h2>
        <p>
          We keep account, membership, questionnaire, and routine records while
          the club uses Pep and as needed for the coaching history the product
          provides. If a player is deactivated, access credentials and phone
          binding may be cleared so the account cannot be reused without a new
          invite; historical response records may remain for the club’s
          records. You can ask your club admin or Pep operator about deletion
          requests for your organisation.
        </p>

        <h2>Security</h2>
        <p>
          Access to Pep requires authentication. Passwords are hashed. API
          access uses short-lived tokens. WhatsApp webhook traffic is verified
          with Meta’s signature when WhatsApp is configured. No method of
          transmission or storage is completely secure; we take reasonable
          measures appropriate to this product.
        </p>

        <h2>Children</h2>
        <p>
          Pep is aimed at sports clubs and their staff. Clubs must only invite
          players in line with applicable youth and safeguarding rules. If you
          believe we hold data about a child without appropriate authority,
          contact us using the details below.
        </p>

        <h2>Your choices</h2>
        <ul>
          <li>Request access or correction via your club administrator.</li>
          <li>
            Stop WhatsApp messages by asking your club to remove your phone
            number or deactivate WhatsApp assignments; you may also use
            WhatsApp’s own blocking controls.
          </li>
          <li>
            Depending on your location, you may have rights to access, rectify,
            erase, restrict, or object to certain processing, or to lodge a
            complaint with a supervisory authority.
          </li>
        </ul>

        <h2>Contact</h2>
        <p>
          For privacy questions about Pep, contact the club administrator who
          invited you, or the Pep operator for your deployment (the person or
          organisation running this Pep instance).
        </p>

        <h2>Changes</h2>
        <p>
          We may update this policy as Pep evolves. The “Last updated” date at
          the top will change when we do. Continued use of Pep after an update
          means you should review the revised policy.
        </p>

        <p className="legal__footer">
          <Link to="/login">Back to sign in</Link>
        </p>
      </article>
    </main>
  );
}
