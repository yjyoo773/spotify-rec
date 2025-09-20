import { atom } from "jotai";
import type { Track } from "@/types/api";

// persistent selected seeds (id -> Track)
export const seedsAtom = atom<Record<string, Track>>({});

// derived array of seed IDs
export const seedIdsAtom = atom((get) => Object.keys(get(seedsAtom)));