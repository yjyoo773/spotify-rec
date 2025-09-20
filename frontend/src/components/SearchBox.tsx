"use client";
import { useState } from "react";
import Spinner from "./Spinner";
import { btn } from "@/lib/ui";

export default function SearchBox({
  onSearch,
  loading = false,
}: {
  onSearch: (q: string) => void;
  loading?: boolean;
}) {
  const [q, setQ] = useState("");
  const canSearch = !loading && q.trim().length > 0;

  return (
    <div className="flex gap-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder='Search by song title (e.g., "Blinding Lights")'
        className="flex-1 rounded-xl border border-[var(--border)] bg-transparent px-3 py-2"
        onKeyDown={(e) => {
          if (e.key === "Enter" && canSearch) onSearch(q.trim());
          if (e.key === "Enter" && !canSearch) e.preventDefault();
        }}
        aria-label="Song title"
      />
      <button
        onClick={() => canSearch && onSearch(q.trim())}
        disabled={!canSearch}
        className={`${btn.primary} inline-flex items-center gap-2 rounded-xl bg-black px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50`}
        aria-busy={loading}
        aria-disabled={!canSearch}
      >
        {loading ? <Spinner /> : null}
        <span>{loading ? "Searching…" : "Search"}</span>
      </button>
    </div>
  );
}
