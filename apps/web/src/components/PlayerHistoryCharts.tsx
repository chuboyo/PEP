import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PlayerHistoryItem, RatingTrend } from "../api/player";
import type { Question } from "../api/questionnaires";

const ACCENT = "#1f6b45";
const INK_MUTED = "#4a5c52";

type RatingTrendChartsProps = {
  trends: RatingTrend[];
};

export function PlayerRatingTrendCharts({ trends }: RatingTrendChartsProps) {
  if (trends.length === 0) {
    return null;
  }

  return (
    <>
      <h2 className="section-title">Rating trends</h2>
      <div className="chart-grid">
        {trends.map((trend) => {
          const data = trend.values.map((value, index) => ({
            label: String(index + 1),
            value,
          }));
          return (
            <div className="chart-card" key={trend.question_id}>
              <h3 className="chart-card__title">{trend.prompt}</h3>
              <p className="chart-card__caption muted">Last {data.length}</p>
              <div className="chart-card__body">
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart
                    data={data}
                    margin={{ top: 8, right: 12, left: 0, bottom: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: INK_MUTED, fontSize: 11 }}
                    />
                    <YAxis domain={[1, 5]} ticks={[1, 2, 3, 4, 5]} width={28} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 8,
                        borderColor: "rgba(20,32,26,0.12)",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke={ACCENT}
                      strokeWidth={2}
                      dot={{ r: 4, fill: ACCENT }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function formatAnswer(question: Question, value: unknown): string {
  if (question.type === "yes_no" && typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (question.type === "rating" && typeof value === "number") {
    return `${value} / 5`;
  }
  if (question.type === "single_choice" && typeof value === "string") {
    return (
      question.options?.find((o) => o.id === value)?.label ?? value
    );
  }
  if (typeof value === "string") {
    return value || "—";
  }
  return String(value);
}

type SubmissionListProps = {
  submissions: PlayerHistoryItem[];
  limit?: number;
};

export function PlayerSubmissionList({
  submissions,
  limit,
}: SubmissionListProps) {
  const rows = limit == null ? submissions : submissions.slice(0, limit);
  if (rows.length === 0) {
    return <p className="muted">No submissions yet.</p>;
  }

  return (
    <div className="occurrence-stack">
      {rows.map((submission) => (
        <article className="occurrence-card" key={submission.occurrence_id}>
          <header className="occurrence-card__header">
            <h3 className="chart-card__title">
              {submission.questionnaire_name}
            </h3>
            <span className="occurrence-card__status">
              {submission.status}
            </span>
          </header>
          <p className="chart-card__caption">
            Submitted {new Date(submission.submitted_at).toLocaleString()}
            {submission.channel ? ` · ${submission.channel}` : null}
          </p>
          <ul className="meta-list">
            {submission.questions_snapshot.map((question) => {
              const value = submission.answers[question.id];
              if (value === undefined) {
                return null;
              }
              return (
                <li key={question.id}>
                  <span className="label">{question.prompt}</span>
                  <span className="value">
                    {formatAnswer(question, value)}
                  </span>
                </li>
              );
            })}
          </ul>
        </article>
      ))}
    </div>
  );
}
