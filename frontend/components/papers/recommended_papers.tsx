"use client";

import {
  ExternalLink,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from "lucide-react";

import { PaperMetadata } from "@/lib/types";

type RecommendedPapersProps = {
  papers: PaperMetadata[];
  loading?: boolean;
  query?: string;
  title?: string;
  description?: string;
  scrollId?: string;
};

// ---------------------------------------------------------
// BASIC HELPERS
// ---------------------------------------------------------

function getPaperTitle(paper: PaperMetadata): string {
  return paper.title?.trim() || "Untitled paper";
}

function getAuthors(paper: PaperMetadata): string {
  if (!paper.authors) {
    return "Authors unavailable";
  }

  if (Array.isArray(paper.authors)) {
    const authors = paper.authors
      .map((author) => String(author).trim())
      .filter(Boolean);

    if (authors.length === 0) {
      return "Authors unavailable";
    }

    if (authors.length <= 3) {
      return authors.join(", ");
    }

    return `${authors.slice(0, 3).join(", ")} + ${
      authors.length - 3
    } more`;
  }

  return String(paper.authors);
}

function getPaperUrl(
  paper: PaperMetadata
): string | undefined {
  return paper.pdf_url || undefined;
}


// ---------------------------------------------------------
// TEXT PROCESSING
// ---------------------------------------------------------

const STOP_WORDS = new Set([
  "this",
  "that",
  "these",
  "those",
  "with",
  "from",
  "using",
  "used",
  "into",
  "their",
  "they",
  "them",
  "were",
  "have",
  "has",
  "been",
  "being",
  "which",
  "where",
  "when",
  "than",
  "such",
  "also",
  "paper",
  "study",
  "research",
  "method",
  "methods",
  "approach",
  "based",
  "results",
  "result",
  "data",
  "dataset",
  "model",
  "models",
  "performance",
  "analysis",
  "proposed",
  "developed",
  "development",
  "investigate",
  "investigates",
  "investigating",
  "evaluate",
  "evaluated",
  "evaluation",
  "classification",
  "classifying",
  "detection",
  "using",
]);

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .split(/\s+/)
    .map((word) => word.trim())
    .filter(
      (word) =>
        word.length >= 4 &&
        !STOP_WORDS.has(word)
    );
}

function unique<T>(items: T[]): T[] {
  return [...new Set(items)];
}

function getResearchTerms(query: string): string[] {
  return unique(tokenize(query));
}


// ---------------------------------------------------------
// WHY RECOMMENDED
// ---------------------------------------------------------

function getReason(
  paper: PaperMetadata,
  query: string
): string {

  const title = getPaperTitle(paper);

  const abstract =
    typeof paper.abstract === "string"
      ? paper.abstract
      : "";

  const queryTerms = getResearchTerms(query);

  if (queryTerms.length === 0) {
    return "Related to the research topic and extracted concepts of your paper.";
  }

  const titleTerms = new Set(
    tokenize(title)
  );

  const abstractTerms = new Set(
    tokenize(abstract)
  );

  const titleMatches = queryTerms.filter(
    (term) => titleTerms.has(term)
  );

  const abstractMatches = queryTerms.filter(
    (term) =>
      !titleTerms.has(term) &&
      abstractTerms.has(term)
  );

  const matches = unique([
    ...titleMatches,
    ...abstractMatches,
  ]);

  // -------------------------------------------------------
  // Strong title overlap
  // -------------------------------------------------------

  if (titleMatches.length >= 3) {

    const concepts = titleMatches
      .slice(0, 3)
      .join(", ");

    return `Closely related to your research through shared focus on ${concepts}.`;
  }

  if (titleMatches.length === 2) {

    return `Shares a strong research focus with your paper around ${titleMatches[0]} and ${titleMatches[1]}.`;
  }

  if (titleMatches.length === 1) {

    const term = titleMatches[0];

    if (abstractMatches.length > 0) {

      return `Shares the research focus on ${term}, with related concepts discussed in the paper's abstract.`;
    }

    return `Shares a direct research focus on ${term}.`;
  }

  // -------------------------------------------------------
  // Abstract overlap
  // -------------------------------------------------------

  if (abstractMatches.length >= 3) {

    const concepts = abstractMatches
      .slice(0, 3)
      .join(", ");

    return `Related through several research concepts, including ${concepts}.`;
  }

  if (abstractMatches.length === 2) {

    return `Related through shared research concepts around ${abstractMatches[0]} and ${abstractMatches[1]}.`;
  }

  if (abstractMatches.length === 1) {

    return `Related through its research focus on ${abstractMatches[0]}.`;
  }

  // -------------------------------------------------------
  // Fallback
  // -------------------------------------------------------

  return "Identified as related literature based on the topic and concepts extracted from your paper.";
}


