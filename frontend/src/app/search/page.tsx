"use client";
import { useAtom } from "jotai";
import { seedsAtom, seedIdsAtom } from "@/state/seeds";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useState } from "react";
import SearchBox from "@/components/SearchBox";
import Spinner from "@/components/Spinner";
import TrackCard from "@/components/TrackCard";
import BackLink from "@/components/BackLink";
import { btn, card } from "@/lib/ui";
import Link from "next/link";


export default function SearchPage() {
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [seedsMap, setSeedsMap] = useAtom(seedsAtom);
  const [seedIds] = useAtom(seedIdsAtom);

const { data = [], isFetching, error, refetch } = useQuery({
  queryKey: ["search", q, offset],
  queryFn: () => api.searchTracks(q, 20, offset),
  enabled: q.trim().length > 0,        // <- only run when we have a query
  refetchOnWindowFocus: false,
});


  const toggle = (id: string) => {
    const track = data.find((t) => t.id === id);
    if (!track) return;
    setSeedsMap((prev) => {
      const next = { ...prev };
      if (next[id]) delete next[id];
      else next[id] = track;
      return next;
    });
  };

  return (
    <main className="mx-auto max-w-5xl p-6 space-y-6">
      <header className="flex items-center justify-between gap-3">
        <BackLink />
        <h1 className="text-2xl font-semibold">Search songs</h1>
        <Link
          href={`/recommend?seeds=${encodeURIComponent(seedIds.join(","))}`}
          className={`${btn.primary} ${seedIds.length ? "" : "pointer-events-none opacity-50"}`}
        >
          Use {seedIds.length} seeds →
        </Link>
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
      {q.trim() && error && (
        <div className="text-sm text-red-500">Error: {(error as Error).message}</div>
      )}

      {/* Top-line loader to indicate background refresh */}
      {isFetching && q ? <Spinner label="Searching…" /> : null}

      <div className={`grid grid-cols-1 gap-3 ${card} p-3`}>
        {data.map((t) => (
          <TrackCard key={t.id} track={t} selected={!!seedsMap[t.id]} onToggle={toggle} />
        ))}
      </div>

      {q && (
        <div className="flex justify-between">
          <button
            onClick={() => setOffset((o) => Math.max(0, o - 20))}
            className={btn.ghost}
            disabled={isFetching || offset === 0}
          >
            ← Prev
          </button>
          <button
            onClick={() => setOffset((o) => o + 20)}
            className={btn.ghost}
            disabled={isFetching}
          >
            Next →
          </button>
        </div>
      )}
    </main>
  );
}
