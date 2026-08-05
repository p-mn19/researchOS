export type PaperStatus = "uploaded" | "parsed" | "indexed" | "extracted";

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
  section_title?: string;
  page?: number;
  text: string;
  score?: number;
}

export interface CompareRow {
  field: string;
  values: Record<string, string>;
}