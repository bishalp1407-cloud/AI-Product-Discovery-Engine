export default function Loading() {
  return (
    <main className="min-h-screen bg-zinc-50">
      <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
        <div className="animate-pulse">
          <div className="mb-10 flex items-center justify-between">
            <div>
              <div className="h-5 w-52 rounded bg-zinc-200" />
              <div className="mt-2 h-3 w-40 rounded bg-zinc-200" />
            </div>

            <div className="h-9 w-24 rounded-lg bg-zinc-200" />
          </div>

          <div className="mb-8">
            <div className="h-8 w-48 rounded bg-zinc-200" />
            <div className="mt-3 h-4 w-80 max-w-full rounded bg-zinc-200" />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="h-28 rounded-xl border border-zinc-200 bg-white"
              />
            ))}
          </div>

          <div className="mt-10 h-72 rounded-xl border border-zinc-200 bg-white" />

          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <div className="h-80 rounded-xl border border-zinc-200 bg-white" />
            <div className="h-80 rounded-xl border border-zinc-200 bg-white" />
          </div>
        </div>
      </div>
    </main>
  );
}