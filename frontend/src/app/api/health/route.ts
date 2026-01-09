import { NextResponse } from "next/server";

export async function GET() {
  const backendBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!backendBase) {
    return NextResponse.json({ error: "NEXT_PUBLIC_API_BASE_URL not set" }, { status: 500 });
  }

  const res = await fetch(`${backendBase}/file-recs/health`, { cache: "no-store" });
  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
