export type Track = {
  id: string;
  name: string;           
  artists: string[];       
  year?: string;           
  pop_bucket?: number;    
};


export type RecommendRequest = {
  seeds: {
    trackIds?: string[];
    artistIds?: string[];
    genres?: string[];
  };
  filters?: {
    year_min?: number;
    year_max?: number;
    popularity_bucket?: number; // aligns with your pop_red
    artist_diversity?: boolean;
    limit?: number;
  };
};

export type RecommendResponse = {
  items: { track: Track; score: number; reason?: string }[];
  meta?: { latency_ms?: number; cache?: "hit" | "miss" };
};