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

  uploaded_at?: string | null;
  parsed_at?: string | null;
  indexed_at?: string | null;
  extracted_at?: string | null;
  updated_at?: string | null;

  status: PaperStatus;

  // Structured extraction fields
  objective?: string | null;
  methodology?: string | null;
  dataset?: string | null;
  evaluation_metric?: string | null;
  limitations?: string | null;
  future_work?: string | null;
  research_gap?: string | null;
  findings?: string | null;
  keywords?: string[];
}


export interface Extraction {
  paper_id?: string;

  objective?: string | null;
  methodology?: string | null;
  dataset?: string | null;
  evaluation_metric?: string | null;
  limitations?: string | null;
  future_work?: string | null;

  // Module 8 and Module 9 fields
  research_gap?: string | null;
  findings?: string | null;
  keywords?: string[];

  updated_at?: string | null;
}


export interface SearchMetadata {
  research_gap?: string | null;
  limitations?: string | null;
  methodology?: string | null;
  findings?: string | null;
  future_work?: string | null;
  keywords?: string[];
}


export interface ChunkResult {
  id: string;
  paper_id?: string;
  paper_title?: string;
  filename?: string | null;

  section_title?: string | null;
  page?: number | null;
  page_number?: number | null;

  text: string;
  score?: number;

  metadata?: SearchMetadata | null;
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

  // Optional expanded review data
  research_gap?: string;
  findings?: string;
  future_work?: string;
  limitations?: string;
  methodology?: string;
}


export type IdeationEvidencePaper = {
  paper_id: string;
  title: string;
  limitation?: string | null;
  future_work?: string | null;
  research_gap?: string | null;
  methodology?: string | null;
};


export type ResearchIdea = {
  title: string;
  problem_statement: string;
  hypothesis: string;
  recommended_methodology: string;
  expected_contribution: string;
  evidence_paper_ids: string[];
};


export type IdeationResponse = {
  corpus_size: number;
  topic?: string | null;
  recurring_limitations: string[];
  research_gaps: string[];
  recommended_methodologies: string[];
  ideas: ResearchIdea[];
  evidence_papers: IdeationEvidencePaper[];
  model: string;
};


export type SentencePlan = {
  sentence_number: number;
  purpose: string;
  claim: string;
  citation_paper_ids: string[];
};


export type CitationSource = {
  paper_id: string;
  title: string;
  authors: string[];
  year?: number | null;
  section_title?: string | null;
  page?: number | null;
  evidence?: string | null;
};


export type SectionPlanResponse = {
  section_type: "related_work" | "methodology";
  section_title: string;
  objective: string;
  sentence_plan: SentencePlan[];
  recommended_sources: CitationSource[];
  model: string;
};


export type DraftSectionResponse = {
  section_type: "related_work" | "methodology";
  section_title: string;
  markdown: string;
  citations: CitationSource[];
  model: string;
};