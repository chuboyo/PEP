import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PlayerOccurrenceHistory } from "../api/dashboard";
import type { Question } from "../api/questionnaires";

const ACCENT = "#1f6b45";
const ACCENT_SOFT = "#8fb9a1";
const INK_MUTED = "#4a5c52";
const STATUS_COLORS: Record<string, string> = {
  completed: "#1f6b45",
  pending: "#c5d0c9",
  in_progress: "#5aa882",
  missed: "#9b2c2c",
};
const CHOICE_PALETTE = ["#1f6b45", "#2d8a5c", "#5aa882", "#8fb9a1", "#b7d0c2"];

type StatusOverviewProps = {
  occurrences: PlayerOccurrenceHistory[];
};

export function StatusOverviewChart({ occurrences }: StatusOverviewProps) {
  const counts = new Map<string, number>();
  for (const occurrence of occurrences) {
    counts.set(occurrence.status, (counts.get(occurrence.status) ?? 0) + 1);
  }
  const data = [...counts.entries()].map(([name, value]) => ({ name, value }));

  return (
    <div className="chart-card">
      <h3 className="chart-card__title">Status mix</h3>
      <div className="chart-card__body chart-card__body--donut">
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={48}
              outerRadius={72}
              paddingAngle={2}
              stroke="none"
            >
              {data.map((row) => (
                <Cell
                  key={row.name}
                  fill={STATUS_COLORS[row.name] ?? ACCENT_SOFT}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ borderRadius: 8, borderColor: "rgba(20,32,26,0.12)" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-card__caption">
        {occurrences.length} occurrence{occurrences.length === 1 ? "" : "s"}
      </p>
    </div>
  );
}

type RatingTrendProps = {
  occurrences: PlayerOccurrenceHistory[];
};

type RatingSeries = {
  questionId: string;
  prompt: string;
  points: { label: string; value: number }[];
};

function buildRatingSeries(
  occurrences: PlayerOccurrenceHistory[],
): RatingSeries[] {
  const completed = occurrences
    .filter((o) => o.status === "completed" && o.answers && o.submitted_at)
    .slice()
    .sort(
      (a, b) =>
        new Date(a.submitted_at!).getTime() -
        new Date(b.submitted_at!).getTime(),
    );

  const byQuestion = new Map<string, RatingSeries>();
  for (const occurrence of completed) {
    const questions = occurrence.questions_snapshot ?? [];
    const label = new Date(occurrence.submitted_at!).toLocaleDateString(
      undefined,
      { month: "short", day: "numeric" },
    );
    for (const question of questions) {
      if (question.type !== "rating") {
        continue;
      }
      const raw = occurrence.answers?.[question.id];
      if (typeof raw !== "number") {
        continue;
      }
      let series = byQuestion.get(question.id);
      if (!series) {
        series = {
          questionId: question.id,
          prompt: question.prompt,
          points: [],
        };
        byQuestion.set(question.id, series);
      }
      series.points.push({ label, value: raw });
    }
  }
  return [...byQuestion.values()].filter((s) => s.points.length > 0);
}

export function RatingTrendCharts({ occurrences }: RatingTrendProps) {
  const series = buildRatingSeries(occurrences);
  if (series.length === 0) {
    return null;
  }

  return (
    <>
      <h2 className="section-title">Rating trends</h2>
      <div className="chart-grid">
        {series.map((item) => (
          <div className="chart-card" key={item.questionId}>
            <h3 className="chart-card__title">{item.prompt}</h3>
            <div className="chart-card__body">
              <ResponsiveContainer width="100%" height={160}>
                <LineChart
                  data={item.points}
                  margin={{ top: 8, right: 12, left: 0, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fill: INK_MUTED, fontSize: 11 }} />
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
        ))}
      </div>
    </>
  );
}

function optionLabel(question: Question, optionId: string): string {
  return question.options?.find((o) => o.id === optionId)?.label ?? optionId;
}

type OccurrenceAnswersChartProps = {
  occurrence: PlayerOccurrenceHistory;
};

export function OccurrenceAnswersChart({
  occurrence,
}: OccurrenceAnswersChartProps) {
  const answers = occurrence.answers;
  if (!answers) {
    return <p className="muted">No answers yet.</p>;
  }

  const questions = occurrence.questions_snapshot ?? [];
  const charts = questions
    .map((question) => {
      const value = answers[question.id];
      if (value === undefined) {
        return null;
      }

      if (question.type === "rating" && typeof value === "number") {
        return (
          <div className="chart-card chart-card--compact" key={question.id}>
            <h3 className="chart-card__title">{question.prompt}</h3>
            <div className="chart-card__body">
              <ResponsiveContainer width="100%" height={100}>
                <BarChart
                  data={[{ name: "Score", value }]}
                  layout="vertical"
                  margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
                >
                  <XAxis type="number" domain={[0, 5]} hide />
                  <YAxis type="category" dataKey="name" hide />
                  <Tooltip
                    formatter={(v) => [Number(v), "Rating"]}
                    contentStyle={{
                      borderRadius: 8,
                      borderColor: "rgba(20,32,26,0.12)",
                    }}
                  />
                  <Bar
                    dataKey="value"
                    fill={ACCENT}
                    radius={[0, 6, 6, 0]}
                    barSize={22}
                    background={{ fill: "#e2ebe4" }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-card__caption">{value} / 5</p>
          </div>
        );
      }

      if (question.type === "yes_no" && typeof value === "boolean") {
        const data = [
          { name: "Yes", value: value ? 1 : 0 },
          { name: "No", value: value ? 0 : 1 },
        ];
        return (
          <div className="chart-card chart-card--compact" key={question.id}>
            <h3 className="chart-card__title">{question.prompt}</h3>
            <div className="chart-card__body">
              <ResponsiveContainer width="100%" height={110}>
                <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                  <XAxis dataKey="name" tick={{ fill: INK_MUTED, fontSize: 11 }} />
                  <YAxis hide domain={[0, 1]} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={28}>
                    <Cell fill={value ? ACCENT : ACCENT_SOFT} />
                    <Cell fill={!value ? ACCENT : ACCENT_SOFT} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-card__caption">{value ? "Yes" : "No"}</p>
          </div>
        );
      }

      if (question.type === "single_choice" && typeof value === "string") {
        const options = question.options ?? [];
        const data = options.map((opt) => ({
          name: opt.label,
          value: opt.id === value ? 1 : 0,
        }));
        return (
          <div className="chart-card chart-card--compact" key={question.id}>
            <h3 className="chart-card__title">{question.prompt}</h3>
            <div className="chart-card__body">
              <ResponsiveContainer
                width="100%"
                height={Math.max(100, options.length * 28)}
              >
                <BarChart
                  data={data}
                  layout="vertical"
                  margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
                >
                  <XAxis type="number" hide domain={[0, 1]} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={80}
                    tick={{ fill: INK_MUTED, fontSize: 11 }}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16}>
                    {data.map((row, index) => (
                      <Cell
                        key={row.name}
                        fill={
                          row.value
                            ? CHOICE_PALETTE[index % CHOICE_PALETTE.length]
                            : "#e2ebe4"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-card__caption">
              {optionLabel(question, value)}
            </p>
          </div>
        );
      }

      if (question.type === "short_text" && typeof value === "string") {
        return (
          <div className="chart-card chart-card--compact" key={question.id}>
            <h3 className="chart-card__title">{question.prompt}</h3>
            <p className="chart-card__caption">{value || "—"}</p>
          </div>
        );
      }

      return null;
    })
    .filter(Boolean);

  if (charts.length === 0) {
    return <p className="muted">No chartable answers.</p>;
  }

  return <div className="chart-grid">{charts}</div>;
}
