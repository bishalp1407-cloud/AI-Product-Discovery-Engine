import { NextResponse } from "next/server";

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{
    projectId: string;
    jobId: string;
  }>;
};

export async function GET(
  _request: Request,
  context: RouteContext,
) {
  const { projectId, jobId } = await context.params;

  try {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectId}/sync/${jobId}`,
      {
        method: "GET",
        cache: "no-store",
      },
    );

    const text = await response.text();

    let data: unknown = null;

    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = {
          detail: text,
        };
      }
    }

    if (!response.ok) {
      return NextResponse.json(
        data ?? {
          detail: "Failed to check sync status.",
        },
        {
          status: response.status,
        },
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : "Unable to reach the API.",
      },
      {
        status: 502,
      },
    );
  }
}