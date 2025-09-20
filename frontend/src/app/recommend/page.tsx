"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import TrackCard from "@/components/TrackCard";
import Spinner from "@/components/Spinner";
import BackLink from "@/components/BackLink";
import { btn, card, subtext } from "@/lib/ui";

export default function RecommendPage() {
  const sp = useSearchParams();
  const seedsParam = sp.get("seeds") ?? "";
  const seedIds = seedsParam.split(",").filter(Boolean);

  const [limit, setLimit] = useState(25);

  const { data = [], isFetching, error, refetch } = useQuery({
    queryKey: ["recommend", seedIds.join(","), limit],
    queryFn: () => api.recommendByIds(seedIds, limit),
    enabled: seedIds.length > 0,
  });

  return (
    <main className="mx-auto max-w-5xl p-6 space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Recommendations</h1>
        <p className={subtext}>Seeds: {seedIds.length || "none"}</p>
      </header>
      <BackLink/>
      <section className={`${card} p-4`}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <div className="col-span-2">
            <label className={subtext}>Limit</label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(Math.max(1, +e.target.value || 1))}
              className="w-full rounded-lg border border-[var(--border)] bg-transparent px-2 py-1"
            />
          </div>
        </div>
        <div className="mt-3">
          <button
            onClick={() => refetch()}
            className={btn.primary}
            disabled={!seedIds.length || isFetching}
            aria-busy={isFetching}
          >
            {isFetching ? "Fetching…" : "Refresh recommendations"}
          </button>
        </div>
      </section>

      {error && (
        <div className="text-sm text-red-600">
          {(error as Error).message}
        </div>
      )}

      {isFetching && <Spinner label="Generating recommendations…" />}

      <div className="grid grid-cols-1 gap-3">
        {data.map((t) => (
          <TrackCard key={t.id} track={t} />
        ))}
      </div>

      {!seedIds.length && (
        <p className="text-sm text-gray-500">
          Go to <a href="/search" className={`${btn.ghost} underline`}>Search</a>, select tracks, and click “Use N seeds →”.
        </p>
      )}
    </main>
  );
}
