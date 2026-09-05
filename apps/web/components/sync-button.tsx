"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type SyncResult = {
  project_id: string;
  sources_synced: number;
  feedback_fetched: number;
  feedback_created: number;
  duplicates: number;
  analyses_completed: number;
  analyses_failed: number;
  insights_created: number;
};

type SyncJobCreated = {
  job_id: string;
  project_id: string;
  status: string;
};

type SyncJobStatus = {
  job_id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_stage: string | null;
  total_items: number;
  processed_items: number;
  total_batches: number;
  completed_batches: number;
  error: string | null;
  result: SyncResult | null;
};

type SyncButtonProps = {
  projectId: string;
};

const POLL_INTERVAL_MS = 2000;

function getProgressMessage(job: SyncJobStatus): string {
  if (job.status === "queued") {
    return "Waiting to start...";
  }

  if (job.status !== "running") {
    return "Sync in progress...";
  }

  switch (job.current_stage) {
    case "ingesting":
      if (job.total_items > 0) {
        return `Syncing sources · ${job.processed_items}/${job.total_items}`;
      }

      return "Syncing sources...";

    case "analyzing":
      if (job.total_items > 0) {
        return `Analyzing feedback · ${job.processed_items}/${job.total_items}`;
      }

      return "Analyzing feedback...";

    case "generating_insights":
      if (job.total_batches > 0) {
        return `Generating insights · ${job.completed_batches}/${job.total_batches}`;
      }

      return "Generating insights...";

    default:
      return "Sync in progress...";
  }
}

export default function SyncButton({
  projectId,
}: SyncButtonProps) {
  const router = useRouter();

  const storageKey = `active-sync-job:${projectId}`;

  /*
   * Keep the initial state identical on the server and client.
   *
   * We intentionally do NOT read localStorage inside useState
   * initializers because localStorage only exists in the browser.
   * Reading it during the initial render can cause a React hydration
   * mismatch.
   *
   * The discoverActiveJob effect below handles localStorage and
   * backend job discovery after hydration.
   */
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const [isSyncing, setIsSyncing] = useState(false);

  const [message, setMessage] = useState<string | null>(null);

  /*
   * Discover an active job from the backend.
   *
   * This is important because localStorage only belongs to one
   * browser/device. PostgreSQL is the source of truth for whether
   * the project already has a running sync.
   */
  useEffect(() => {
    let cancelled = false;

    async function discoverActiveJob() {
      try {
        const response = await fetch(
          `/api/projects/${projectId}/sync/active`,
          {
            method: "GET",
            cache: "no-store",
          },
        );

        /*
         * 404 simply means there is currently no active job.
         * That is a normal state, not an error.
         */
        if (response.status === 404) {
          /*
           * If there is no backend job, also make sure a stale
           * localStorage entry does not keep the button stuck.
           */
          window.localStorage.removeItem(storageKey);
          setActiveJobId(null);
          setIsSyncing(false);
          setMessage(null);

          return;
        }

        const data = (await response.json()) as
          | SyncJobStatus
          | { detail?: string };

        if (!response.ok) {
          throw new Error(
            "detail" in data && data.detail
              ? data.detail
              : "Failed to check active sync.",
          );
        }

        if (cancelled) {
          return;
        }

        const job = data as SyncJobStatus;

        if (
          job.status === "queued" ||
          job.status === "running"
        ) {
          window.localStorage.setItem(
            storageKey,
            job.job_id,
          );

          setActiveJobId(job.job_id);
          setIsSyncing(true);
          setMessage(getProgressMessage(job));

          return;
        }

        /*
         * If the backend reports a completed/failed job as the
         * active job, clean up the local state.
         */
        window.localStorage.removeItem(storageKey);
        setActiveJobId(null);
        setIsSyncing(false);
      } catch (error) {
        if (cancelled) {
          return;
        }

        /*
         * Failure to discover an active job should not destroy
         * an already-known local job.
         */
        const storedJobId =
          window.localStorage.getItem(storageKey);

        if (storedJobId) {
          setActiveJobId(storedJobId);
          setIsSyncing(true);
          setMessage(
            "Unable to check sync status. Retrying...",
          );
        }

        console.error(
          "Failed to discover active sync job:",
          error,
        );
      }
    }

    void discoverActiveJob();

    return () => {
      cancelled = true;
    };
  }, [projectId, storageKey]);

  /*
   * Poll the backend whenever we know about an active job.
   */
  useEffect(() => {
    if (!activeJobId) {
      return;
    }

    let cancelled = false;

    async function checkStatus() {
      try {
        const statusResponse = await fetch(
          `/api/projects/${projectId}/sync/${activeJobId}`,
          {
            method: "GET",
            cache: "no-store",
          },
        );

        const statusData = (await statusResponse.json()) as
          | SyncJobStatus
          | { detail?: string };

        if (!statusResponse.ok) {
          throw new Error(
            "detail" in statusData && statusData.detail
              ? statusData.detail
              : "Failed to check sync status.",
          );
        }

        if (cancelled) {
          return;
        }

        const currentJob = statusData as SyncJobStatus;

        if (
          currentJob.status === "queued" ||
          currentJob.status === "running"
        ) {
          setIsSyncing(true);
          setMessage(getProgressMessage(currentJob));

          return;
        }

        if (currentJob.status === "failed") {
          window.localStorage.removeItem(storageKey);

          setActiveJobId(null);
          setIsSyncing(false);
          setMessage(
            currentJob.error ?? "Sync failed.",
          );

          return;
        }

        if (currentJob.status === "completed") {
          const result = currentJob.result;

          if (!result) {
            throw new Error(
              "Sync completed without a result.",
            );
          }

          window.localStorage.removeItem(storageKey);

          setActiveJobId(null);
          setIsSyncing(false);

          setMessage(
            `Sync complete · ${result.feedback_created} new feedback · ${result.analyses_completed} analyzed · ${result.insights_created} prioritized issues`,
          );

          router.refresh();
        }
      } catch (error) {
        if (cancelled) {
          return;
        }

        /*
         * A temporary polling/network failure does not mean
         * the backend job has stopped.
         *
         * Keep the job ID and retry on the next interval.
         */
        setIsSyncing(true);

        setMessage(
          error instanceof Error
            ? `${error.message} Retrying...`
            : "Unable to check sync status. Retrying...",
        );
      }
    }

    void checkStatus();

    const intervalId = window.setInterval(
      () => void checkStatus(),
      POLL_INTERVAL_MS,
    );

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeJobId, projectId, router, storageKey]);

  async function handleSync() {
    if (isSyncing) {
      return;
    }

    setIsSyncing(true);
    setMessage("Starting sync...");

    try {
      const startResponse = await fetch(
        `/api/projects/${projectId}/sync`,
        {
          method: "POST",
        },
      );

      const startData = (await startResponse.json()) as
        | SyncJobCreated
        | { detail?: string };

      if (!startResponse.ok) {
        throw new Error(
          "detail" in startData && startData.detail
            ? startData.detail
            : "Failed to start sync.",
        );
      }

      const job = startData as SyncJobCreated;

      window.localStorage.setItem(
        storageKey,
        job.job_id,
      );

      setActiveJobId(job.job_id);
      setIsSyncing(true);
      setMessage("Waiting to start...");
    } catch (error) {
      setIsSyncing(false);

      setMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong while syncing.",
      );
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={handleSync}
        disabled={isSyncing}
        className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSyncing ? "Syncing..." : "Sync now"}
      </button>

      {message && (
        <p className="max-w-sm text-right text-xs text-zinc-500">
          {message}
        </p>
      )}
    </div>
  );
}