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
      `API ${response.status}: ${
        text || "Request failed"
      }`,
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
  api(`/papers/${id}/parse`, {
    method: "POST",
  });


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
   Compare and Review
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
  }>("/compare", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      paper_ids: paperIds,
    }),
  });


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
   These can be removed after the old manuscript service/routes
   are no longer used anywhere in the frontend.
   ============================================================ */

export const createSectionPlan = (data: {
  paper_ids: string[];
  section_type: "related_work" | "methodology";
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
  section_type: "related_work" | "methodology";
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
  api<Workspace>(
    `/workspaces/${workspaceId}`,
  );


export const updateWorkspace = (
  workspaceId: string,
  data: Partial<{
    title: string;
    description: string;
    paper_ids: string[];
    idea: ResearchIdea;
    research_objective: string;
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


export type GenerateWorkspaceSectionInput = {
  content_type: WorkspaceContentType;

  target_word_count?: number;
  generate_latex?: boolean;
  generate_bibtex?: boolean;

  citation_style?: "internal" | "latex";
  instructions?: string;
};


export type GenerateWorkspaceContentInput =
  GenerateWorkspaceSectionInput;


export const generateWorkspaceContent = (
  workspaceId: string,
  data: GenerateWorkspaceContentInput,
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

    bibtex?: string;
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
