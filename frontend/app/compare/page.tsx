"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import {
  getPapers,
  comparePapers,
  searchGlobalLiterature,
} from "@/lib/api";
import {
  CompareRow,
  Paper,
  PaperMetadata,
} from "@/lib/types";
import {
  GitCompareArrows,
  CheckCircle2,
  ExternalLink,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from "lucide-react";
import { CompareTable } from "@/components/compare/compare_table";


// =========================================================
// HELPERS
// =========================================================

function cleanText(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value)
    .replace(/\s+/g, " ")
    .trim();
}


function getPaperTitle(
  paper: Paper
): string {
  return (
    cleanText(paper.title) ||
    cleanText(paper.filename) ||
    "Untitled paper"
  );
}


function getPaperAuthors(
  paper: Paper
): string {
  if (!paper.authors?.length) {
    return "Authors unavailable";
  }

  const authors = paper.authors
    .map((author) => cleanText(author))
    .filter(Boolean);

  if (authors.length <= 3) {
    return authors.join(", ");
  }

  return `${authors.slice(0, 3).join(", ")} + ${
    authors.length - 3
  } more`;
}


function getPaperUrl(
  paper: PaperMetadata
): string | undefined {
  return (
    paper.pdf_url ||
    undefined
  );
}


// =========================================================
// QUERY BUILDING
// =========================================================

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
  "using",
]);


function tokenize(
  text: string
): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .split(/\s+/)
    .filter(
      (word) =>
        word.length >= 4 &&
        !STOP_WORDS.has(word)
    );
}


function unique(
  values: string[]
): string[] {
  return [...new Set(values)];
}


function buildComparisonQuery(
  papers: Paper[],
  rows: CompareRow[]
): string {

  const terms: string[] = [];

  // -------------------------------------------------------
  // Paper titles
  // -------------------------------------------------------

  for (const paper of papers) {
    terms.push(
      ...tokenize(
        getPaperTitle(paper)
      )
    );
  }

  // -------------------------------------------------------
  // Abstracts
  // -------------------------------------------------------

  for (const paper of papers) {

    if (paper.abstract) {

      terms.push(
        ...tokenize(
          paper.abstract
        ).slice(0, 12)
      );
    }
  }

  // -------------------------------------------------------
  // Existing paper-level fields
  // -------------------------------------------------------

  for (const paper of papers) {

    if (paper.methodology) {

      terms.push(
        ...tokenize(
          paper.methodology
        ).slice(0, 10)
      );
    }

    if (paper.dataset) {

      terms.push(
        ...tokenize(
          paper.dataset
        ).slice(0, 10)
      );
    }
  }

  // -------------------------------------------------------
  // Comparison results
  //
  // This adds fields such as:
  // evaluation metric
  // limitations
  // future work
  // -------------------------------------------------------

  for (const row of rows) {

    if (
      row.field === "Methodology" ||
      row.field === "Dataset" ||
      row.field === "Evaluation Metric"
    ) {

      for (
        const value of Object.values(
          row.values
        )
      ) {

        if (
          typeof value === "string"
        ) {

          terms.push(
            ...tokenize(value)
              .slice(0, 12)
          );
        }
      }
    }
  }

  const uniqueTerms =
    unique(terms);

  /*
   * Keep the query comfortably below
   * the backend's 300-character limit.
   *
   * Prefer the first meaningful concepts
   * because titles/methodology/dataset are
   * generally more useful for discovery.
   */

  let query =
    uniqueTerms.join(" ");

  if (query.length > 280) {

    query =
      query.slice(0, 280);

    /*
     * Avoid cutting a word in half.
     */
    const lastSpace =
      query.lastIndexOf(" ");

    if (lastSpace > 0) {
      query =
        query.slice(0, lastSpace);
    }
  }

  return query.trim();
}


// =========================================================
// RECOMMENDATION REASON
// =========================================================

