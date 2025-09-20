"use client";
import { useState } from "react";
import Spinner from "./Spinner";

export default function SearchBox({
  onSearch,
  loading = false,
}: {
  onSearch: (q: string) => void;
  loading?: boolean;
}) {
  const [q, setQ] = useState("");

  return (
    <div className="flex gap-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder='Search by song title (e.g., "Blinding Lights")'
        className="flex-1 rounded-xl border px-3 py-2"
        onKeyDown={(e) => e.key === "Enter" && !loading && onSearch(q)}
        aria-label="Song title"
      />
      <button
        onClick={() => onSearch(q)}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-xl bg-black px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
        aria-busy={loading}
        aria-disabled={loading}
      >
        {loading ? <Spinner /> : null}
        <span>{loading ? "Searching…" : "Search"}</span>
      </button>
    </div>
  );
}
