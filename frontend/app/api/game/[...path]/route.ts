import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

function buildTargetUrl(path: string[]) {
  const cleaned = path.filter(Boolean).map(encodeURIComponent).join("/");
  return `${BACKEND_BASE}/api/game/${cleaned}`;
}

async function forward(req: NextRequest, path: string[]) {
  const target = buildTargetUrl(path);
  const body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers: {
        "Content-Type": req.headers.get("content-type") ?? "application/json",
      },
      body,
      cache: "no-store",
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown proxy error";
    return NextResponse.json(
      {
        detail: `Backend request failed via Next proxy: ${detail}`,
        target,
      },
      { status: 502 },
    );
  }
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path);
}
