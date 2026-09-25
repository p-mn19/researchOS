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
  X,
} from "lucide-react";

const dimensionIcons: Record<string, React.ReactNode> = {
  clarity: <BookOpen className="h-5 w-5 text-blue-500" />,
  novelty: <Lightbulb className="h-5 w-5 text-yellow-500" />,
  methodology: <AlertTriangle className="h-5 w-5 text-orange-500" />,
  evidence: <Target className="h-5 w-5 text-emerald-500" />,
  limitations: <TrendingDown className="h-5 w-5 text-violet-500" />,
};

const REVIEW_DIMENSION_GUIDE = [
  {
    id: "clarity",
    title: "Problem Clarity & Literature Coverage",
    description:
      "Checks whether the paper clearly explains the research problem, motivation, objectives, and relationship to relevant literature.",
  },
  {
    id: "novelty",
    title: "Novelty / Contribution",
    description:
      "Checks whether the paper clearly states its contribution and differentiates it from related work. Novelty cannot be proven from a single paper alone.",
  },
  {
    id: "methodology",
    title: "Method Justification & Completeness",
    description:
      "Checks whether the chosen methods are appropriate, justified, sufficiently described, and potentially reproducible.",
  },
  {
    id: "evidence",
    title: "Evidence & Results",
    description:
      "Checks whether datasets, experiments, metrics, comparisons, results, and interpretation sufficiently support the stated claims.",
  },
  {
    id: "limitations",
    title: "Limitations & Scope",
    description:
      "Checks whether assumptions, limitations, scope boundaries, risks, and future work are clearly acknowledged.",
  },
];

const dimensionExplanations: Record<string, string> = Object.fromEntries(
  REVIEW_DIMENSION_GUIDE.map((item) => [item.id, item.description]),
);

