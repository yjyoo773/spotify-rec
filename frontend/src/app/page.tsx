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
      <h1 className="text-3xl font-semibold">Spotify Recs</h1>
      <p className="text-gray-600">Choose a flow:</p>
      <div className="flex gap-3">
        <a href="/search" className="rounded-xl border px-4 py-2 hover:bg-gray-50">Search</a>
        <a href="/recommend" className="rounded-xl border px-4 py-2 hover:bg-gray-50">Recommendations</a>
      </div>
    </main>
  );
}
