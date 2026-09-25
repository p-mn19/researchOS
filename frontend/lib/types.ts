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


export interface PaperSearchResponse {
  query: string;
  top_k: number;
  count: number;
  results: ChunkResult[];
}


export interface CompareRow {
  field: string;
  values: Record<
    string,
    string | number | null | undefined
  >;
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


/* ============================================================
   Module 7 — Reviewer Simulation
   ============================================================ */

export type ReviewConcern =
  | "None"
  | "Moderate"
  | "Major"
  | "Critical";


export type ReviewConfidence =
  | "Low"
  | "Medium"
  | "High";


export interface ReviewDimension {
  id: string;
  title: string;

  /*
   * Score generated from the paper evidence by the
   * review model.
   */
  score: string;

  /*
   * Severity of the issue identified in this dimension.
   */
  concern: ReviewConcern;

  /*
   * Confidence reflects how strongly the available
   * paper evidence supports the assessment.
   */
  confidence: ReviewConfidence;

  /*
   * Evidence taken from the supplied paper context.
   */
  evidence: string;

  /*
   * Actionable improvement suggested from the
   * identified evidence/gap.
   */
  suggestion: string;
}


export interface ReviewReport {
  paperId: string;
  paperTitle: string;

  /*
   * Overall numerical assessment.
   * Example: "7.4/10"
   */
  overallScore: string;

  /*
   * Natural-language assessment generated from
   * the paper evidence.
   */
  overallAssessment: string;

  /*
   * Kept for compatibility with the existing
   * review frontend/backend structure.
   */
  summary: string;

  /*
   * Positive aspects identified from the paper.
   */
  strengths: string[];

  /*
   * Weaknesses or areas requiring improvement.
   */
  weaknesses: string[];

  /*
   * Information that is missing or insufficiently
   * supported in the available paper content.
   */
  missingInformation: string[];

  /*
   * Detailed assessment across the fixed review
   * dimensions.
   */
  dimensions: ReviewDimension[];

  /*
   * Backend model used for the review.
   */
  model?: string;
}


/* ============================================================
   Module 8 — Research Gap and Ideation
   ============================================================ */

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


/* ============================================================
   Legacy Manuscript Composer
   Kept only while old /manuscript routes exist.
   ============================================================ */

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
  section_type:
    | "related_work"
    | "methodology";

  section_title: string;
  objective: string;
  sentence_plan: SentencePlan[];
  recommended_sources: CitationSource[];
  model: string;
};


export type DraftSectionResponse = {
  section_type:
    | "related_work"
    | "methodology";

  section_title: string;
  markdown: string;
  citations: CitationSource[];
  model: string;
};


/* ============================================================
   Module 9 — Research Workspace
   ============================================================ */

export type WorkspaceContentType =
  | "introduction"
  | "research_problem"
  | "research_objectives"
  | "research_questions"
  | "hypotheses"
  | "related_work"
  | "methodology"
  | "proposed_framework"
  | "experimental_design"
  | "evaluation_plan"
  | "expected_contributions"
  | "limitations_and_scope"
  | "abstract_draft"
  | "conclusion";


export type WorkspaceIdea = ResearchIdea;


export interface Workspace {
  id: string;
  title: string;
  description: string;
  paper_ids: string[];
  idea: WorkspaceIdea;
  research_objective: string;
  created_at: string;
  updated_at: string;
}


export interface WorkspaceCitation {
  paper_id: string;
  title: string;
  authors: string[];
  year?: number | null;
  venue?: string | null;
  doi?: string | null;
  citation_key: string;
  section_title?: string | null;
  page?: number | null;
}


export interface WorkspaceGenerationResponse {
  workspace_id: string;
  content_type: WorkspaceContentType;
  title: string;
  content_markdown: string;
  latex_code: string;
  citations: WorkspaceCitation[];
  warnings: string[];
  source_chunk_ids: string[];
  model: string;
  bibtex: string;
}


export interface WorkspaceVersion {
  id: string;
  workspace_id: string;
  content_type: WorkspaceContentType;
  content_markdown: string;
  latex_code: string;
  citations: WorkspaceCitation[];
  warnings: string[];
  source_chunk_ids: string[];
  bibtex: string;
  version: number;
  created_at: string;
}