function getRecommendationReason(
  paper: PaperMetadata,
  query: string
): string {

  const title =
    cleanText(
      paper.title
    ).toLowerCase();

  const abstract =
    cleanText(
      paper.abstract
    ).toLowerCase();

  const queryTerms =
    unique(
      tokenize(query)
    );

  const titleMatches =
    queryTerms.filter(
      (term) =>
        title.includes(term)
    );

  const abstractMatches =
    queryTerms.filter(
      (term) =>
        !title.includes(term) &&
        abstract.includes(term)
    );

  const uniqueTitleMatches =
    unique(titleMatches)
      .slice(0, 3);

  const uniqueAbstractMatches =
    unique(abstractMatches)
      .slice(0, 3);

  if (
    uniqueTitleMatches.length >= 3
  ) {

    return (
      `Directly related to the compared papers through shared focus on ` +
      `${uniqueTitleMatches.join(", ")}.`
    );
  }

  if (
    uniqueTitleMatches.length === 2
  ) {

    return (
      `Closely related through shared research focus on ` +
      `${uniqueTitleMatches[0]} and ${uniqueTitleMatches[1]}.`
    );
  }

  if (
    uniqueTitleMatches.length === 1
  ) {

    if (
      uniqueAbstractMatches.length > 0
    ) {

      return (
        `Shares a direct focus on ` +
        `${uniqueTitleMatches[0]}, with additional overlap in ` +
        `${uniqueAbstractMatches[0]}.`
      );
    }

    return (
      `Shares a direct research focus on ` +
      `${uniqueTitleMatches[0]}.`
    );
  }

  if (
    uniqueAbstractMatches.length >= 3
  ) {

    return (
      `Related through research concepts including ` +
      `${uniqueAbstractMatches.join(", ")}.`
    );
  }

  if (
    uniqueAbstractMatches.length === 2
  ) {

    return (
      `Related through shared concepts around ` +
      `${uniqueAbstractMatches[0]} and ` +
      `${uniqueAbstractMatches[1]}.`
    );
  }

  if (
    uniqueAbstractMatches.length === 1
  ) {

    return (
      `Related through its research focus on ` +
      `${uniqueAbstractMatches[0]}.`
    );
  }

  return (
    "Selected as related literature based on " +
    "the research themes represented across the compared papers."
  );
}


// =========================================================
// RECOMMENDED LITERATURE
// =========================================================

