"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/app_shell";
import { generateReview, getPapers } from "@/lib/api";
import {
  Paper,
  ReviewDimension,
  ReviewReport,
} from "@/lib/types";

import {
  AlertTriangle,
  Award,
  BookOpen,
  CheckCircle,
  ClipboardCheck,
  Info,
  Lightbulb,
  Loader2,
  Target,
  TrendingDown,
} from "lucide-react";


/* ============================================================
   Dimension Icons
   ============================================================ */

const dimensionIcons: Record<
  string,
  React.ReactNode
> = {
  clarity: (
    <BookOpen className="h-5 w-5 text-blue-500" />
  ),

  novelty: (
    <Lightbulb className="h-5 w-5 text-yellow-500" />
  ),

  methodology: (
    <AlertTriangle className="h-5 w-5 text-orange-500" />
  ),

  evidence: (
    <Target className="h-5 w-5 text-emerald-500" />
  ),

  limitations: (
    <TrendingDown className="h-5 w-5 text-violet-500" />
  ),
};


/* ============================================================
   Concern Styling
   ============================================================ */

function concernColor(
  concern: ReviewDimension["concern"],
) {
  if (concern === "Critical") {
    return "text-red-600";
  }

  if (concern === "Major") {
    return "text-orange-600";
  }

  if (concern === "Moderate") {
    return "text-yellow-600";
  }

  return "text-emerald-600";
}


function concernBadge(
  concern: ReviewDimension["concern"],
) {
  if (concern === "Critical") {
    return "border-red-200 bg-red-50 text-red-700";
  }

  if (concern === "Major") {
    return "border-orange-200 bg-orange-50 text-orange-700";
  }

  if (concern === "Moderate") {
    return "border-yellow-200 bg-yellow-50 text-yellow-700";
  }

  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}


/* ============================================================
   Confidence Styling
   ============================================================ */

function confidenceColor(
  confidence: ReviewDimension["confidence"],
) {
  if (confidence === "High") {
    return "text-emerald-600";
  }

  if (confidence === "Medium") {
    return "text-blue-600";
  }

  return "text-slate-500";
}


/* ============================================================
   Page
   ============================================================ */

