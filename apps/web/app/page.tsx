import AnalyticsDashboard, {
  ProjectAnalytics,
} from "../components/analytics-dashboard";

import RankedInsights, {
  RankedInsightsResponse,
} from "../components/ranked-insights";

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

const PROJECT_ID = "4a3ed65e-ab06-4b3e-9eb4-8190a7cc7495";

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
      <div className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-sm font-semibold text-zinc-900">
              AI Product Discovery Engine
            </p>

            <p className="text-xs text-zinc-500">
              Feedback intelligence workspace
            </p>
          </div>

          <button
            type="button"
            disabled
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white opacity-50"
          >
            Sync now
          </button>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-10">
        <section className="mb-10">
          <p className="mb-2 text-sm font-medium text-zinc-500">
            Project
          </p>

          <h1 className="text-3xl font-semibold tracking-tight">
            {overview.project_name}
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">
            Monitor customer feedback, identify recurring pain points,
            and prioritize product opportunities using evidence from
            connected sources.
          </p>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Total feedback"
            value={overview.total_feedback.toLocaleString()}
            helper="Feedback collected across all sources"
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
            helper="Recurring evidence-backed problems"
          />
        </section>

        <section className="mt-10">
          <div className="rounded-xl border border-zinc-200 bg-white p-6">
            <h2 className="font-semibold text-zinc-900">
              Project health
            </h2>

            <p className="mt-1 text-sm text-zinc-500">
              Current feedback coverage
            </p>

            <div className="mt-6">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-zinc-600">
                  Relevant feedback
                </span>

                <span className="font-medium text-zinc-900">
                  {relevanceRate}%
                </span>
              </div>

              <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
                <div
                  className="h-full rounded-full bg-zinc-900"
                  style={{
                    width: `${Math.min(relevanceRate, 100)}%`,
                  }}
                />
              </div>

              <p className="mt-4 text-xs leading-5 text-zinc-500">
                Relevant feedback is the portion of collected feedback
                classified as useful for product analysis.
              </p>
            </div>
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
    <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-zinc-500">
        {label}
      </p>

      <p className="mt-3 text-3xl font-semibold tracking-tight">
        {value}
      </p>

      <p className="mt-2 text-xs leading-5 text-zinc-500">
        {helper}
      </p>
    </div>
  );
}