import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { QuestionStat } from "../api/dashboard";
import type { Question } from "../api/questionnaires";

const ACCENT = "#1f6b45";
const ACCENT_SOFT = "#8fb9a1";
const INK_MUTED = "#4a5c52";
const REMAINING = "#c5d0c9";
const CHOICE_PALETTE = ["#1f6b45", "#2d8a5c", "#5aa882", "#8fb9a1", "#b7d0c2"];

function optionLabel(question: Question | undefined, optionId: string): string {
  return question?.options?.find((o) => o.id === optionId)?.label ?? optionId;
}

type CompletionChartProps = {
  completed: number;
  rosterSize: number;
};

export function CompletionChart({ completed, rosterSize }: CompletionChartProps) {
  const remaining = Math.max(rosterSize - completed, 0);
  const data = [
    { name: "Completed", value: completed },
    { name: "Outstanding", value: remaining },
  ];
  const empty = rosterSize === 0;

  return (
    <div className="chart-card">
      <h3 className="chart-card__title">Completion</h3>
      {empty ? (
        <p className="muted">No players on roster.</p>
      ) : (
        <>
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
                  <Cell fill={ACCENT} />
                  <Cell fill={REMAINING} />
                </Pie>
                <Tooltip
                  formatter={(value) => [Number(value), ""]}
                  contentStyle={{ borderRadius: 8, borderColor: "rgba(20,32,26,0.12)" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-card__caption">
            {completed} of {rosterSize} submitted
          </p>
        </>
      )}
    </div>
  );
}

type QuestionStatChartProps = {
  stat: QuestionStat;
  responseCount: number;
  question?: Question;
};

export function QuestionStatChart({
  stat,
  responseCount,
  question,
}: QuestionStatChartProps) {
  if (stat.question_type === "rating") {
    const average = stat.average ?? 0;
    const data = [{ name: "Average", value: average }];
    return (
      <div className="chart-card">
        <h3 className="chart-card__title">{stat.prompt}</h3>
        <p className="chart-card__caption muted">Rating average</p>
        {stat.average == null ? (
          <p className="muted">No responses yet.</p>
        ) : (
          <div className="chart-card__body">
            <ResponsiveContainer width="100%" height={140}>
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 5]} ticks={[1, 2, 3, 4, 5]} />
                <YAxis type="category" dataKey="name" width={64} tick={{ fill: INK_MUTED }} />
                <Tooltip
                  formatter={(value) => [Number(value).toFixed(2), "Average"]}
                  contentStyle={{ borderRadius: 8, borderColor: "rgba(20,32,26,0.12)" }}
                />
                <Bar dataKey="value" fill={ACCENT} radius={[0, 6, 6, 0]} barSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    );
  }

  if (stat.question_type === "yes_no") {
    const yes = stat.yes_count ?? 0;
    const no = Math.max(responseCount - yes, 0);
    const data = [
      { name: "Yes", value: yes },
      { name: "No", value: no },
    ];
    return (
      <div className="chart-card">
        <h3 className="chart-card__title">{stat.prompt}</h3>
        <p className="chart-card__caption muted">Yes / no</p>
        {responseCount === 0 ? (
          <p className="muted">No responses yet.</p>
        ) : (
          <div className="chart-card__body">
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: INK_MUTED }} />
                <YAxis allowDecimals={false} width={28} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, borderColor: "rgba(20,32,26,0.12)" }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={40}>
                  <Cell fill={ACCENT} />
                  <Cell fill={ACCENT_SOFT} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    );
  }

  if (stat.question_type === "single_choice" && stat.option_counts) {
    const data = Object.entries(stat.option_counts).map(([optionId, value]) => ({
      name: optionLabel(question, optionId),
      value,
    }));
    const hasData = data.some((row) => row.value > 0);
    const labelWidth = Math.min(
      140,
      Math.max(72, ...data.map((row) => row.name.length * 7)),
    );
    return (
      <div className="chart-card">
        <h3 className="chart-card__title">{stat.prompt}</h3>
        <p className="chart-card__caption muted">Choice counts</p>
        {!hasData ? (
          <p className="muted">No responses yet.</p>
        ) : (
          <div className="chart-card__body">
            <ResponsiveContainer width="100%" height={Math.max(140, data.length * 36)}>
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={labelWidth}
                  tick={{ fill: INK_MUTED, fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 8, borderColor: "rgba(20,32,26,0.12)" }}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={22}>
                  {data.map((row, index) => (
                    <Cell
                      key={row.name}
                      fill={CHOICE_PALETTE[index % CHOICE_PALETTE.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    );
  }

  return null;
}