function RecommendedLiterature({
  papers,
  loading,
  query,
}: {
  papers: PaperMetadata[];
  loading: boolean;
  query: string;
}) {

  const [
    scrollContainer,
    setScrollContainer,
  ] = useState<HTMLDivElement | null>(
    null
  );


  const scroll = (
    direction: "left" | "right"
  ) => {

    if (!scrollContainer) {
      return;
    }

    scrollContainer.scrollBy({
      left:
        direction === "left"
          ? -390
          : 390,
      behavior: "smooth",
    });
  };


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
              Related Literature
            </h2>

            <p className="mt-1 text-sm leading-6 text-slate-500">
              Literature discovered from the combined
              research themes of the compared papers.
            </p>

          </div>

        </div>


        {!loading &&
          papers.length > 1 && (

            <div className="hidden gap-2 sm:flex">

              <button
                type="button"
                onClick={() =>
                  scroll("left")
                }
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                aria-label="Previous related papers"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={() =>
                  scroll("right")
                }
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                aria-label="Next related papers"
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
                className="flex min-h-[410px] min-w-[340px] max-w-[340px] shrink-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5"
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

                  <div className="h-3 w-4/6 animate-pulse rounded bg-slate-200" />

                </div>

                <div className="mt-auto h-11 animate-pulse rounded-xl bg-slate-200" />

              </div>
            )
          )}

        </div>

      ) : (

        <div
          ref={setScrollContainer}
          className="mt-6 flex gap-5 overflow-x-auto scroll-smooth pb-4 [scrollbar-width:thin]"
        >

          {papers.map(
            (paper, index) => {

              const title =
                cleanText(
                  paper.title
                ) ||
                "Untitled paper";

              const url =
                getPaperUrl(
                  paper
                );

              const reason =
                getRecommendationReason(
                  paper,
                  query
                );

              return (

                <article
                  key={`${paper.source}-${paper.source_id}-${index}`}
                  className="flex min-h-[410px] min-w-[340px] max-w-[340px] shrink-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5 transition duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white hover:shadow-md"
                >

                  {/* ===================================== */}
                  {/* ICON */}
                  {/* ===================================== */}

                  <div className="flex items-start justify-between">

                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-slate-600 shadow-sm">
                      <BookOpen className="h-4 w-4" />
                    </div>

                    {url && (

                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
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
                  {/* SOURCE / YEAR */}
                  {/* ===================================== */}

                  <div className="mt-3 flex min-h-[28px] flex-wrap gap-2 text-xs">

                    {paper.source && (

                      <span className="rounded-full bg-white px-2.5 py-1 font-medium text-slate-600 shadow-sm">
                        {paper.source}
                      </span>

                    )}

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
                    {paper.authors?.length
                      ? paper.authors
                          .slice(0, 3)
                          .join(", ")
                      : "Authors unavailable"}
                  </p>


                  {/* ===================================== */}
                  {/* WHY RECOMMENDED */}
                  {/* ===================================== */}

                  <div className="mt-4 rounded-xl border border-violet-100 bg-violet-50 p-3.5">

                    <div className="flex items-center gap-2">

                      <Sparkles className="h-3.5 w-3.5 text-violet-600" />

                      <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">
                        Why relevant
                      </p>

                    </div>

                    <p className="mt-2 line-clamp-4 text-xs leading-5 text-violet-900">
                      {reason}
                    </p>

                  </div>


                  {/* ===================================== */}
                  {/* BUTTON */}
                  {/* ===================================== */}

                  <div className="mt-auto pt-5">

                    {url ? (

                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex min-h-[42px] w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
                      >

                        <span className="text-white">
                          Read paper
                        </span>

                        <ExternalLink className="h-4 w-4 text-white" />

                      </a>

                    ) : (

                      <div className="flex min-h-[42px] w-full items-center justify-center rounded-xl bg-slate-200 px-4 py-2.5 text-sm font-medium text-slate-500">
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


      {!loading &&
        papers.length > 0 && (

          <p className="mt-1 text-xs text-slate-400">
            Swipe horizontally to explore related papers.
          </p>

        )}

    </section>
  );
}


// =========================================================
// MAIN PAGE
// =========================================================

export default function ComparePage() {

  const [papers, setPapers] =
    useState<Paper[]>([]);

  const [selected, setSelected] =
    useState<string[]>([]);

  const [rows, setRows] =
    useState<CompareRow[]>([]);

  const [loadingPapers, setLoadingPapers] =
    useState(true);

  const [loadingCompare, setLoadingCompare] =
    useState(false);

  const [loadingRecommendations, setLoadingRecommendations] =
    useState(false);

  const [recommendedPapers, setRecommendedPapers] =
    useState<PaperMetadata[]>([]);

  const [recommendationQuery, setRecommendationQuery] =
    useState("");

  const [error, setError] =
    useState("");

  const [
    recommendationError,
    setRecommendationError,
  ] = useState("");


  // =======================================================
  // LOAD PAPERS
  // =======================================================

  useEffect(() => {

    async function load() {

      try {

        setLoadingPapers(true);
        setError("");

        const data =
          await getPapers();

        setPapers(data);

      } catch (err) {

        console.error(err);

        setError(
          "Failed to load papers."
        );

      } finally {

        setLoadingPapers(false);

      }
    }

    load();

  }, []);


  // =======================================================
  // TOGGLE PAPER
  // =======================================================

  function togglePaper(
    id: string
  ) {

    setSelected(
      (prev) =>
        prev.includes(id)
          ? prev.filter(
              (p) => p !== id
            )
          : [
              ...prev,
              id,
            ].slice(0, 4)
    );

    // Clear previous comparison/recommendations
    // when the selection changes.
    setRows([]);
    setRecommendedPapers([]);
    setRecommendationQuery("");
    setRecommendationError("");
  }


  // =======================================================
  // SELECTED PAPERS
  // =======================================================

  const selectedPapers =
    useMemo(
      () =>
        papers.filter(
          (paper) =>
            selected.includes(
              paper.id
            )
        ),
      [
        papers,
        selected,
      ]
    );


  // =======================================================
  // GENERATE RECOMMENDATIONS
  // =======================================================

  async function generateRecommendations(
    comparedPapers: Paper[],
    comparisonRows: CompareRow[]
  ) {

    if (
      comparedPapers.length < 2
    ) {
      return;
    }

    const query =
      buildComparisonQuery(
        comparedPapers,
        comparisonRows
      );

    if (!query) {
      return;
    }

    try {

      setLoadingRecommendations(true);
      setRecommendationError("");
      setRecommendationQuery(query);

      console.log(
        "[Comparison Discovery] Query:",
        query
      );

      const results =
        await searchGlobalLiterature(
          query,
          8
        );

      // ---------------------------------------------------
      // Remove papers that are already being compared.
      // ---------------------------------------------------

      const selectedTitles =
        new Set(
          comparedPapers.map(
            (paper) =>
              cleanText(
                paper.title
              ).toLowerCase()
          )
        );

      const filtered =
        results.filter(
          (paper) =>
            !selectedTitles.has(
              cleanText(
                paper.title
              ).toLowerCase()
            )
        );

      setRecommendedPapers(
        filtered
      );

      console.log(
        "[Comparison Discovery] Results:",
        filtered
      );

    } catch (err) {

      console.error(
        "[Comparison Discovery] Failed:",
        err
      );

      setRecommendedPapers([]);

      setRecommendationError(
        "Related literature could not be loaded."
      );

    } finally {

      setLoadingRecommendations(
        false
      );
    }
  }


  // =======================================================
  // COMPARE
  // =======================================================

  async function handleCompare() {

    if (
      selected.length < 2
    ) {

      setError(
        "Select at least 2 papers to compare."
      );

      return;
    }

    try {

      setLoadingCompare(true);
      setError("");

      setRows([]);
      setRecommendedPapers([]);
      setRecommendationQuery("");
      setRecommendationError("");

      const data =
        await comparePapers(
          selected
        );

      setRows(
        data.rows
      );

      // ---------------------------------------------------
      // Immediately search literature based on the
      // combined characteristics of the compared papers.
      // ---------------------------------------------------

      await generateRecommendations(
        selectedPapers,
        data.rows
      );

    } catch (err) {

      console.error(err);

      setError(
        "Comparison failed."
      );

    } finally {

      setLoadingCompare(false);

    }
  }


  // =======================================================
  // RENDER
  // =======================================================

  return (
    <AppShell>

      <div className="space-y-8">

        {/* ================================================= */}
        {/* PAPER SELECTION */}
        {/* ================================================= */}

        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">

          <div className="mb-6 flex items-start justify-between gap-4">

            <div>

              <div className="mb-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                Cross-paper analysis
              </div>

              <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
                Compare research papers side by side
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Select papers to compare methods,
                datasets, metrics, baselines, and
                limitations in one structured view.
              </p>

            </div>


            <div className="hidden rounded-2xl bg-slate-50 p-3 md:block">

              <GitCompareArrows className="h-8 w-8 text-blue-600" />

            </div>

          </div>


          {/* ================================================= */}
          {/* ERROR */}
          {/* ================================================= */}

          {error ? (

            <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>

          ) : null}


          {/* ================================================= */}
          {/* PAPER CARDS */}
          {/* ================================================= */}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">

            {loadingPapers ? (

              <div className="text-sm text-slate-500">
                Loading papers...
              </div>

            ) : papers.length === 0 ? (

              <div className="text-sm text-slate-500">
                No papers available for comparison.
              </div>

            ) : (

              papers.map(
                (paper) => {

                  const active =
                    selected.includes(
                      paper.id
                    );

                  return (

                    <button
                      key={paper.id}
                      type="button"
                      onClick={() =>
                        togglePaper(
                          paper.id
                        )
                      }
                      className={`min-w-0 rounded-2xl border p-5 text-left transition ${
                        active
                          ? "border-blue-200 bg-blue-50 ring-1 ring-blue-100"
                          : "border-slate-200 bg-white hover:border-blue-100 hover:bg-slate-50"
                      }`}
                    >

                      <div className="flex min-w-0 items-start justify-between gap-3">

                        <div className="min-w-0 flex-1">

                          <h3 className="line-clamp-2 break-words text-base font-semibold text-slate-900">
                            {getPaperTitle(
                              paper
                            )}
                          </h3>

                          <p className="mt-2 break-all text-sm text-slate-500">
                            {paper.filename}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            {paper.year ||
                              "Year unavailable"}
                          </p>

                        </div>


                        {active && (

                          <CheckCircle2 className="h-5 w-5 shrink-0 text-blue-600" />

                        )}

                      </div>

                    </button>
                  );
                }
              )

            )}

          </div>


          {/* ================================================= */}
          {/* COMPARE BUTTON */}
          {/* ================================================= */}

          <div className="mt-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">

            <p className="text-sm text-slate-500">

              Selected:{" "}

              <span className="font-semibold text-slate-900">
                {selected.length}
              </span>

              {" "} / 4

            </p>


            <button
              type="button"
              onClick={handleCompare}
              disabled={
                selected.length < 2 ||
                loadingCompare
              }
              className="inline-flex items-center justify-center rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >

              {loadingCompare
                ? "Generating comparison..."
                : "Compare selected papers"}

            </button>

          </div>

        </section>


        {/* ================================================= */}
        {/* COMPARISON TABLE */}
        {/* ================================================= */}

        <CompareTable
          rows={rows}
          selectedPapers={
            selectedPapers
          }
        />


        {/* ================================================= */}
        {/* RECOMMENDED LITERATURE */}
        {/* ================================================= */}

        {rows.length > 0 && (

          <RecommendedLiterature
            papers={
              recommendedPapers
            }
            loading={
              loadingRecommendations
            }
            query={
              recommendationQuery
            }
          />

        )}


        {/* ================================================= */}
        {/* RECOMMENDATION ERROR */}
        {/* ================================================= */}

        {recommendationError &&
          !loadingRecommendations && (

            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              {recommendationError}
            </div>

          )}

      </div>

    </AppShell>
  );
}