import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{
    projectId: string;
  }>;
};

export async function GET(
  _request: NextRequest,
  context: RouteContext,
) {
  const { projectId } = await context.params;

  try {
    const response = await fetch(
      `${API_BASE_URL}/projects/${projectId}/sync/active`,
      {
        method: "GET",
        cache: "no-store",
      },
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch {
    return NextResponse.json(
      {
        detail: "Unable to reach sync service.",
      },
      {
        status: 502,
      },
    );
  }
}