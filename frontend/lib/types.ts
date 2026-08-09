export type PaperStatus =
  | "uploaded"
  | "parsed"
  | "indexed"
  | "extracted";

export interface Paper {
  id: string;
  title: string;
  filename: string;
  authors?: string[];
  year?: number | null;
  abstract?: string;
  uploaded_at?: string;
  status: PaperStatus;
  methodology?: string;
  dataset?: string;
  limitations?: string;
}

export interface Extraction {
  objective?: string;
  methodology?: string;
  dataset?: string;
  evaluation_metric?: string;
  limitations?: string;
  future_work?: string;
}

export interface ChunkResult {
  id: string;
  section_title?: string;
  page?: number;
  text: string;
  score?: number;
}

export interface CompareRow {
  field: string;
  values: Record<string, string>;
}

export interface SearchResult {
  paper_id: string;
  paper_title: string;
  filename?: string;
  section_title?: string;
  page?: number;
  text: string;
  score?: number;
}

export interface SemanticSearchResponse {
  query: string;
  count: number;
  results: SearchResult[];
}

export interface ReviewDimension {
  id: string;
  title: string;
  score: string;
  concern: "None" | "Moderate" | "Major" | "Critical";
  evidence: string;
  suggestion: string;
}

export interface ReviewReport {
  paperId: string;
  paperTitle: string;
  overallScore: string;
  summary: string;
  dimensions: ReviewDimension[];
}