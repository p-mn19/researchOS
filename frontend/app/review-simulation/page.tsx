"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import { generateReview, getPapers } from "@/lib/api";
import { Paper, ReviewDimension, ReviewReport } from "@/lib/types";
import {
  AlertTriangle,
  Award,
  BookOpen,
  CheckCircle,
  ClipboardCheck,
  Lightbulb,
  Loader2,
  MessageSquareWarning,
} from "lucide-react";

const dimensionIcons: Record<string, React.ReactNode> = {
  clarity: <BookOpen className="h-5 w-5 text-blue-500" />,
  novelty: <Lightbulb className="h-5 w-5 text-yellow-500" />,
  methodology: <AlertTriangle className="h-5 w-5 text-orange-500" />,
  claims: <MessageSquareWarning className="h-5 w-5 text-red-500" />,
};

function concernColor(concern: ReviewDimension["concern"]) {
  if (concern === "Critical") return "text-red-600";
  if (concern === "Major") return "text-orange-600";
  if (concern === "Moderate") return "text-yellow-600";
  return "text-emerald-600";
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
    [papers, selectedPaperId]
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
      setSelectedDimension(data.dimensions?.[0] || null);
    } catch (err) {
      console.error(err);
      setError("Could not generate the review.");
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
                Peer-review assistance
              </div>

              <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                Reviewer Simulation
              </h1>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Select one of your uploaded papers to generate a structured
                simulated review covering clarity, novelty, methodology, and
                limitations.
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
                }}
                disabled={loadingPapers || papers.length === 0}
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100"
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
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
                Generate simulated review
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
              Select a paper and generate a simulated reviewer report.
            </p>
          </section>
        ) : null}

        {report ? (
          <div className="flex flex-col gap-6 xl:flex-row">
            <main className="min-w-0 flex-1 space-y-6">
              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <h2 className="break-words text-xl font-semibold text-slate-800">
                      {report.paperTitle}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Generated by ResearchOS Review Engine
                    </p>
                  </div>

                  <div className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-indigo-50 px-4 py-2 font-medium text-indigo-700">
                    <Award className="h-5 w-5" />
                    {report.overallScore}
                  </div>
                </div>

                <p className="mt-5 border-t border-slate-100 pt-5 text-sm leading-7 text-slate-700">
                  {report.summary}
                </p>
              </section>

              <section className="grid gap-4 md:grid-cols-2">
                {report.dimensions.map((dimension) => (
                  <button
                    type="button"
                    key={dimension.id}
                    onClick={() => setSelectedDimension(dimension)}
                    className={`min-w-0 rounded-2xl border p-5 text-left transition ${
                      selectedDimension?.id === dimension.id
                        ? "border-indigo-500 bg-indigo-50/30 ring-1 ring-indigo-500"
                        : "border-slate-200 bg-white hover:border-indigo-300"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-start gap-2">
                        <span className="shrink-0">
                          {dimensionIcons[dimension.id] || (
                            <CheckCircle className="h-5 w-5 text-emerald-500" />
                          )}
                        </span>

                        <h3 className="break-words font-semibold text-slate-800">
                          {dimension.title}
                        </h3>
                      </div>

                      <span className="shrink-0 text-sm font-bold text-slate-600">
                        {dimension.score}
                      </span>
                    </div>

                    <p className="mt-4 text-sm text-slate-600">
                      <strong>Concern level:</strong>{" "}
                      <span className={concernColor(dimension.concern)}>
                        {dimension.concern}
                      </span>
                    </p>
                  </button>
                ))}
              </section>
            </main>

            <aside className="w-full xl:sticky xl:top-6 xl:w-96 xl:self-start">
              <section className="flex max-h-[calc(100vh-3rem)] min-h-[420px] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 bg-slate-50 p-4">
                  <h3 className="flex items-center gap-2 font-semibold text-slate-800">
                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                    Evidence & suggestions
                  </h3>
                </div>

                {selectedDimension ? (
                  <div className="flex-1 space-y-6 overflow-y-auto p-5">
                    <div>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Selected dimension
                      </h4>
                      <p className="break-words text-lg font-medium text-slate-800">
                        {selectedDimension.title}
                      </p>
                    </div>

                    <div>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Evidence / rationale
                      </h4>
                      <div className="break-words rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                        {selectedDimension.evidence}
                      </div>
                    </div>

                    <div>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                        Improvement suggestion
                      </h4>
                      <div className="break-words rounded-xl border border-indigo-100 bg-indigo-50 p-4 text-sm leading-6 text-indigo-900">
                        {selectedDimension.suggestion}
                      </div>
                    </div>

                    <button
                      type="button"
                      className="w-full rounded-xl bg-slate-900 py-3 text-sm font-medium text-white transition hover:bg-slate-800"
                    >
                      Apply suggestion to draft
                    </button>
                  </div>
                ) : (
                  <div className="p-5 text-sm text-slate-500">
                    Select a review dimension to view its evidence.
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