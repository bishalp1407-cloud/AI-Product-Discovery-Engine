import Link from "next/link";
import { notFound } from "next/navigation";

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

const PROJECT_ID = "4a3ed65e-ab06-4b3e-9eb4-8190a7cc7495";

type InsightEvidenceItem = {
  feedback_id: string;
  source_type: string;
  raw_text: string;
  severity: string | null;
  sentiment: string | null;
};

type InsightSourceBreakdown = {
  source_type: string;
  evidence_count: number;
};

type InsightDetail = {
  id: string;
  project_id: string;
  title: string;
  category: string;
  description: string | null;
  feedback_count: number;
  reach: number;
  impact: number;
  confidence: number;
  opportunity_score: number;
  source_breakdown: InsightSourceBreakdown[];
  evidence: InsightEvidenceItem[];
};

type InsightPageProps = {
  params: Promise<{
    insightId: string;
  }>;
};

function formatLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

async function getInsightDetail(
  insightId: string,
): Promise<InsightDetail | null> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${PROJECT_ID}/insights/${insightId}`,
    {
      cache: "no-store",
    },
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      `Failed to load insight detail: ${response.status}`,
    );
  }

  return response.json();
}

export default async function InsightPage({
  params,
}: InsightPageProps) {
  const { insightId } = await params;

  const insight = await getInsightDetail(insightId);

  if (!insight) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <div className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-sm font-semibold text-zinc-900">
              AI Product Discovery Engine
            </p>

            <p className="text-xs text-zinc-500">
              Insight investigation
            </p>
          </div>

          <Link
            href="/"
            className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50"
          >
            Back to dashboard
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10">
        <section>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-zinc-900 px-3 py-1 text-xs font-medium text-white">
              {formatLabel(insight.category)}
            </span>

            <span className="text-sm text-zinc-500">
              {insight.feedback_count} supporting feedback
            </span>
          </div>

          <h1 className="mt-4 max-w-4xl text-3xl font-semibold tracking-tight">
            {insight.title}
          </h1>

          {insight.description && (
            <p className="mt-4 max-w-4xl text-base leading-7 text-zinc-600">
              {insight.description}
            </p>
          )}
        </section>

        <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Reach"
            value={`${(insight.reach * 100).toFixed(1)}%`}
            helper="Share of relevant feedback"
          />

          <MetricCard
            label="Impact"
            value={insight.impact.toFixed(1)}
            helper="Average severity"
          />

          <MetricCard
            label="Confidence"
            value={`${Math.round(insight.confidence * 100)}%`}
            helper="Evidence strength"
          />

          <MetricCard
            label="Priority score"
            value={(insight.opportunity_score * 100).toFixed(2)}
            helper="Reach × Impact × Confidence"
          />
        </section>

        <section className="mt-10 grid gap-6 lg:grid-cols-[1fr_2fr]">
          <aside className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
            <h2 className="font-semibold text-zinc-900">
              Evidence sources
            </h2>

            <p className="mt-1 text-sm text-zinc-500">
              Where supporting feedback comes from
            </p>

            <div className="mt-6 space-y-4">
              {insight.source_breakdown.map((source) => (
                <div
                  key={source.source_type}
                  className="flex items-center justify-between"
                >
                  <span className="text-sm text-zinc-600">
                    {formatLabel(source.source_type)}
                  </span>

                  <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-semibold text-zinc-700">
                    {source.evidence_count}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-6 border-t border-zinc-100 pt-5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-700">
                  Total evidence
                </span>

                <span className="text-sm font-semibold text-zinc-900">
                  {insight.feedback_count}
                </span>
              </div>
            </div>
          </aside>

          <div className="rounded-xl border border-zinc-200 bg-white shadow-sm">
            <div className="border-b border-zinc-100 px-6 py-5">
              <h2 className="font-semibold text-zinc-900">
                Supporting customer evidence
              </h2>

              <p className="mt-1 text-sm text-zinc-500">
                Raw feedback used to support this insight
              </p>
            </div>

            <div>
              {insight.evidence.map((item) => (
                <article
                  key={item.feedback_id}
                  className="border-b border-zinc-100 px-6 py-5 last:border-b-0"
                >
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600">
                      {formatLabel(item.source_type)}
                    </span>

                    {item.sentiment && (
                      <span className="text-xs text-zinc-500">
                        {formatLabel(item.sentiment)}
                      </span>
                    )}

                    {item.severity && (
                      <span className="text-xs text-zinc-500">
                        {formatLabel(item.severity)} severity
                      </span>
                    )}
                  </div>

                  <p className="text-sm leading-6 text-zinc-700">
                    {item.raw_text}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>
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
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-zinc-500">
        {label}
      </p>

      <p className="mt-2 text-2xl font-semibold text-zinc-900">
        {value}
      </p>

      <p className="mt-2 text-xs text-zinc-500">
        {helper}
      </p>
    </div>
  );
}