"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6">
      <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-zinc-100 text-lg">
          !
        </div>

        <h1 className="mt-5 text-lg font-semibold text-zinc-900">
          Couldn&apos;t load the dashboard
        </h1>

        <p className="mt-2 text-sm leading-6 text-zinc-500">
          {error.message ||
            "Something went wrong while loading project data."}
        </p>

        <button
          type="button"
          onClick={reset}
          className="mt-6 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800"
        >
          Try again
        </button>
      </div>
    </main>
  );
}