"use client";
import { useAtom } from "jotai";
import { seedsAtom, seedIdsAtom } from "@/state/seeds";
import { btn, faint } from "@/lib/ui";

export default function SeedChips() {
  const [seeds, setSeeds] = useAtom(seedsAtom);
  const [ids] = useAtom(seedIdsAtom);
  if (!ids.length) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {ids.map((id) => (
        <span key={id} className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] px-3 py-1">
          <span className={faint}>{seeds[id]?.name ?? id}</span>
          <button
            className={btn.link}
            onClick={() => {
              const next = { ...seeds };
              delete next[id];
              setSeeds(next);
            }}
            title="Remove from seeds"
          >
            ×
          </button>
        </span>
      ))}
    </div>
  );
}
