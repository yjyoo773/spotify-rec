"use client";
import { Track } from "@/types/api";
import { card, subtext, faint } from "@/lib/ui";

export default function TrackCard({
  track,
  selected,
  onToggle,
}: {
  track: Track;
  selected?: boolean;
  onToggle?: (id: string) => void;
}) {
  return (
    <div
      className={`flex items-center gap-3 ${card} p-3 hover:bg-[var(--hover)] ${selected ? "outline outline-2 outline-[var(--spotify-green)]" : ""}`}
      onClick={() => onToggle?.(track.id)}
      role="button"
    >
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{track.name}</div>
        <div className={`truncate ${subtext}`}>{track.artists.join(", ")}</div>
        <div className={faint}>
          {track.year ?? ""}
        </div>
      </div>
      {selected !== undefined && <input type="checkbox" checked={!!selected} readOnly className="h-5 w-5" />}
    </div>
  );
}
