import type { Track } from "@/types/api";

export const API_BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init, // pass AbortSignal through
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

type TrackWire = Partial<{
  id: string;
  title: string;
  name: string;
  artists: unknown;
  year: number;
  pop_bucket: number;
}>;

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null;
}


function coerceTrackList(payload: unknown): Track[] {
  const list: unknown[] = Array.isArray(payload)
    ? payload
    : isRecord(payload) && Array.isArray(payload.items)
      ? (payload.items as unknown[])
      : [];

  return list.map((t): Track => {
    const obj: TrackWire = isRecord(t) ? (t as TrackWire) : {};

    const id = typeof obj.id === "string" ? obj.id : String(obj.id ?? "");
    const name =
      typeof obj.title === "string"
        ? obj.title
        : typeof obj.name === "string"
          ? obj.name
          : id || "unknown";

    const artists = Array.isArray(obj.artists) ? (obj.artists as string[]) : [];

    return {
      id,
      name,
      artists,
      year: typeof obj.year === "number" ? obj.year : undefined,
      pop_bucket: typeof obj.pop_bucket === "number" ? obj.pop_bucket : undefined,
    } as Track;
  });
}


export const api = {
  health: () =>
    request<{ status: string; service?: string; mode?: string }>("/api/health"),

  searchTracks: async (q: string, limit = 20, offset = 0, opts?: { signal?: AbortSignal }) => {
    const s = (q ?? "").trim();
    if (!s) return [];

    const params = new URLSearchParams({
      q: s,
      limit: String(limit),
      offset: String(offset),
    });

    const raw = await request<unknown>(`/api/search?${params.toString()}`, { signal: opts?.signal });
    return coerceTrackList(raw);
  },

 recommendSingle: async (
    trackId: string,
    k = 25,
    bucketBias = 1.0,
    genreOnly?: string,
    opts?: { signal?: AbortSignal }
  ) => {
    const params = new URLSearchParams({
      track_id: trackId,
      k: String(k),
      bucket_bias: String(bucketBias),
    });
    if (genreOnly) params.set("genre_only", genreOnly);

    const raw = await request<unknown>(`/api/recommend?${params.toString()}`, { signal: opts?.signal });
    return coerceTrackList(raw);
  },

  recommendMulti: async (
    trackIds: string[],
    k = 25,
    bucketBias = 1.0,
    opts?: { signal?: AbortSignal }
  ) => {
    if (!trackIds.length) return [];

    const params = new URLSearchParams({
      track_ids: trackIds.join(","),
      k: String(k),
      bucket_bias: String(bucketBias),
    });

    const raw = await request<unknown>(`/api/recommend-multi?${params.toString()}`, {
      signal: opts?.signal,
    });
    return coerceTrackList(raw);
  },
};