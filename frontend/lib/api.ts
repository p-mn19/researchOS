import {
  ChunkResult,
  CompareRow,
  Extraction,
  Paper,
  PaperMetadata,
  ReviewReport,
  SearchResult,
} from "./types";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").replace(/\/+$/, "");

async function api(path: string, options?: RequestInit): Promise<any> {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      cache: "no-store",
      headers: {
        ...(options?.headers || {}),
      },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(
        `API ${response.status}: ${text || "Request failed"}`
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to fetch ${url}: ${error.message}`);
    }
    throw new Error(`Failed to fetch ${url}`);
  }
}

function normalizePaper(raw: any): Paper {
  return {
    id: String(raw.id ?? raw._id ?? raw.paper_id ?? ""),
    title: raw.title ?? "",
    filename: raw.filename ?? raw.original_filename ?? "",
    authors: raw.authors ?? [],
    year: raw.year ?? raw.publication_year ?? null,
    abstract: raw.abstract ?? "",
    uploaded_at: raw.uploaded_at ?? raw.uploadedAt,
    status: raw.status ?? "uploaded",
    methodology: raw.methodology,
    dataset: raw.dataset,
    limitations: raw.limitations,
  };
}

export const getPapers = async (): Promise<Paper[]> => {
  const response = await api("/papers/");

  const rawPapers = Array.isArray(response)
    ? response
    : response.papers ?? response.data ?? [];

  return rawPapers
    .map(normalizePaper)
    .filter((paper: Paper) => paper.id.length > 0);
};

export const getPaper = (id: string) =>
  api(`/papers/${encodeURIComponent(id)}`) as Promise<Paper>;

export const getExtraction = (id: string) =>
  api(`/papers/${encodeURIComponent(id)}/extraction`) as Promise<Extraction>;

export const searchPaper = async (
  id: string,
  query: string
): Promise<ChunkResult[]> => {
  const response = await api(`/papers/${encodeURIComponent(id)}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      top_k: 5,
    }),
  });

  const results = Array.isArray(response)
    ? response
    : response.results ?? [];

  return results.map((chunk: any) => ({
    ...chunk,
    page:
      chunk.page ??
      chunk.page_number ??
      chunk.page_no ??
      chunk.pageno ??
      chunk.pageNum ??
      null,
    section_title:
      chunk.section_title ??
      chunk.section ??
      chunk.section_name ??
      "",
  }));
};

export const semanticSearch = async (
  query: string,
  paperIds?: string[],
  topK = 5
): Promise<{
  query: string;
  count: number;
  results: SearchResult[];
}> => {
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

export const searchDiscoveryPapers = async (
  query: string,
  limit = 5
): Promise<PaperMetadata[]> => {
  return api(
    `/search/discovery?query=${encodeURIComponent(query)}&limit=${limit}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
};

export const generateReview = async (
  paperId: string
): Promise<ReviewReport> => {
  const normalizedId = String(paperId ?? "").trim();

  if (
    !normalizedId ||
    normalizedId === "undefined" ||
    normalizedId === "null"
  ) {
    throw new Error("The selected paper has no valid ID.");
  }

  return api(`/reviews/${encodeURIComponent(normalizedId)}`, {
    method: "POST",
  });
};

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

  return response.json();
}

export const parsePaper = (id: string) =>
  api(`/papers/${id}/parse`, {
    method: "POST",
  });

export const extractPaper = (id: string) =>
  api(`/papers/${id}/extract`, {
    method: "POST",
  });

export const comparePapers = async (
  paperIds: string[]
): Promise<CompareRow[]> => {
  const response = await api("/compare", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      paper_ids: paperIds,
    }),
  });

  return Array.isArray(response)
    ? response
    : response.rows ?? [];
};