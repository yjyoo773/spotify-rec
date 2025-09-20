"use client";
import { useState } from "react";

export default function SearchBox({ onSearch }: { onSearch: (q: string) => void }) {
  const [q, setQ] = useState("");
  return (
    <div className="flex gap-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Track, artist, or genre"
        className="flex-1 rounded-xl border px-3 py-2"
        onKeyDown={(e) => e.key === "Enter" && onSearch(q)}
      />
      <button onClick={() => onSearch(q)} className="rounded-xl bg-black px-4 py-2 text-white">
        Search
      </button>
    </div>
  );
}