import { CompareRow, Extraction, Paper, ChunkResult, SearchResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

async function api(path: string, options?: RequestInit): Promise<any> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text || "Request failed"}`);
  }

  return res.json();
}

export const getPapers = () => api("/papers") as Promise<Paper[]>;
export const getPaper = (id: string) => api(`/papers/${id}`) as Promise<Paper>;
export const getExtraction = (id: string) => api(`/papers/${id}/extraction`) as Promise<Extraction>;

export const searchPaper = (id: string, query: string) =>
  api(`/papers/${id}/search`, {
    method: "POST",
    body: JSON.stringify({ query }),
    headers: { "Content-Type": "application/json" },
  }) as Promise<ChunkResult[]>;

export interface SemanticSearchResponse {
  query: string;
  count: number;
  results: SearchResult[];
}

export const comparePapers = (paperIds: string[]) =>
  api("/compare", {
    method: "POST",
    body: JSON.stringify({ paper_ids: paperIds }),
    headers: { "Content-Type": "application/json" },
  }) as Promise<CompareRow[]>;

export const semanticSearch = async (
  query: string,
  paperIds?: string[],
  topK = 5
): Promise<SemanticSearchResponse> => {
  return api("/search/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      paper_ids: paperIds?.length ? paperIds : null,
      top_k: topK,
    }),
  });
};

export async function uploadPaper(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/papers/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Upload failed");
  }

  return res.json();
}

export const parsePaper = (id: string) =>
  api(`/papers/${id}/parse`, { method: "POST" });

export const extractPaper = (id: string) =>
  api(`/papers/${id}/extract`, { method: "POST" });