export default function ReviewSimulationPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperId, setSelectedPaperId] =
    useState("");

  const [report, setReport] =
    useState<ReviewReport | null>(null);

  const [selectedDimension, setSelectedDimension] =
    useState<ReviewDimension | null>(null);

  const [loadingPapers, setLoadingPapers] =
    useState(true);

  const [loadingReview, setLoadingReview] =
    useState(false);

  const [error, setError] =
    useState("");


  /* ============================================================
     Load Papers
     ============================================================ */

  useEffect(() => {
    async function loadPapers() {
      try {
        setLoadingPapers(true);
        setError("");

        const data = await getPapers();

        setPapers(data);

        if (data.length > 0) {
          setSelectedPaperId(data[0].id);
        }
      } catch (err) {
        console.error(err);
        setError(
          "Could not load uploaded papers.",
        );
      } finally {
        setLoadingPapers(false);
      }
    }

    loadPapers();
  }, []);


  /* ============================================================
     Selected Paper
     ============================================================ */

  const selectedPaper = useMemo(
    () =>
      papers.find(
        (paper) =>
          paper.id === selectedPaperId,
      ),
    [
      papers,
      selectedPaperId,
    ],
  );


  /* ============================================================
     Generate Review
     ============================================================ */

  async function handleGenerateReview() {
    if (!selectedPaperId) {
      setError(
        "Select a paper first.",
      );

      return;
    }

    try {
      setLoadingReview(true);
      setError("");

      setReport(null);
      setSelectedDimension(null);

      const data =
        await generateReview(
          selectedPaperId,
        );

      setReport(data);

      if (
        data.dimensions &&
        data.dimensions.length > 0
      ) {
        setSelectedDimension(
          data.dimensions[0],
        );
      }
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Could not generate the review.",
      );
    } finally {
      setLoadingReview(false);
    }
  }


  /* ============================================================
     Render
     ============================================================ */

  return (
    <AppShell>
      <div className="min-h-full space-y-6 bg-slate-50 p-4 md:p-8">

        {/* ======================================================
            Header / Paper Selection
            ====================================================== */}

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">

          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">

            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                <ClipboardCheck className="h-3.5 w-3.5" />

                Research quality assistance
              </div>

              <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                Reviewer Simulation
              </h1>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Analyse an uploaded research paper using its
                extracted information and source text. ResearchOS
                evaluates clarity, contribution, methodology,
                evidence, and limitations.
              </p>
            </div>


            {/* Paper Selector */}

            <div className="w-full lg:max-w-md">

              <label
                htmlFor="paper-select"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Select paper to review
              </label>

              <select
                id="paper-select"
                value={selectedPaperId}
                onChange={(event) => {
                  setSelectedPaperId(
                    event.target.value,
                  );

                  setReport(null);
                  setSelectedDimension(null);
                  setError("");
                }}
                disabled={
                  loadingPapers ||
                  papers.length === 0
                }
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100"
              >
                {loadingPapers ? (
                  <option>
                    Loading papers...
                  </option>
                ) : papers.length === 0 ? (
                  <option>
                    No uploaded papers found
                  </option>
                ) : (
                  papers.map((paper) => (
                    <option
                      key={paper.id}
                      value={paper.id}
                    >
                      {
                        paper.title ||
                        paper.filename
                      }
                    </option>
                  ))
                )}
              </select>

            </div>
          </div>


          {/* Selected Paper */}

          {selectedPaper ? (
            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">

              <p className="break-words text-sm font-medium text-slate-900">
                {
                  selectedPaper.title ||
                  "Untitled paper"
                }
              </p>

              <p className="mt-1 break-all text-xs text-slate-500">
                {selectedPaper.filename}
              </p>

            </div>
          ) : null}


          {/* Error */}

          {error ? (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700">
              {error}
            </div>
          ) : null}


          {/* Generate Button */}

          <button
            type="button"
            onClick={handleGenerateReview}
            disabled={
              !selectedPaperId ||
              loadingReview ||
              loadingPapers
            }
            className="mt-5 inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loadingReview ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />

                Generating review...
              </>
            ) : (
              <>
                <ClipboardCheck className="h-4 w-4" />

                Generate review
              </>
            )}
          </button>

        </section>


        {/* ======================================================
            Empty State
            ====================================================== */}

        {!report &&
        !loadingReview ? (
          <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center">

            <ClipboardCheck className="mx-auto h-10 w-10 text-slate-300" />

            <h2 className="mt-4 text-lg font-semibold text-slate-800">
              No review generated yet
            </h2>

            <p className="mt-2 text-sm text-slate-500">
              Select a paper and generate a review
              based on the available research evidence.
            </p>

          </section>
        ) : null}


        {/* ======================================================
            REVIEW
            ====================================================== */}

        {report ? (
          <div className="flex flex-col gap-6 xl:flex-row">

            {/* ==================================================
                Main Review
                ================================================== */}

            <main className="min-w-0 flex-1 space-y-6">

              {/* =================================================
                  Overall Assessment
                  ================================================= */}

              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">

                <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">

                  <div className="min-w-0">

                    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-500">
                      ResearchOS Review Engine
                    </p>

                    <h2 className="break-words text-2xl font-semibold leading-8 text-slate-900">
                      {report.paperTitle}
                    </h2>

                  </div>


                  {/* Overall Score */}

                  <div className="inline-flex shrink-0 items-center gap-2 rounded-2xl border border-indigo-100 bg-indigo-50 px-5 py-3 font-semibold text-indigo-700">

                    <Award className="h-5 w-5" />

                    <span className="text-lg">
                      {report.overallScore}
                    </span>

                  </div>

                </div>


                {/* Overall Assessment */}

                <div className="mt-6 border-t border-slate-100 pt-6">

                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                    Overall assessment
                  </h3>

                  <p className="mt-3 text-sm leading-7 text-slate-700">
                    {
                      report.overallAssessment ||
                      report.summary
                    }
                  </p>

                </div>

              </section>


              {/* =================================================
                  Strengths / Weaknesses / Missing Information
                  ================================================= */}

              <section className="grid gap-4 lg:grid-cols-3">

                {/* Strengths */}

                <div className="rounded-2xl border border-emerald-200 bg-white p-5">

                  <div className="flex items-center gap-2">

                    <div className="rounded-lg bg-emerald-50 p-2">
                      <CheckCircle className="h-4 w-4 text-emerald-600" />
                    </div>

                    <h3 className="font-semibold text-slate-800">
                      Strengths
                    </h3>

                  </div>

                  {report.strengths?.length ? (
                    <ul className="mt-4 space-y-3">

                      {report.strengths.map(
                        (strength, index) => (
                          <li
                            key={index}
                            className="flex gap-2 text-sm leading-6 text-slate-600"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />

                            <span>
                              {strength}
                            </span>
                          </li>
                        ),
                      )}

                    </ul>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      No specific strengths were identified
                      from the supplied evidence.
                    </p>
                  )}

                </div>


                {/* Weaknesses */}

                <div className="rounded-2xl border border-orange-200 bg-white p-5">

                  <div className="flex items-center gap-2">

                    <div className="rounded-lg bg-orange-50 p-2">
                      <AlertTriangle className="h-4 w-4 text-orange-600" />
                    </div>

                    <h3 className="font-semibold text-slate-800">
                      Areas to improve
                    </h3>

                  </div>

                  {report.weaknesses?.length ? (
                    <ul className="mt-4 space-y-3">

                      {report.weaknesses.map(
                        (weakness, index) => (
                          <li
                            key={index}
                            className="flex gap-2 text-sm leading-6 text-slate-600"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" />

                            <span>
                              {weakness}
                            </span>
                          </li>
                        ),
                      )}

                    </ul>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      No specific weaknesses were identified
                      from the supplied evidence.
                    </p>
                  )}

                </div>


                {/* Missing Information */}

                <div className="rounded-2xl border border-blue-200 bg-white p-5">

                  <div className="flex items-center gap-2">

                    <div className="rounded-lg bg-blue-50 p-2">
                      <Info className="h-4 w-4 text-blue-600" />
                    </div>

                    <h3 className="font-semibold text-slate-800">
                      Missing information
                    </h3>

                  </div>

                  {report.missingInformation?.length ? (
                    <ul className="mt-4 space-y-3">

                      {report.missingInformation.map(
                        (item, index) => (
                          <li
                            key={index}
                            className="flex gap-2 text-sm leading-6 text-slate-600"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />

                            <span>
                              {item}
                            </span>
                          </li>
                        ),
                      )}

                    </ul>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      No major missing information was
                      identified from the supplied paper.
                    </p>
                  )}

                </div>

              </section>


              {/* =================================================
                  Review Dimensions
                  ================================================= */}

              <section>

                <div className="mb-4">

                  <h2 className="text-lg font-semibold text-slate-900">
                    Review dimensions
                  </h2>

                  <p className="mt-1 text-sm text-slate-500">
                    Select a dimension to inspect the evidence
                    and suggested improvement.
                  </p>

                </div>


                <div className="grid gap-4 md:grid-cols-2">

                  {report.dimensions.map(
                    (dimension) => (

                      <button
                        type="button"
                        key={dimension.id}
                        onClick={() =>
                          setSelectedDimension(
                            dimension,
                          )
                        }
                        className={`min-w-0 rounded-2xl border bg-white p-5 text-left transition ${
                          selectedDimension?.id ===
                          dimension.id
                            ? "border-indigo-500 bg-indigo-50/30 ring-1 ring-indigo-500"
                            : "border-slate-200 hover:border-indigo-300 hover:shadow-sm"
                        }`}
                      >

                        {/* Top */}

                        <div className="flex items-start justify-between gap-4">

                          <div className="flex min-w-0 items-start gap-3">

                            <span className="mt-0.5 shrink-0">
                              {
                                dimensionIcons[
                                  dimension.id
                                ] || (
                                  <CheckCircle className="h-5 w-5 text-emerald-500" />
                                )
                              }
                            </span>

                            <h3 className="break-words font-semibold leading-6 text-slate-800">
                              {dimension.title}
                            </h3>

                          </div>


                          <span className="shrink-0 text-lg font-bold text-slate-700">
                            {dimension.score}
                          </span>

                        </div>


                        {/* Concern + Confidence */}

                        <div className="mt-5 flex flex-wrap items-center gap-2">

                          <span className="text-xs font-medium text-slate-500">
                            Concern:
                          </span>

                          <span
                            className={`rounded-full border px-2.5 py-1 text-xs font-medium ${concernBadge(
                              dimension.concern,
                            )}`}
                          >
                            {dimension.concern}
                          </span>


                          <span className="ml-2 text-xs font-medium text-slate-500">
                            Confidence:
                          </span>

                          <span
                            className={`text-xs font-semibold ${confidenceColor(
                              dimension.confidence,
                            )}`}
                          >
                            {dimension.confidence}
                          </span>

                        </div>

                      </button>

                    ),
                  )}

                </div>

              </section>

            </main>


            {/* ==================================================
                Evidence Sidebar
                ================================================== */}

            <aside className="w-full xl:sticky xl:top-6 xl:w-96 xl:self-start">

              <section className="flex max-h-[calc(100vh-3rem)] min-h-[500px] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">

                {/* Sidebar Header */}

                <div className="border-b border-slate-100 bg-slate-50 p-5">

                  <h3 className="flex items-center gap-2 font-semibold text-slate-800">

                    <CheckCircle className="h-4 w-4 text-emerald-500" />

                    Evidence & suggestions

                  </h3>

                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    Grounded in the evidence supplied to
                    the review engine.
                  </p>

                </div>


                {/* Sidebar Content */}

                {selectedDimension ? (

                  <div className="flex-1 space-y-6 overflow-y-auto p-5">

                    {/* Selected Dimension */}

                    <div>

                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Selected dimension
                      </h4>

                      <p className="break-words text-lg font-semibold leading-7 text-slate-800">
                        {selectedDimension.title}
                      </p>

                    </div>


                    {/* Score / Concern / Confidence */}

                    <div className="flex flex-wrap gap-2">

                      <span className="rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700">
                        Score {selectedDimension.score}
                      </span>

                      <span
                        className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${concernBadge(
                          selectedDimension.concern,
                        )}`}
                      >
                        {selectedDimension.concern} concern
                      </span>

                      <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
                        {selectedDimension.confidence} confidence
                      </span>

                    </div>


                    {/* Evidence */}

                    <div>

                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Evidence / rationale
                      </h4>

                      <div className="break-words rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm leading-7 text-slate-700">
                        {selectedDimension.evidence}
                      </div>

                    </div>


                    {/* Suggestion */}

                    <div>

                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Improvement suggestion
                      </h4>

                      <div className="break-words rounded-2xl border border-indigo-100 bg-indigo-50 p-4 text-sm leading-7 text-indigo-900">
                        {selectedDimension.suggestion}
                      </div>

                    </div>


                    {/* No fake Apply button */}

                    <div className="rounded-2xl border border-slate-100 bg-white p-4">

                      <div className="flex gap-3">

                        <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />

                        <p className="text-xs leading-5 text-slate-500">
                          Suggestions are provided as review
                          guidance. They do not automatically
                          modify your manuscript or workspace.
                        </p>

                      </div>

                    </div>

                  </div>

                ) : (

                  <div className="p-5 text-sm text-slate-500">
                    Select a review dimension to view its
                    evidence and suggestion.
                  </div>

                )}

              </section>

            </aside>

          </div>
        ) : null}

      </div>
    </AppShell>
  );
}