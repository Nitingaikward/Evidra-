// API integration hooks. Frontend-only for now: every hook resolves mock data,
// but the fetch path is already wired — set VITE_EVIDRA_API to a running
// FastAPI instance and `live` becomes true.

import { useQuery } from "@tanstack/react-query";
import {
  ARTIFACTS,
  BENCHMARKS,
  CASE,
  CUSTODY_LOG,
  DISK_BLOCKS,
  GRAPH,
  KPIS,
  hexDump,
} from "./forensic-data";

const BASE = (import.meta.env["VITE_EVIDRA_API"] as string | undefined) ?? "";
export const isLive = Boolean(BASE);

async function get<T>(path: string, fallback: T): Promise<T> {
  if (!BASE) return fallback;
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export function useCaseOverview(caseId = CASE.id) {
  return useQuery({
    queryKey: ["overview", caseId],
    queryFn: () =>
      get(`/api/cases/${caseId}/overview`, {
        case: CASE,
        kpis: KPIS,
        benchmarks: BENCHMARKS,
        custody: CUSTODY_LOG,
      }),
  });
}

export function useBlocks(caseId = CASE.id) {
  return useQuery({
    queryKey: ["blocks", caseId],
    queryFn: () => get(`/api/cases/${caseId}/blocks`, DISK_BLOCKS),
  });
}

export function useHexDump(offsetBlock: number | null, caseId = CASE.id) {
  return useQuery({
    enabled: offsetBlock !== null,
    queryKey: ["hex", caseId, offsetBlock],
    queryFn: () =>
      get(
        `/api/cases/${caseId}/blocks/${offsetBlock}/hex`,
        hexDump(offsetBlock ?? 0),
      ),
  });
}

export function useArtifacts(caseId = CASE.id) {
  return useQuery({
    queryKey: ["artifacts", caseId],
    queryFn: () => get(`/api/cases/${caseId}/artifacts`, ARTIFACTS),
  });
}

export function useGraph(caseId = CASE.id) {
  return useQuery({
    queryKey: ["graph", caseId],
    queryFn: () => get(`/api/cases/${caseId}/graph`, GRAPH),
  });
}
