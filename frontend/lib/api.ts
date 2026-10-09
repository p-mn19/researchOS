import type {
  CompareRow,
  DocumentFormat,
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

export type LatexCompileError = {
  line: number | null;
  message: string;
};

export type WorkspaceLatexCompileStatusResponse = {
  success: boolean;
  log: string;
  errors: LatexCompileError[];
  document_format?: DocumentFormat;
};

async function api<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      ...options,
      headers: {
        ...(options?.headers || {}),
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const text = await response.text();

    throw new Error(
      `API ${response.status}: ${text || "Request failed"}`,
    );
  }

  return response.json() as Promise<T>;
}

/* ============================================================
   Papers
   ============================================================ */

export const getPapers = (): Promise<Paper[]> =>
  api<Paper[]>("/papers");

export const getPaper = (
  id: string,
): Promise<Paper> =>
  api<Paper>(`/papers/${id}`);

export const getExtraction = (
  id: string,
): Promise<ExtractionResponse> =>
  api<ExtractionResponse>(
    `/papers/${id}/extraction`,
  );

export const deletePaper = (
  id: string,
): Promise<{
  paper_id: string;
  message: string;
  vectors_deleted: number;
  chunks_deleted: number;
  extraction_deleted: number;
  file_deleted: boolean;
}> =>
  api<{
    paper_id: string;
    message: string;
    vectors_deleted: number;
    chunks_deleted: number;
    extraction_deleted: number;
    file_deleted: boolean;
  }>(
    `/papers/${id}`,
    {
      method: "DELETE",
    },
  );

