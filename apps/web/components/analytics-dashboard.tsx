"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type DistributionItem = {
  name: string;
  count: number;
};

type SourceAnalyticsItem = {
  source_type: string;
  count: number;
};

type FeedbackTrendItem = {
  date: string;
  count: number;
};

type RecentFeedbackItem = {
  feedback_id: string;
  source_type: string;
  raw_text: string;
  sentiment: string;
  category: string;
  severity: string;
  source_created_at: string | null;
};

export type ProjectAnalytics = {
  project_id: string;
  relevant_feedback: number;
  sentiment_distribution: DistributionItem[];
  category_distribution: DistributionItem[];
  source_breakdown: SourceAnalyticsItem[];
  feedback_trend: FeedbackTrendItem[];
  recent_feedback: RecentFeedbackItem[];
};

type AnalyticsDashboardProps = {
  analytics: ProjectAnalytics;
};

function formatLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Date unavailable";
  }

  const date = new Date(value);

  const day = date.getDate();
  const month = date.toLocaleString("en-US", {
    month: "short",
  });

  const hours = date.getHours();
  const minutes = date.getMinutes();

  const hour12 = hours % 12 || 12;
  const period = hours >= 12 ? "PM" : "AM";

  return `${day} ${month} · ${hour12}:${minutes
    .toString()
    .padStart(2, "0")} ${period}`;
}

export default function AnalyticsDashboard({
  analytics,
}: AnalyticsDashboardProps) {
  const categoryData = analytics.category_distribution.map((item) => ({
    ...item,
    label: formatLabel(item.name),
  }));

  const sourceData = analytics.source_breakdown.map((item) => ({
    name: formatLabel(item.source_type),
    count: item.count,
  }));

  const trendData = analytics.feedback_trend.map((item) => ({
    ...item,
    label: formatDate(item.date),
  }));

  return (
    <section className="mt-10">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-zinc-900">
          Feedback analytics
        </h2>

        <p className="mt-1 text-sm text-zinc-500">
          Patterns across relevant customer feedback
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard
          title="Sentiment"
          description="How relevant feedback is distributed by sentiment"
        >
          <div className="space-y-4">
            {analytics.sentiment_distribution.map((item) => {
              const percentage =
                analytics.relevant_feedback > 0
                  ? Math.round(
                      (item.count / analytics.relevant_feedback) * 100,
                    )
                  : 0;

              return (
                <div key={item.name}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="text-zinc-600">
                      {formatLabel(item.name)}
                    </span>

                    <span className="font-medium text-zinc-900">
                      {item.count.toLocaleString()} ({percentage}%)
                    </span>
                  </div>

                  <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
                    <div
                      className="h-full rounded-full bg-zinc-900"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>

        <ChartCard
          title="Feedback sources"
          description="Relevant feedback by connected channel"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sourceData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                />

                <XAxis
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />

                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />

                <Tooltip />

                <Bar
                  dataKey="count"
                  fill="currentColor"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Top feedback categories"
          description="Where relevant customer feedback is concentrated"
        >
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={categoryData.slice(0, 8)}
                layout="vertical"
                margin={{ left: 20 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  horizontal={false}
                />

                <XAxis
                  type="number"
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />

                <YAxis
                  type="category"
                  dataKey="label"
                  width={120}
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                />

                <Tooltip />

                <Bar
                  dataKey="count"
                  fill="currentColor"
                  radius={[0, 6, 6, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Feedback trend"
          description="Relevant feedback occurrence over the last 30 days"
        >
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                />

                <XAxis
                  dataKey="label"
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                />

                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />

                <Tooltip />

                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="currentColor"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      <div className="mt-8">
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-zinc-900">
            Recent feedback
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Latest relevant customer feedback across connected sources
          </p>
        </div>

        <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
          {analytics.recent_feedback.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-sm text-zinc-500">
                No recent feedback available.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-100">
              {analytics.recent_feedback.map((feedback) => (
                <article
                  key={feedback.feedback_id}
                  className="p-5 sm:p-6"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700">
                        {formatLabel(feedback.source_type)}
                      </span>

                      <span className="rounded-full border border-zinc-200 px-2.5 py-1 text-xs text-zinc-600">
                        {formatLabel(feedback.category)}
                      </span>

                      <span className="rounded-full border border-zinc-200 px-2.5 py-1 text-xs text-zinc-600">
                        {formatLabel(feedback.sentiment)}
                      </span>

                      <span className="rounded-full border border-zinc-200 px-2.5 py-1 text-xs text-zinc-600">
                        {formatLabel(feedback.severity)} severity
                      </span>
                    </div>

                    <span className="shrink-0 text-xs text-zinc-400">
                      {formatDateTime(feedback.source_created_at)}
                    </span>
                  </div>

                  <p className="mt-4 text-sm leading-6 text-zinc-700">
                    {feedback.raw_text}
                  </p>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <h3 className="font-semibold text-zinc-900">
          {title}
        </h3>

        <p className="mt-1 text-sm text-zinc-500">
          {description}
        </p>
      </div>

      {children}
    </div>
  );
}