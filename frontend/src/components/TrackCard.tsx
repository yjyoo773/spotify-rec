"use client";
import { Track } from "@/types/api";

export default function TrackCard({
  track,
  selected,
  onToggle,
}: {
  track: Track;
  selected?: boolean;
  onToggle?: (id: string) => void;
}) {
  const img =
  track.album?.imageUrl ||
  "https://placehold.co/64x64?text=♪";
  return (
    <div
      className={`flex items-center gap-3 rounded-xl border p-3 shadow-sm ${selected ? "ring-2 ring-emerald-500" : ""}`}
      onClick={() => onToggle?.(track.id)}
      role="button"
    >
      <img
        src={img}
        alt={track.album?.name || track.name}
        className="h-16 w-16 rounded-lg object-cover"
      />
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{track.name}</div>
        <div className="truncate text-sm text-gray-600">{track.artists.join(", ")}</div>
        <div className="text-xs text-gray-400">
          {track.release_date?.slice(0, 10)} {typeof track.popularity === "number" ? `• pop ${track.popularity}` : ""}
        </div>
      </div>
      {selected !== undefined && (
        <input type="checkbox" checked={!!selected} readOnly className="h-5 w-5" />
      )}
    </div>
  );
}