export const searchPaper = (
  id: string,
  query: string,
  topK = 5,
): Promise<PaperSearchResponse> =>
  api<PaperSearchResponse>(
    `/papers/${id}/search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        top_k: topK,
      }),
    },
  );

export const askPaper = (
  id: string,
  question: string,
  topK = 5,
): Promise<PaperAnswer> =>
  api<PaperAnswer>(
    `/papers/${id}/answer`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        top_k: topK,
      }),
    },
  );

export async function uploadPaper(
  file: File,
): Promise<{
  id: string;
  filename: string;
  title: string;
  status: string;
}> {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(
    `${API_BASE}/papers/upload`,
    {
      method: "POST",
      body: formData,
    },
  );

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

export const parsePaper = (
  id: string,
) =>
  api(
    `/papers/${id}/parse`,
    {
      method: "POST",
    },
  );

export const extractPaper = (
  id: string,
): Promise<ExtractionResponse> =>
  api<ExtractionResponse>(
    `/papers/${id}/extract`,
    {
      method: "POST",
    },
  );

/* ============================================================
   Comparison and Review
   ============================================================ */

export const comparePapers = (
  paperIds: string[],
): Promise<{
  rows: CompareRow[];
  paper_map?: Record<string, string>;
}> =>
  api<{
    rows: CompareRow[];
    paper_map?: Record<string, string>;
  }>(
    "/compare",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        paper_ids: paperIds,
      }),
    },
  );

export const generateReview = (
  paperId: string,
): Promise<ReviewReport> =>
  api<ReviewReport>(
    `/reviews/${paperId}`,
    {
      method: "POST",
    },
  );

/* ============================================================
   Literature Discovery
   ============================================================ */

export const searchGlobalLiterature = async (
  query: string,
  limit = 5,
): Promise<PaperMetadata[]> => {
  const params = new URLSearchParams({
    query: query.trim(),
    limit: String(limit),
  });

  return api<PaperMetadata[]>(
    `/discovery/search?${params.toString()}`,
  );
};

export const searchDiscoveryPapers = async (
  query: string,
  limit = 5,
): Promise<PaperMetadata[]> => {
  const params = new URLSearchParams({
    query: query.trim(),
    limit: String(limit),
  });

  const response = await api<unknown>(
    `/search/discovery?${params.toString()}`,
  );

  return Array.isArray(response)
    ? (response as PaperMetadata[])
    : [];
};

/* ============================================================
   Module 8 — Research Gap and Ideation
   ============================================================ */

export const analyzeIdeation = (data: {
  paper_ids: string[];
  topic?: string;
  idea_count?: number;
}): Promise<IdeationResponse> =>
  api<IdeationResponse>(
    "/ideation/analyze",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
  );

/* ============================================================
   Legacy Manuscript Composer
   ============================================================ */

export const createSectionPlan = (data: {
  paper_ids: string[];
  section_type:
    | "related_work"
    | "methodology";
  research_topic?: string;
  target_word_count?: number;
}): Promise<SectionPlanResponse> =>
  api<SectionPlanResponse>(
    "/manuscript/plan",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
  );

export const generateManuscriptSection = (data: {
  paper_ids: string[];
  section_type:
    | "related_work"
    | "methodology";
  research_topic?: string;
  target_word_count?: number;
  sentence_plan?: SentencePlan[];
}): Promise<DraftSectionResponse> =>
  api<DraftSectionResponse>(
    "/manuscript/generate",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
  );

/* ============================================================
   Module 9 — Research Workspace
   ============================================================ */

export const createWorkspace = (data: {
  title: string;
  description?: string;
  paper_ids: string[];
  idea: ResearchIdea;
  research_objective?: string;
  document_format?: DocumentFormat;
}): Promise<Workspace> =>
  api<Workspace>(
    "/workspaces",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
  );

export const getWorkspaces = (): Promise<Workspace[]> =>
  api<Workspace[]>("/workspaces");

export const getWorkspace = (
  workspaceId: string,
): Promise<Workspace> =>
  api<Workspace>(`/workspaces/${workspaceId}`);

export const updateWorkspace = (
  workspaceId: string,
  data: Partial<{
    title: string;
    description: string;
    paper_ids: string[];
    idea: ResearchIdea;
    research_objective: string;
    document_format: DocumentFormat;
  }>,
): Promise<Workspace> =>
  api<Workspace>(
    `/workspaces/${workspaceId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
  );

export const generateWorkspaceContent = (
  workspaceId: string,
  data: {
    content_type: WorkspaceContentType;
    target_word_count?: number;
    generate_latex?: boolean;
    citation_style?: "internal" | "latex";
    instructions?: string;
    document_format?: DocumentFormat;
  },
): Promise<WorkspaceGenerationResponse> =>
  api<WorkspaceGenerationResponse>(
    `/workspaces/${workspaceId}/generate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
  );

export const saveWorkspaceVersion = (
  workspaceId: string,
  data: {
    content_type: WorkspaceContentType;
    content_markdown: string;
    latex_code: string;
    citations?: WorkspaceCitation[];
    warnings?: string[];
    source_chunk_ids?: string[];
    document_format?: DocumentFormat;
  },
): Promise<WorkspaceVersion> =>
  api<WorkspaceVersion>(
    `/workspaces/${workspaceId}/versions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
  );

export const getWorkspaceVersions = (
  workspaceId: string,
): Promise<WorkspaceVersion[]> =>
  api<WorkspaceVersion[]>(
    `/workspaces/${workspaceId}/versions`,
  );

/* ============================================================
   Module 9 — LaTeX Workspace
   ============================================================ */

function getCompileErrorMessage(
  data: unknown,
  fallback: string,
): string {
  if (
    typeof data === "object" &&
    data !== null &&
    "detail" in data
  ) {
    const detail = data.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (
      typeof detail === "object" &&
      detail !== null &&
      "message" in detail &&
      typeof detail.message === "string"
    ) {
      return detail.message;
    }
  }

  return fallback;
}

export async function compileWorkspaceLatexStatus(
  workspaceId: string,
  latexCode: string,
  referencesBib = "",
  documentFormat: DocumentFormat = "normal",
): Promise<WorkspaceLatexCompileStatusResponse> {
  const response = await fetch(
    `${API_BASE}/workspaces/${workspaceId}/latex/compile/status`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        latex_code: latexCode,
        references_bib: referencesBib,
        document_format: documentFormat,
      }),
      cache: "no-store",
    },
  );

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      getCompileErrorMessage(
        data,
        "Unable to check LaTeX compilation status.",
      ),
    );
  }

  return data as WorkspaceLatexCompileStatusResponse;
}

export async function compileWorkspaceLatexPdf(
  workspaceId: string,
  latexCode: string,
  referencesBib = "",
  documentFormat: DocumentFormat = "normal",
): Promise<Blob> {
  const response = await fetch(
    `${API_BASE}/workspaces/${workspaceId}/latex/compile`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        latex_code: latexCode,
        references_bib: referencesBib,
        document_format: documentFormat,
      }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);

    throw new Error(
      getCompileErrorMessage(
        data,
        "LaTeX compilation failed.",
      ),
    );
  }

  return response.blob();
}