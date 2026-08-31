import AnalyticsDashboard, {
  type ProjectAnalytics,
} from "@/components/analytics-dashboard";

import RankedInsights, {
  type RankedInsightsResponse,
} from "@/components/ranked-insights";

import SyncButton from "@/components/sync-button";

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

const PROJECT_ID =
  process.env.PROJECT_ID ?? "4a3ed65e-ab06-4b3e-9eb4-8190a7cc7495";

type ProjectOverview = {
  project_id: string;
  project_name: string;
  total_feedback: number;
  relevant_feedback: number;
  source_count: number;
  insight_count: number;
};

async function getProjectOverview(): Promise<ProjectOverview> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${PROJECT_ID}/overview`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to load project overview: ${response.status}`,
    );
  }

  return response.json();
}

async function getProjectAnalytics(): Promise<ProjectAnalytics> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${PROJECT_ID}/analytics?days=30&recent_limit=10`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to load project analytics: ${response.status}`,
    );
  }

  return response.json();
}

async function getRankedInsights(): Promise<RankedInsightsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${PROJECT_ID}/insights?limit=5&offset=0`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to load ranked insights: ${response.status}`,
    );
  }

  return response.json();
}

export default async function Home() {
  const [overview, analytics, insights] = await Promise.all([
    getProjectOverview(),
    getProjectAnalytics(),
    getRankedInsights(),
  ]);

  const relevanceRate =
    overview.total_feedback > 0
      ? Math.round(
          (overview.relevant_feedback / overview.total_feedback) * 100,
        )
      : 0;

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-zinc-900">
              AI Product Discovery Engine
            </p>

            <p className="mt-0.5 text-xs text-zinc-500">
              Feedback intelligence workspace
            </p>
          </div>

          <div className="self-start sm:self-auto">
            <SyncButton projectId={PROJECT_ID} />
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <section className="border-b border-zinc-200 pb-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
                Project
              </p>

              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-zinc-950 sm:text-4xl">
                {overview.project_name}
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-600 sm:text-base">
                Understand what customers are saying, identify recurring
                problems, and prioritize the issues worth investigating.
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              {overview.source_count} connected sources
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Total feedback"
            value={overview.total_feedback.toLocaleString()}
            helper="Raw feedback collected"
          />

          <MetricCard
            label="Relevant feedback"
            value={overview.relevant_feedback.toLocaleString()}
            helper={`${relevanceRate}% of collected feedback`}
          />

          <MetricCard
            label="Connected sources"
            value={overview.source_count.toLocaleString()}
            helper="Active feedback channels"
          />

          <MetricCard
            label="Prioritized issues"
            value={overview.insight_count.toLocaleString()}
            helper="Recurring evidence-backed issues"
          />
        </section>

        <section className="mt-8 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                Analysis coverage
              </p>

              <h2 className="mt-1 font-semibold text-zinc-900">
                Project health
              </h2>

              <p className="mt-1 text-sm text-zinc-500">
                Relevant feedback available for product analysis
              </p>
            </div>

            <div className="sm:text-right">
              <p className="text-3xl font-semibold tracking-tight text-zinc-900">
                {relevanceRate}%
              </p>

              <p className="mt-1 text-xs text-zinc-500">
                relevance rate
              </p>
            </div>
          </div>

          <div className="mt-6 h-2.5 overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full rounded-full bg-zinc-900 transition-all duration-500"
              style={{
                width: `${Math.min(relevanceRate, 100)}%`,
              }}
            />
          </div>

          <div className="mt-3 flex flex-col gap-1 text-xs text-zinc-500 sm:flex-row sm:justify-between">
            <span>
              {overview.relevant_feedback.toLocaleString()} relevant feedback
            </span>

            <span>
              {overview.total_feedback.toLocaleString()} total feedback
            </span>
          </div>
        </section>

        <RankedInsights insights={insights} />

        <AnalyticsDashboard analytics={analytics} />
      </div>
    </main>
  );
}

function MetricCard({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <p className="text-sm font-medium text-zinc-500">
        {label}
      </p>

      <p className="mt-3 text-3xl font-semibold tracking-tight text-zinc-900">
        {value}
      </p>

      <p className="mt-2 text-xs leading-5 text-zinc-500">
        {helper}
      </p>
    </div>
  );
}