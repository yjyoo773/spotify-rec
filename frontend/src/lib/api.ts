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

function coerceTrackList(payload: any): Track[] {
  const list = Array.isArray(payload) ? payload : payload?.items ?? [];
  return list.map((t: any) => ({
    id: t.id,
    name: t.title ?? t.name ?? String(t.id),
    artists: Array.isArray(t.artists) ? t.artists : [],
    year: t.year,
    pop_bucket: t.pop_bucket,
  }));
}

export const api = {
  health: () =>
    request<{ status: string; service?: string; mode?: string }>("/api/file-recs/health"),

  searchTracks: async (q: string, limit = 20, offset = 0, opts?: { signal?: AbortSignal }) => {
    const s = (q ?? "").trim();
    if (!s) return [];
    const params = new URLSearchParams({ q: s, limit: String(limit) });
    const raw = await request<any>(`/api/search?${params.toString()}`, { signal: opts?.signal });
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
    const raw = await request<any>(`/api/recommend?${params.toString()}`, { signal: opts?.signal });
    return coerceTrackList(raw);
  },

  recommendMulti: async (trackIds: string[], k = 25, bucketBias = 1.0, opts?: { signal?: AbortSignal }) => {
    if (!trackIds.length) return [];
    const params = new URLSearchParams({
      track_ids: trackIds.join(","),
      k: String(k),
      bucket_bias: String(bucketBias),
    });
    const raw = await request<any>(`/api/recommend-multi?${params.toString()}`, {
      signal: opts?.signal,
    });
    return coerceTrackList(raw);
  },
};
