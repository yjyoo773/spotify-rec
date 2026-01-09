import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const backendBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!backendBase) {
    return NextResponse.json({ error: "NEXT_PUBLIC_API_BASE_URL not set" }, { status: 500 });
  }

  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") ?? "";
  const limit = searchParams.get("limit") ?? "20";

  const upstream = `${backendBase}/file-recs/search?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`;
  const res = await fetch(upstream, { cache: "no-store" });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
