import { CompareRow, Extraction, Paper, ChunkResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

async function api<T>(path: string, options?: RequestInit): Promise<T> {
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

export const getPapers = () => api<Paper[]>("/papers");
export const getPaper = (id: string) => api<Paper>(`/papers/${id}`);
export const getExtraction = (id: string) => api<Extraction>(`/papers/${id}/extraction`);

export const searchPaper = (id: string, query: string) =>
  api<ChunkResult[]>(`/papers/${id}/search`, {
    method: "POST",
    body: JSON.stringify({ query }),
    headers: { "Content-Type": "application/json" },
  });

export const comparePapers = (paperIds: string[]) =>
  api<CompareRow[]>("/compare", {
    method: "POST",
    body: JSON.stringify({ paper_ids: paperIds }),
    headers: { "Content-Type": "application/json" },
  });

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