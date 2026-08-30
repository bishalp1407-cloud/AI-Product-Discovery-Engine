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

export default async function Home() {
  const overview = await getProjectOverview();

  return (
    <main className="min-h-screen bg-zinc-50 px-6 py-10 text-zinc-950">
      <div className="mx-auto max-w-7xl">
        <header className="mb-10">
          <p className="mb-2 text-sm font-medium text-zinc-500">
            AI Product Discovery Engine
          </p>

          <h1 className="text-3xl font-semibold tracking-tight">
            {overview.project_name}
          </h1>

          <p className="mt-2 text-sm text-zinc-500">
            Customer feedback intelligence dashboard
          </p>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Total Feedback"
            value={overview.total_feedback}
          />

          <MetricCard
            label="Relevant Feedback"
            value={overview.relevant_feedback}
          />

          <MetricCard
            label="Connected Sources"
            value={overview.source_count}
          />

          <MetricCard
            label="Prioritized Issues"
            value={overview.insight_count}
          />
        </section>
      </div>
    </main>
  );
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <p className="text-sm text-zinc-500">{label}</p>

      <p className="mt-2 text-3xl font-semibold tracking-tight">
        {value.toLocaleString()}
      </p>
    </div>
  );
}