const scoreExplanations = [
  {
    range: "9–10",
    label: "Strong",
    description:
      "The supplied evidence is clear, specific, and strongly supports this dimension.",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  {
    range: "7–8",
    label: "Generally solid",
    description:
      "The paper is reasonably supported, with some areas that could still be strengthened.",
    className: "border-blue-200 bg-blue-50 text-blue-800",
  },
  {
    range: "5–6",
    label: "Mixed",
    description:
      "Some useful evidence is present, but important gaps or uncertainties remain.",
    className: "border-yellow-200 bg-yellow-50 text-yellow-800",
  },
  {
    range: "3–4",
    label: "Weak",
    description:
      "Major weaknesses or missing evidence materially affect the assessment.",
    className: "border-orange-200 bg-orange-50 text-orange-800",
  },
  {
    range: "1–2",
    label: "Very weak",
    description:
      "Little or no sufficient evidence was supplied for this dimension.",
    className: "border-red-200 bg-red-50 text-red-800",
  },
];

const concernExplanations = [
  {
    label: "None",
    description:
      "No significant concern was identified from the supplied evidence.",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  {
    label: "Moderate",
    description:
      "A meaningful issue or uncertainty should be clarified or strengthened.",
    className: "border-yellow-200 bg-yellow-50 text-yellow-800",
  },
  {
    label: "Major",
    description:
      "An important weakness or missing evidence materially affects the assessment.",
    className: "border-orange-200 bg-orange-50 text-orange-800",
  },
  {
    label: "Critical",
    description:
      "A fundamental issue exists, or essential information is unavailable for responsible assessment.",
    className: "border-red-200 bg-red-50 text-red-800",
  },
];

const confidenceExplanations = [
  {
    label: "High",
    description:
      "The supplied paper evidence clearly supports the assessment.",
    className: "text-emerald-700",
  },
  {
    label: "Medium",
    description:
      "The evidence reasonably supports the assessment, but uncertainty remains.",
    className: "text-blue-700",
  },
  {
    label: "Low",
    description:
      "The supplied evidence is limited, ambiguous, or incomplete.",
    className: "text-slate-600",
  },
];

function concernBadge(concern: ReviewDimension["concern"]) {
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

function confidenceColor(confidence: ReviewDimension["confidence"]) {
  if (confidence === "High") {
    return "text-emerald-600";
  }

  if (confidence === "Medium") {
    return "text-blue-600";
  }

  return "text-slate-500";
}

export default function ReviewSimulationPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState("");
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [selectedDimension, setSelectedDimension] =
    useState<ReviewDimension | null>(null);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [loadingReview, setLoadingReview] = useState(false);
  const [error, setError] = useState("");
  const [showReviewGuide, setShowReviewGuide] = useState(false);

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
        setError("Could not load uploaded papers.");
      } finally {
        setLoadingPapers(false);
      }
    }

    loadPapers();
  }, []);

  const selectedPaper = useMemo(
    () => papers.find((paper) => paper.id === selectedPaperId),
    [papers, selectedPaperId],
  );

  async function handleGenerateReview() {
    if (!selectedPaperId) {
      setError("Select a paper first.");
      return;
    }

    try {
      setLoadingReview(true);
      setError("");
      setReport(null);
      setSelectedDimension(null);

      const data = await generateReview(selectedPaperId);
      setReport(data);

      if (data.dimensions && data.dimensions.length > 0) {
        setSelectedDimension(data.dimensions[0]);
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

  return (
    <AppShell>
      <div className="min-h-full space-y-6 bg-slate-50 p-4 md:p-8">
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
                Analyse an uploaded research paper using its extracted
                information and source text. ResearchOS evaluates clarity,
                contribution, methodology, evidence, and limitations.
              </p>
            </div>

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
                  setSelectedPaperId(event.target.value);
                  setReport(null);
                  setSelectedDimension(null);
                  setError("");
                }}
                disabled={loadingPapers || papers.length === 0}
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100"
              >
                {loadingPapers ? (
                  <option>Loading papers...</option>
                ) : papers.length === 0 ? (
                  <option>No uploaded papers found</option>
                ) : (
                  papers.map((paper) => (
                    <option key={paper.id} value={paper.id}>
                      {paper.title || paper.filename}
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>

          {selectedPaper ? (
            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="break-words text-sm font-medium text-slate-900">
                {selectedPaper.title || "Untitled paper"}
              </p>

              <p className="mt-1 break-all text-xs text-slate-500">
                {selectedPaper.filename}
              </p>
            </div>
          ) : null}

          {error ? (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700">
              {error}
            </div>
          ) : null}

          <button
            type="button"
            onClick={handleGenerateReview}
            disabled={!selectedPaperId || loadingReview || loadingPapers}
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

        {!report && !loadingReview ? (
          <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center">
            <ClipboardCheck className="mx-auto h-10 w-10 text-slate-300" />

            <h2 className="mt-4 text-lg font-semibold text-slate-800">
              No review generated yet
            </h2>

            <p className="mt-2 text-sm text-slate-500">
              Select a paper and generate a review based on the available
              research evidence.
            </p>
          </section>
        ) : null}

        {report ? (
          <div className="flex flex-col gap-6 xl:flex-row">
            <main className="min-w-0 flex-1 space-y-6">
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

                  <div className="inline-flex shrink-0 items-center gap-2 rounded-2xl border border-indigo-100 bg-indigo-50 px-5 py-3 font-semibold text-indigo-700">
                    <Award className="h-5 w-5" />
                    <span className="text-lg">{report.overallScore}</span>
                  </div>
                </div>

                <div className="mt-6 border-t border-slate-100 pt-6">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                    Overall assessment
                  </h3>

                  <p className="mt-3 text-sm leading-7 text-slate-700">
                    {report.overallAssessment || report.summary}
                  </p>
                </div>
              </section>

              <section className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-2xl border border-emerald-200 bg-white p-5">
                  <div className="flex items-center gap-2">
                    <div className="rounded-lg bg-emerald-50 p-2">
                      <CheckCircle className="h-4 w-4 text-emerald-600" />
                    </div>

                    <h3 className="font-semibold text-slate-800">Strengths</h3>
                  </div>

                  {report.strengths?.length ? (
                    <ul className="mt-4 space-y-3">
                      {report.strengths.map((strength, index) => (
                        <li
                          key={index}
                          className="flex gap-2 text-sm leading-6 text-slate-600"
                        >
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                          <span>{strength}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      No specific strengths were identified from the supplied
                      evidence.
                    </p>
                  )}
                </div>

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
                      {report.weaknesses.map((weakness, index) => (
                        <li
                          key={index}
                          className="flex gap-2 text-sm leading-6 text-slate-600"
                        >
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" />
                          <span>{weakness}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      No specific weaknesses were identified from the supplied
                      evidence.
                    </p>
                  )}
                </div>

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
                      {report.missingInformation.map((item, index) => (
                        <li
                          key={index}
                          className="flex gap-2 text-sm leading-6 text-slate-600"
                        >
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      No major missing information was identified from the
                      supplied paper.
                    </p>
                  )}
                </div>
              </section>

              <section>
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900">
                      Review dimensions
                    </h2>

                    <p className="mt-1 text-sm text-slate-500">
                      Select a dimension to inspect the evidence and suggested
                      improvement.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => setShowReviewGuide(true)}
                    className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 transition hover:bg-indigo-100"
                  >
                    <Info className="h-4 w-4" />
                    How to interpret
                  </button>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {report.dimensions.map((dimension) => (
                    <button
                      type="button"
                      key={dimension.id}
                      onClick={() => setSelectedDimension(dimension)}
                      className={`min-w-0 rounded-2xl border bg-white p-5 text-left transition ${
                        selectedDimension?.id === dimension.id
                          ? "border-indigo-500 bg-indigo-50/30 ring-1 ring-indigo-500"
                          : "border-slate-200 hover:border-indigo-300 hover:shadow-sm"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex min-w-0 items-start gap-3">
                          <span className="mt-0.5 shrink-0">
                            {dimensionIcons[dimension.id] || (
                              <CheckCircle className="h-5 w-5 text-emerald-500" />
                            )}
                          </span>

                          <div className="min-w-0">
                            <h3 className="break-words font-semibold leading-6 text-slate-800">
                              {dimension.title}
                            </h3>

                            <p className="mt-1 break-words text-xs leading-5 text-slate-500">
                              {dimensionExplanations[dimension.id] ||
                                "This dimension assesses the quality of the supplied evidence."}
                            </p>
                          </div>
                        </div>

                        <span className="shrink-0 text-lg font-bold text-slate-700">
                          {dimension.score}
                        </span>
                      </div>

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
                  ))}
                </div>
              </section>
            </main>

            <aside className="w-full xl:sticky xl:top-6 xl:w-96 xl:self-start">
              <section className="flex max-h-[calc(100vh-3rem)] min-h-[500px] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 bg-slate-50 p-5">
                  <h3 className="flex items-center gap-2 font-semibold text-slate-800">
                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                    Evidence & suggestions
                  </h3>

                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    Grounded in the evidence supplied to the review engine.
                  </p>
                </div>

                {selectedDimension ? (
                  <div className="flex-1 space-y-6 overflow-y-auto p-5">
                    <div>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Selected dimension
                      </h4>

                      <p className="break-words text-lg font-semibold leading-7 text-slate-800">
                        {selectedDimension.title}
                      </p>

                      <p className="mt-2 text-sm leading-6 text-slate-500">
                        {dimensionExplanations[selectedDimension.id] ||
                          "This dimension assesses the quality of the supplied evidence."}
                      </p>
                    </div>

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

                    <div>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Evidence / rationale
                      </h4>

                      <div className="break-words rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm leading-7 text-slate-700">
                        {selectedDimension.evidence}
                      </div>
                    </div>

                    <div>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Improvement suggestion
                      </h4>

                      <div className="break-words rounded-2xl border border-indigo-100 bg-indigo-50 p-4 text-sm leading-7 text-indigo-900">
                        {selectedDimension.suggestion}
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-100 bg-white p-4">
                      <div className="flex gap-3">
                        <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />

                        <p className="text-xs leading-5 text-slate-500">
                          Suggestions are provided as review guidance. They do
                          not automatically modify your manuscript or workspace.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-5 text-sm text-slate-500">
                    Select a review dimension to view its evidence and
                    suggestion.
                  </div>
                )}
              </section>
            </aside>
          </div>
        ) : null}
      </div>

      {showReviewGuide && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="review-guide-title"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowReviewGuide(false);
            }
          }}
        >
          <section className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                  Review guide
                </p>

                <h2
                  id="review-guide-title"
                  className="mt-1 text-2xl font-semibold text-slate-900"
                >
                  How to interpret this review
                </h2>

                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                  Scores and labels describe how strongly the supplied paper
                  evidence supports each assessment. They are decision-support
                  signals, not an automatic publication decision.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowReviewGuide(false)}
                aria-label="Close review guide"
                className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <section className="mt-8">
              <h3 className="text-base font-semibold text-slate-900">
                Review dimensions
              </h3>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {REVIEW_DIMENSION_GUIDE.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <h4 className="font-semibold text-slate-900">
                      {item.title}
                    </h4>

                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      {item.description}
                    </p>
                  </article>
                ))}
              </div>
            </section>

            <section className="mt-8">
              <h3 className="text-base font-semibold text-slate-900">Score</h3>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {scoreExplanations.map((item) => (
                  <article
                    key={item.range}
                    className={`rounded-2xl border p-4 ${item.className}`}
                  >
                    <p className="font-semibold">
                      {item.range} · {item.label}
                    </p>

                    <p className="mt-1 text-sm leading-6">
                      {item.description}
                    </p>
                  </article>
                ))}
              </div>
            </section>

            <section className="mt-8 grid gap-8 md:grid-cols-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Concern level
                </h3>

                <div className="mt-3 space-y-3">
                  {concernExplanations.map((item) => (
                    <article
                      key={item.label}
                      className={`rounded-xl border px-3 py-3 ${item.className}`}
                    >
                      <p className="text-sm font-semibold">{item.label}</p>

                      <p className="mt-1 text-xs leading-5">
                        {item.description}
                      </p>
                    </article>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Confidence
                </h3>

                <div className="mt-3 space-y-3">
                  {confidenceExplanations.map((item) => (
                    <article
                      key={item.label}
                      className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3"
                    >
                      <p className={`text-sm font-semibold ${item.className}`}>
                        {item.label}
                      </p>

                      <p className="mt-1 text-xs leading-5 text-slate-600">
                        {item.description}
                      </p>
                    </article>
                  ))}
                </div>
              </div>
            </section>

            <div className="mt-8 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm leading-6 text-blue-900">
              <p className="font-semibold">Important interpretation note</p>

              <p className="mt-1">
                “Not reported” does not automatically mean “poor quality.” A
                lower confidence or moderate concern can mean the supplied
                paper text did not include enough information for a stronger
                assessment.
              </p>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}