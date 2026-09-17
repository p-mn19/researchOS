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
  year?: number;
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
  paper_id?: string;
  paper_title?: string;
  section_title?: string | null;
  page?: number | null;
  page_number?: number | null;
  text: string;
  score?: number;
}

export interface CompareRow {
  field: string;
  values: Record<string, string | number | null | undefined>;
}

export interface AnswerSource {
  source_number?: number;
  paper_title?: string;
  page?: number;
  section_title?: string;
  score?: number;
}

export interface PaperAnswer {
  paper_id: string;
  question: string;
  answer: string;
  sources: AnswerSource[];
  model?: string;
}

export interface LiteraturePaper {
  source: string;
  source_id: string;
  title: string;
  abstract: string;
  authors: string[];
  year?: number | null;
  doi?: string | null;
  pdf_url?: string | null;
  citation_count?: number;
  venue?: string | null;
}

export interface PaperMetadata extends LiteraturePaper {}

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
