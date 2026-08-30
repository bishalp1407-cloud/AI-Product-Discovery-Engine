"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

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
  error: string | null;
  result: SyncResult | null;
};

type SyncButtonProps = {
  projectId: string;
};

const POLL_INTERVAL_MS = 2000;

function sleep(milliseconds: number) {
  return new Promise((resolve) =>
    setTimeout(resolve, milliseconds),
  );
}

export default function SyncButton({
  projectId,
}: SyncButtonProps) {
  const router = useRouter();

  const [isSyncing, setIsSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

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

      setMessage("Sync in progress...");

      while (true) {
        await sleep(POLL_INTERVAL_MS);

        const statusResponse = await fetch(
          `/api/projects/${projectId}/sync/${job.job_id}`,
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

        const currentJob = statusData as SyncJobStatus;

        if (
          currentJob.status === "queued" ||
          currentJob.status === "running"
        ) {
          setMessage("Sync in progress...");
          continue;
        }

        if (currentJob.status === "failed") {
          throw new Error(
            currentJob.error ?? "Sync failed.",
          );
        }

        if (currentJob.status === "completed") {
          const result = currentJob.result;

          if (!result) {
            throw new Error(
              "Sync completed without a result.",
            );
          }

          setMessage(
            `Sync complete · ${result.feedback_created} new feedback · ${result.analyses_completed} analyzed · ${result.insights_created} insights`,
          );

          router.refresh();
          break;
        }
      }
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong while syncing.",
      );
    } finally {
      setIsSyncing(false);
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