// ---------------------------------------------------------
// SOURCE LABEL
// ---------------------------------------------------------

function getSourceLabel(
  source?: string
): string {

  if (!source) {
    return "Literature";
  }

  if (
    source.toLowerCase() === "openalex"
  ) {
    return "OpenAlex";
  }

  if (
    source.toLowerCase() === "arxiv"
  ) {
    return "arXiv";
  }

  return source;
}


// ---------------------------------------------------------
// COMPONENT
// ---------------------------------------------------------

export function RecommendedPapers({
  papers,
  loading = false,
  query = "",
  title = "Recommended Literature",
  description = "Related research discovered from your extracted paper.",
  scrollId = "recommended-papers-scroll",
}: RecommendedPapersProps) {

  const scroll = (
    direction: "left" | "right"
  ) => {

    const container =
      document.getElementById(scrollId);

    if (!container) {
      return;
    }

    container.scrollBy({
      left:
        direction === "left"
          ? -380
          : 380,
      behavior: "smooth",
    });
  };


  // -------------------------------------------------------
  // EMPTY STATE
  // -------------------------------------------------------

  if (
    !loading &&
    papers.length === 0
  ) {
    return null;
  }


  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">

      {/* ================================================= */}
      {/* HEADER */}
      {/* ================================================= */}

      <div className="flex items-start justify-between gap-4">

        <div className="flex items-start gap-3">

          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">

            <Sparkles className="h-5 w-5" />

          </div>

          <div>

            <h2 className="text-xl font-semibold text-slate-900">
              {title}
            </h2>

            <p className="mt-1 text-sm leading-5 text-slate-500">
              {description}
            </p>

          </div>

        </div>


        {/* ================================================= */}
        {/* NAVIGATION */}
        {/* ================================================= */}

        {!loading &&
          papers.length > 1 && (

            <div className="hidden gap-2 sm:flex">

              <button
                type="button"
                onClick={() =>
                  scroll("left")
                }
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                aria-label="Previous recommended papers"
              >

                <ChevronLeft className="h-4 w-4" />

              </button>


              <button
                type="button"
                onClick={() =>
                  scroll("right")
                }
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                aria-label="Next recommended papers"
              >

                <ChevronRight className="h-4 w-4" />

              </button>

            </div>
          )}

      </div>


      {/* ================================================= */}
      {/* LOADING */}
      {/* ================================================= */}

      {loading ? (

        <div className="mt-6 flex gap-5 overflow-hidden">

          {[1, 2, 3].map(
            (item) => (

              <div
                key={item}
                className="flex min-h-[420px] min-w-[340px] max-w-[340px] shrink-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5"
              >

                <div className="flex justify-between">

                  <div className="h-9 w-9 animate-pulse rounded-xl bg-slate-200" />

                  <div className="h-9 w-9 animate-pulse rounded-xl bg-slate-200" />

                </div>

                <div className="mt-5 h-5 w-4/5 animate-pulse rounded bg-slate-200" />

                <div className="mt-2 h-5 w-3/5 animate-pulse rounded bg-slate-200" />

                <div className="mt-5 h-6 w-2/5 animate-pulse rounded-full bg-slate-200" />

                <div className="mt-5 space-y-2">

                  <div className="h-3 w-full animate-pulse rounded bg-slate-200" />

                  <div className="h-3 w-5/6 animate-pulse rounded bg-slate-200" />

                </div>

                <div className="mt-auto h-12 animate-pulse rounded-xl bg-slate-200" />

              </div>

            )
          )}

        </div>

      ) : (

        /* ================================================= */
        /* PAPERS */
        /* ================================================= */

        <div
          id={scrollId}
          className="mt-6 flex gap-5 overflow-x-auto scroll-smooth pb-4 [scrollbar-width:thin]"
        >

          {papers.map(
            (paper, index) => {

              const title =
                getPaperTitle(paper);

              const url =
                getPaperUrl(paper);

              const reason =
                getReason(
                  paper,
                  query
                );

              const source =
                getSourceLabel(
                  paper.source
                );

              return (

                <article
                  key={`${paper.source || "paper"}-${paper.source_id || title}-${index}`}
                  className="flex min-h-[420px] min-w-[340px] max-w-[340px] shrink-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5 transition duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white hover:shadow-md"
                >

                  {/* ===================================== */}
                  {/* ICONS */}
                  {/* ===================================== */}

                  <div className="flex items-start justify-between gap-3">

                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-slate-600 shadow-sm">

                      <BookOpen className="h-4 w-4" />

                    </div>


                    {url && (

                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
                        aria-label={`Open ${title}`}
                      >

                        <ExternalLink className="h-4 w-4" />

                      </a>

                    )}

                  </div>


                  {/* ===================================== */}
                  {/* TITLE */}
                  {/* ===================================== */}

                  <h3 className="mt-4 line-clamp-3 min-h-[72px] text-base font-semibold leading-6 text-slate-900">
                    {title}
                  </h3>


                  {/* ===================================== */}
                  {/* SOURCE + YEAR */}
                  {/* ===================================== */}

                  <div className="mt-3 flex min-h-[28px] flex-wrap items-center gap-2 text-xs">

                    <span className="rounded-full bg-white px-2.5 py-1 font-medium text-slate-600 shadow-sm">
                      {source}
                    </span>

                    {paper.year && (

                      <span className="rounded-full bg-white px-2.5 py-1 text-slate-500 shadow-sm">
                        {paper.year}
                      </span>

                    )}

                  </div>


                  {/* ===================================== */}
                  {/* AUTHORS */}
                  {/* ===================================== */}

                  <p className="mt-4 line-clamp-2 min-h-[40px] text-xs leading-5 text-slate-500">
                    {getAuthors(paper)}
                  </p>


                  {/* ===================================== */}
                  {/* WHY RECOMMENDED */}
                  {/* ===================================== */}

                  <div className="mt-4 rounded-xl border border-violet-100 bg-violet-50 p-3.5">

                    <div className="flex items-center gap-2">

                      <Sparkles className="h-3.5 w-3.5 text-violet-600" />

                      <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">
                        Why recommended
                      </p>

                    </div>

                    <p className="mt-2 line-clamp-4 text-xs leading-5 text-violet-900">
                      {reason}
                    </p>

                  </div>


                  {/* ===================================== */}
                  {/* READ PAPER */}
                  {/* ===================================== */}

                  <div className="mt-auto pt-5">

                    {url ? (

                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
                      >

                        <span>
                          Read paper
                        </span>

                        <ExternalLink className="h-4 w-4" />

                      </a>

                    ) : (

                      <div className="flex w-full items-center justify-center rounded-xl bg-slate-200 px-4 py-2.5 text-sm font-medium text-slate-500">
                        Paper link unavailable
                      </div>

                    )}

                  </div>

                </article>

              );
            }
          )}

        </div>
      )}


      {/* ================================================= */}
      {/* FOOTER */}
      {/* ================================================= */}

      {!loading &&
        papers.length > 0 && (

          <p className="mt-1 text-xs text-slate-400">
            Swipe horizontally to explore related papers.
          </p>

        )}

    </section>
  );
}