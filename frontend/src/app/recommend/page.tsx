"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import TrackCard from "@/components/TrackCard";
import Spinner from "@/components/Spinner";
import { btn, card, subtext } from "@/lib/ui";
import BackLink from "@/components/BackLink";
import SeedChips from "@/components/SeedChips";

export default function RecommendPage() {
  const sp = useSearchParams();
  const qc = useQueryClient();

  const seedsParam = sp.get("seeds") ?? "";
  const seedIds = seedsParam.split(",").filter(Boolean);

  // Draft controls (editable)
  const [draftK, setDraftK] = useState(25);
  const [draftBucketBias, setDraftBucketBias] = useState(1.0);

  // Applied controls (used by query)
  const [k, setK] = useState(25);
  const [bucketBias, setBucketBias] = useState(1.0);

  const { data = [], isFetching, error, refetch } = useQuery({
    queryKey: ["recommend-multi", seedIds.join(","), k, bucketBias],
    queryFn: ({ signal }) => api.recommendMulti(seedIds, k, bucketBias, { signal }),
    enabled: seedIds.length > 0,
    refetchOnWindowFocus: false,
  });

  const onRefresh = () => {
    setK(draftK);
    setBucketBias(draftBucketBias);
    // react-query will refetch because queryKey changes; call refetch to be explicit
    refetch();
  };

  return (
    <main className="mx-auto max-w-5xl p-6 space-y-6">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <BackLink />
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold">Recommendations</h1>
            <p className={subtext}>Seeds: {seedIds.length || "none"}</p>
          </div>
        </div>
        {isFetching && (
          <div className="flex items-center gap-2">
            <Spinner />
            <button
              className={btn.ghost}
              onClick={() =>
                qc.cancelQueries({ queryKey: ["recommend-multi", seedIds.join(","), k, bucketBias] })
              }
            >
              Cancel
            </button>
          </div>
        )}
      </header>
      <SeedChips />

      <section className={`${card} p-4`}>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div>
            <label className={subtext}>k (results)</label>
            <input
              type="number"
              value={draftK}
              onChange={(e) => setDraftK(Math.min(100, Math.max(1, +e.target.value || 25)))}
              className="w-full rounded-lg border border-[var(--border)] bg-transparent px-2 py-1"
            />
          </div>
          <div>
            <label className={subtext}>bucket bias (0.5–2.0)</label>
            <input
              type="number"
              step="0.1"
              min={0.5}
              max={2.0}
              value={draftBucketBias}
              onChange={(e) => setDraftBucketBias(Math.max(0.1, +e.target.value || 1.0))}
              className="w-full rounded-lg border border-[var(--border)] bg-transparent px-2 py-1"
            />
          </div>
          <div className="md:col-span-2 flex items-end">
            <div className="flex gap-2">
              <button
                onClick={onRefresh}
                className={btn.primary}
                disabled={!seedIds.length || isFetching}
                aria-busy={isFetching}
              >
                {isFetching ? "Fetching…" : "Refresh recommendations"}
              </button>
              <button
                onClick={() =>
                  qc.cancelQueries({ queryKey: ["recommend-multi", seedIds.join(","), k, bucketBias] })
                }
                className={btn.ghost}
                disabled={!isFetching}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </section>

      {error && <div className="text-sm text-red-500">{(error as Error).message}</div>}
      {isFetching && <Spinner label="Generating…" />}

      <div className="grid grid-cols-1 gap-3">
        {data.map((t) => (
          <TrackCard key={t.id} track={t} />
        ))}
      </div>

      {!seedIds.length && (
        <p className={subtext}>
          Go to <Link className="underline" href="/search">Search</Link>, select tracks, and click “Use N seeds →”.
        </p>
      )}
    </main>
  );
}