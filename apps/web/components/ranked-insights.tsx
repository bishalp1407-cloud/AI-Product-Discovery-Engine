import Link from "next/link";

export type RankedInsight = {
  id: string;
  rank: number;
  title: string;
  category: string;
  description: string | null;
  feedback_count: number;
  reach: number;
  impact: number;
  confidence: number;
  opportunity_score: number;
};

export type RankedInsightsResponse = {
  project_id: string;
  total: number;
  limit: number;
  offset: number;
  items: RankedInsight[];
};

type RankedInsightsProps = {
  insights: RankedInsightsResponse;
};

function formatLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function RankedInsights({
  insights,
}: RankedInsightsProps) {
  return (
    <section className="mt-10">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            Prioritized issues
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Recurring customer problems ranked by reach, impact, and confidence
          </p>
        </div>

        <span className="shrink-0 rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600">
          {insights.total} issues
        </span>
      </div>

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        {insights.items.map((insight) => (
          <Link
            key={insight.id}
            href={`/insights/${insight.id}`}
            className="block border-b border-zinc-100 p-6 transition hover:bg-zinc-50 last:border-b-0"
          >
            <article>
              <div className="flex gap-5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-sm font-semibold text-white">
                  {insight.rank}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-zinc-900">
                      {insight.title}
                    </h3>

                    <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600">
                      {formatLabel(insight.category)}
                    </span>
                  </div>

                  {insight.description && (
                    <p className="mt-2 max-w-4xl text-sm leading-6 text-zinc-600">
                      {insight.description}
                    </p>
                  )}

                  <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                    <InsightMetric
                      label="Evidence"
                      value={`${insight.feedback_count}`}
                    />

                    <InsightMetric
                      label="Reach"
                      value={`${(insight.reach * 100).toFixed(1)}%`}
                    />

                    <InsightMetric
                      label="Impact"
                      value={insight.impact.toFixed(1)}
                    />

                    <InsightMetric
                      label="Confidence"
                      value={`${Math.round(insight.confidence * 100)}%`}
                    />

                    <InsightMetric
                      label="Priority score"
                      value={(insight.opportunity_score * 100).toFixed(2)}
                    />
                  </div>

                  <div className="mt-5 flex items-center justify-end">
                    <span className="text-sm font-medium text-zinc-700">
                      View evidence →
                    </span>
                  </div>
                </div>
              </div>
            </article>
          </Link>
        ))}

        {insights.items.length === 0 && (
          <div className="px-6 py-12 text-center">
            <p className="text-sm font-medium text-zinc-700">
              No prioritized issues yet
            </p>

            <p className="mt-2 text-sm text-zinc-500">
              Sync and analyze feedback to generate evidence-backed issues.
            </p>
          </div>
        )}
      </div>

      {insights.total > insights.items.length && (
        <p className="mt-3 text-right text-xs text-zinc-500">
          Showing top {insights.items.length} of {insights.total} issues
        </p>
      )}
    </section>
  );
}

function InsightMetric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs text-zinc-500">
        {label}
      </p>

      <p className="mt-1 text-sm font-semibold text-zinc-900">
        {value}
      </p>
    </div>
  );
}