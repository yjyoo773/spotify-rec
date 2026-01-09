import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const backendBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!backendBase) {
    return NextResponse.json({ error: "NEXT_PUBLIC_API_BASE_URL not set" }, { status: 500 });
  }

  const { searchParams } = new URL(req.url);

  const params = new URLSearchParams();
  for (const key of ["track_ids", "k", "bucket_bias", "genre_only"]) {
    const v = searchParams.get(key);
    if (v != null) params.set(key, v);
  }

  const upstream = `${backendBase}/file-recs/recommend-multi?${params.toString()}`;
  const res = await fetch(upstream, { cache: "no-store" });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
