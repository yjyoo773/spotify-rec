"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useState } from "react";

export default function Home() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
  });

  const [q, setQ] = useState("");

  return (
    <main className="mx-auto max-w-4xl p-6 space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">Spotify Recs</h1>
        <p className="text-sm text-gray-600">
          Backend health:{" "}
          {isLoading ? "Checking..." : isError ? (error as Error).message : data?.status ?? "unknown"}
        </p>
      </header>

      <section className="rounded-2xl border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-xl font-medium">Search seeds</h2>
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Track/artist/genre"
            className="flex-1 rounded-xl border px-3 py-2"
          />
          <button
            onClick={() => alert(`Wire this to /tracks/search?q=${q}`)}
            className="rounded-xl bg-black px-4 py-2 text-white"
          >
            Search
          </button>
        </div>
      </section>

      <section className="rounded-2xl border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-xl font-medium">Generate recommendations</h2>
        <button
          onClick={() => alert("Wire this to POST /recommend with your payload")}
          className="rounded-xl bg-emerald-600 px-4 py-2 text-white"
        >
          Generate
        </button>
      </section>

      <footer className="text-xs text-gray-500">
        <button onClick={() => refetch()} className="underline">Retry health</button>
      </footer>
    </main>
  );
}
