import type {
  ChunkResult,
  CompareRow,
  DraftSectionResponse,
  Extraction,
  IdeationResponse,
  Paper,
  PaperAnswer,
  PaperMetadata,
  PaperSearchResponse,
  ResearchIdea,
  ReviewReport,
  SectionPlanResponse,
  SentencePlan,
  Workspace,
  WorkspaceCitation,
  WorkspaceContentType,
  WorkspaceGenerationResponse,
  WorkspaceVersion,
} from "./types";


const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://127.0.0.1:8000";


export type ExtractionResponse =
  | Extraction
  | {
      extraction?: Extraction;
    };

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${response.status}: ${text || "Request failed"}`);
  }

  return response.json() as Promise<T>;
}

export const getPapers = (): Promise<Paper[]> => api<Paper[]>("/papers");

export const getPaper = (
  id: string,
): Promise<Paper> =>
  api<Paper>(`/papers/${id}`);

export const getExtraction = (id: string): Promise<ExtractionResponse> =>
  api<ExtractionResponse>(`/papers/${id}/extraction`);

export const searchPaper = (id: string, query: string): Promise<ChunkResult[]> =>
  api<ChunkResult[]>(`/papers/${id}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

export const askPaper = (
  id: string,
  question: string,
  topK = 5
): Promise<PaperAnswer> =>
  api<PaperAnswer>(`/papers/${id}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });

export const comparePapers = (
  paperIds: string[],
): Promise<{ rows: CompareRow[] }> =>
  api<{ rows: CompareRow[] }>("/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper_ids: paperIds }),
  });

export async function uploadPaper(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/papers/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Upload failed");
  }

  return response.json() as Promise<{
    id: string;
    filename: string;
    title: string;
    status: string;
  }>;
}


export const parsePaper = (id: string) =>
  api(`/papers/${id}/parse`, { method: "POST" });

export const extractPaper = (id: string) =>
  api(`/papers/${id}/extract`, { method: "POST" });

export const searchGlobalLiterature = async (
  query: string,
  limit = 5
): Promise<PaperMetadata[]> => {
  const params = new URLSearchParams({ query: query.trim(), limit: String(limit) });
  return api<PaperMetadata[]>(`/discovery/search?${params.toString()}`);
};


export const searchDiscoveryPapers = async (
  query: string,
  limit = 5
): Promise<PaperMetadata[]> => {
  const params = new URLSearchParams({
    query: query.trim(),
    limit: String(limit),
  });

  const response = await api<unknown>(`/search/discovery?${params.toString()}`);
  return Array.isArray(response) ? (response as PaperMetadata[]) : [];
};

export const generateReview = (
  paperId: string,
): Promise<ReviewReport> =>
  api<ReviewReport>(`/reviews/${paperId}`, {
    method: "POST",
  });
