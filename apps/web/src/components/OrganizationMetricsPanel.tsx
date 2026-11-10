import type { OrganizationMetrics } from "../api/organizations";

type Props = {
  metrics: OrganizationMetrics;
};

export function OrganizationMetricsPanel({ metrics }: Props) {
  return (
    <ul className="meta-list">
      <li>
        <span className="label">Coaches</span>
        <span className="value">{metrics.coach_count}</span>
      </li>
      <li>
        <span className="label">Players</span>
        <span className="value">{metrics.player_count}</span>
      </li>
      <li>
        <span className="label">Active players</span>
        <span className="value">{metrics.active_player_count}</span>
      </li>
      <li>
        <span className="label">Questionnaire completion</span>
        <span className="value">
          {metrics.questionnaire_completed_count} /{" "}
          {metrics.questionnaire_occurrence_count}
        </span>
      </li>
      <li>
        <span className="label">Routines assigned</span>
        <span className="value">{metrics.routine_counts.assigned}</span>
      </li>
      <li>
        <span className="label">Routines in progress</span>
        <span className="value">{metrics.routine_counts.in_progress}</span>
      </li>
      <li>
        <span className="label">Routines completed</span>
        <span className="value">{metrics.routine_counts.completed}</span>
      </li>
    </ul>
  );
}
