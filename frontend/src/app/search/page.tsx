"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useState } from "react";
import SearchBox from "@/components/SearchBox";
import Spinner from "@/components/Spinner";
import TrackCard from "@/components/TrackCard";
import type { Track } from "@/types/api";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Record<string, Track>>({});

  const { data = [], isFetching, error, refetch } = useQuery({
    queryKey: ["search", q, offset],
    queryFn: () => api.searchTracks(q, 20, offset),
    enabled: !!q,
    // keepPreviousData keeps old results visible while fetching new ones
    staleTime: 0,
    refetchOnWindowFocus: false,
  });

  const toggle = (id: string) => {
    const track = data.find((t) => t.id === id);
    if (!track) return;
    setSelected((s) => {
      const next = { ...s };
      if (next[id]) delete next[id];
      else next[id] = track;
      return next;
    });
  };

  const seeds = Object.keys(selected);

  return (
    <main className="mx-auto max-w-5xl p-6 space-y-6">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Search songs</h1>
        <a
          href={`/recommend?seeds=${encodeURIComponent(seeds.join(","))}`}
          className={`rounded-xl px-4 py-2 text-white ${seeds.length ? "bg-emerald-600" : "bg-gray-300 pointer-events-none"}`}
        >
          Use {seeds.length || 0} seeds →
        </a>
      </header>

      <SearchBox
        loading={isFetching}
        onSearch={(qq) => {
          setQ(qq);
          setOffset(0);
          // If you want immediate fetch even when qq === current q:
          refetch();
        }}
      />

      {error && (
        <div className="text-sm text-red-600">
          Error: {(error as Error).message}
        </div>
      )}

      {/* Top-line loader to indicate background refresh */}
      {isFetching && q ? <Spinner label="Searching…" /> : null}

      <div className="grid grid-cols-1 gap-3">
        {data.map((t) => (
          <TrackCard key={t.id} track={t} selected={!!selected[t.id]} onToggle={toggle} />
        ))}
      </div>

      {q && (
        <div className="flex justify-between">
          <button
            onClick={() => setOffset((o) => Math.max(0, o - 20))}
            className="rounded-lg border px-3 py-1"
            disabled={isFetching || offset === 0}
          >
            ← Prev
          </button>
          <button
            onClick={() => setOffset((o) => o + 20)}
            className="rounded-lg border px-3 py-1"
            disabled={isFetching}
          >
            Next →
          </button>
        </div>
      )}
    </main>
  );
}
