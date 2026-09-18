"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Check,
  CheckSquare,
  FolderPlus,
  Lightbulb,
  Loader2,
  Sparkles,
} from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import { analyzeIdeation, getPapers } from "@/lib/api";
import type {
  IdeationResponse,
  Paper,
  ResearchIdea,
} from "@/lib/types";


const IDEA_STORAGE_KEY = "researchos_ideation_ideas";


function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Something went wrong while generating research ideas.";
}


function getStoredIdeas(): ResearchIdea[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const stored = window.localStorage.getItem(
      IDEA_STORAGE_KEY,
    );

    if (!stored) {
      return [];
    }

    const parsed: unknown = JSON.parse(stored);

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(
      (idea): idea is ResearchIdea =>
        typeof idea === "object" &&
        idea !== null &&
        "title" in idea &&
        "problem_statement" in idea,
    );
  } catch {
    return [];
  }
}


function saveIdeas(ideas: ResearchIdea[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    IDEA_STORAGE_KEY,
    JSON.stringify(ideas),
  );
}


export default function IdeationPage() {
  const router = useRouter();

  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [topic, setTopic] = useState("");
  const [ideaCount, setIdeaCount] = useState(3);
  const [result, setResult] = useState<IdeationResponse | null>(null);
  const [savedIdeas, setSavedIdeas] = useState<ResearchIdea[]>([]);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");


  const extractedPapers = useMemo(
    () =>
      papers.filter(
        (paper) => paper.status === "extracted",
      ),
    [papers],
  );


  useEffect(() => {
    setSavedIdeas(getStoredIdeas());

    async function loadPapers() {
      try {
        setLoadingPapers(true);
        setError("");

        const data = await getPapers();
        setPapers(data);

        const extractedIds = data
          .filter(
            (paper) =>
              paper.status === "extracted",
          )
          .map((paper) => paper.id);

        setSelectedPaperIds(extractedIds);
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setLoadingPapers(false);
      }
    }

    void loadPapers();
  }, []);


  function togglePaper(paperId: string) {
    setSelectedPaperIds((current) =>
      current.includes(paperId)
        ? current.filter((id) => id !== paperId)
        : [...current, paperId],
    );
  }


  function selectAllExtracted() {
    setSelectedPaperIds(
      extractedPapers.map(
        (paper) => paper.id,
      ),
    );
  }


  function clearSelection() {
    setSelectedPaperIds([]);
  }


  function saveAllGeneratedIdeas(
    ideas: ResearchIdea[],
  ) {
    if (ideas.length === 0) {
      return;
    }

    const existingIdeas = getStoredIdeas();

    const mergedIdeas = [
      ...ideas,
      ...existingIdeas,
    ].filter((idea, index, allIdeas) => {
      return (
        allIdeas.findIndex(
          (candidate) =>
            candidate.title === idea.title &&
            candidate.problem_statement ===
              idea.problem_statement,
        ) === index
      );
    });

    saveIdeas(mergedIdeas);
    setSavedIdeas(mergedIdeas);

    setNotice(
      `${ideas.length} generated idea${
        ideas.length === 1 ? "" : "s"
      } saved for the Research Workspace.`,
    );
  }


  function sendIdeaToWorkspace(
    idea: ResearchIdea,
  ) {
    const existingIdeas = getStoredIdeas();

    const alreadyStored = existingIdeas.some(
      (candidate) =>
        candidate.title === idea.title &&
        candidate.problem_statement ===
          idea.problem_statement,
    );

    const updatedIdeas = alreadyStored
      ? existingIdeas
      : [idea, ...existingIdeas];

    saveIdeas(updatedIdeas);
    setSavedIdeas(updatedIdeas);

    router.push("/workspace");
  }


  async function handleGenerate() {
    if (
      selectedPaperIds.length === 0 ||
      generating
    ) {
      return;
    }

    try {
      setGenerating(true);
      setError("");
      setNotice("");

      const response = await analyzeIdeation({
        paper_ids: selectedPaperIds,
        topic: topic.trim() || undefined,
        idea_count: ideaCount,
      });

      setResult(response);

      if (response.ideas.length > 0) {
        saveAllGeneratedIdeas(response.ideas);
      } else {
        setNotice(
          "Analysis completed, but no usable candidate ideas were returned. Check whether selected papers have limitations, future-work, and methodology extraction fields.",
        );
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setGenerating(false);
    }
  }


  return (
    <AppShell>
      <div className="space-y-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700">
                <Lightbulb className="h-3.5 w-3.5" />
                Module 8
              </div>

              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                Research Gap & Ideation
              </h1>

              <p className="mt-3 text-sm leading-6 text-slate-600">
                Analyze limitations, future work, methodologies, and findings across your selected corpus. The output contains candidate gaps and testable research directions grounded in the papers you select.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              {savedIdeas.length > 0 && (
                <button
                  type="button"
                  onClick={() => router.push("/workspace")}
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-2xl border border-violet-200 bg-violet-50 px-5 py-3 text-sm font-medium text-violet-800 transition hover:bg-violet-100"
                >
                  <FolderPlus className="h-4 w-4" />
                  Open Workspace
                </button>
              )}

              <button
                type="button"
                onClick={() => void handleGenerate()}
                disabled={
                  generating ||
                  selectedPaperIds.length === 0
                }
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-2xl bg-violet-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}

                {generating
                  ? "Analyzing corpus..."
                  : "Generate ideas"}
              </button>
            </div>
          </div>
        </section>

        {error && (
          <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {notice && (
          <div className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">
            <Check className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{notice}</p>
          </div>
        )}

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 border-b border-slate-100 pb-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Select paper corpus
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Select papers that have completed extraction. A diverse and relevant corpus generally produces stronger comparison and ideation results.
              </p>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={selectAllExtracted}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Select extracted
              </button>

              <button
                type="button"
                onClick={clearSelection}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Clear
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="max-h-[380px] space-y-3 overflow-y-auto pr-1">
              {loadingPapers ? (
                <p className="text-sm text-slate-500">
                  Loading papers...
                </p>
              ) : extractedPapers.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
                  No extracted papers are available. Open each relevant paper, click “Run extraction,” then return here.
                </div>
              ) : (
                extractedPapers.map((paper) => {
                  const selected =
                    selectedPaperIds.includes(
                      paper.id,
                    );

                  return (
                    <label
                      key={paper.id}
                      className={`flex cursor-pointer items-start gap-3 rounded-2xl border p-4 transition ${
                        selected
                          ? "border-violet-300 bg-violet-50"
                          : "border-slate-200 bg-white hover:bg-slate-50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() =>
                          togglePaper(paper.id)
                        }
                        className="mt-1 h-4 w-4 accent-violet-600"
                      />

                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-slate-900">
                          {paper.title ||
                            "Untitled paper"}
                        </span>

                        <span className="mt-1 block text-xs text-slate-500">
                          {paper.year ||
                            "Year unavailable"}{" "}
                          · {paper.filename}
                        </span>
                      </span>
                    </label>
                  );
                })
              )}
            </div>

            <div className="space-y-4 rounded-2xl bg-slate-50 p-5">
              <div>
                <label className="text-sm font-medium text-slate-800">
                  Optional research direction
                </label>

                <textarea
                  value={topic}
                  onChange={(event) =>
                    setTopic(event.target.value)
                  }
                  rows={5}
                  placeholder="Example: Robust exoplanet detection from noisy light curves using deep learning..."
                  className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-slate-800">
                  Number of candidate ideas
                </label>

                <select
                  value={ideaCount}
                  onChange={(event) =>
                    setIdeaCount(
                      Number(event.target.value),
                    )
                  }
                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 outline-none focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
                >
                  <option value={1}>1 idea</option>
                  <option value={2}>2 ideas</option>
                  <option value={3}>3 ideas</option>
                  <option value={4}>4 ideas</option>
                  <option value={5}>5 ideas</option>
                </select>
              </div>

              <div className="rounded-xl border border-violet-100 bg-violet-50 px-4 py-3 text-sm text-violet-900">
                <p className="font-medium">
                  {selectedPaperIds.length} paper
                  {selectedPaperIds.length === 1
                    ? ""
                    : "s"}{" "}
                  selected
                </p>

                <p className="mt-1 text-xs leading-5 text-violet-700">
                  Generated ideas must reference selected paper IDs so the workspace can preserve evidence traceability.
                </p>
              </div>
            </div>
          </div>
        </section>

        {result && (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">
                  Corpus analysis
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Analysis based on {result.corpus_size} selected paper
                  {result.corpus_size === 1 ? "" : "s"}{" "}
                  using {result.model}.
                </p>
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-2xl border border-orange-100 bg-orange-50 p-5">
                  <h3 className="font-semibold text-orange-950">
                    Recurring limitations
                  </h3>

                  <div className="mt-3 space-y-2">
                    {result.recurring_limitations.length >
                    0 ? (
                      result.recurring_limitations.map(
                        (item, index) => (
                          <p
                            key={`${item}-${index}`}
                            className="text-sm leading-6 text-orange-900"
                          >
                            {index + 1}. {item}
                          </p>
                        ),
                      )
                    ) : (
                      <p className="text-sm text-orange-800">
                        No recurring limitations were identified from the available extraction fields.
                      </p>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-violet-100 bg-violet-50 p-5">
                  <h3 className="font-semibold text-violet-950">
                    Candidate research gaps
                  </h3>

                  <div className="mt-3 space-y-2">
                    {result.research_gaps.length > 0 ? (
                      result.research_gaps.map(
                        (item, index) => (
                          <p
                            key={`${item}-${index}`}
                            className="text-sm leading-6 text-violet-900"
                          >
                            {index + 1}. {item}
                          </p>
                        ),
                      )
                    ) : (
                      <p className="text-sm text-violet-800">
                        No candidate gaps were returned. Ensure selected papers have limitations and future-work extraction data.
                      </p>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-cyan-100 bg-cyan-50 p-5">
                  <h3 className="font-semibold text-cyan-950">
                    Method directions
                  </h3>

                  <div className="mt-3 space-y-2">
                    {result.recommended_methodologies
                      .length > 0 ? (
                      result.recommended_methodologies.map(
                        (item, index) => (
                          <p
                            key={`${item}-${index}`}
                            className="text-sm leading-6 text-cyan-900"
                          >
                            {index + 1}. {item}
                          </p>
                        ),
                      )
                    ) : (
                      <p className="text-sm text-cyan-800">
                        No method directions were returned from the corpus.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    Candidate research ideas
                  </h2>

                  <p className="mt-1 text-sm text-slate-500">
                    These are candidate directions to validate through a broader literature review. Select an idea to continue in Research Workspace.
                  </p>
                </div>

                {result.ideas.length > 0 && (
                  <button
                    type="button"
                    onClick={() =>
                      saveAllGeneratedIdeas(
                        result.ideas,
                      )
                    }
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-medium text-violet-800 transition hover:bg-violet-100"
                  >
                    <FolderPlus className="h-4 w-4" />
                    Save all ideas
                  </button>
                )}
              </div>

              <div className="space-y-5">
                {result.ideas.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                    No ideas were generated. Check that your selected papers have extracted content and try again.
                  </div>
                ) : (
                  result.ideas.map((idea, index) => (
                    <article
                      key={`${idea.title}-${index}`}
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-6"
                    >
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div className="flex items-start gap-3">
                          <div className="rounded-xl bg-violet-600 p-2 text-white">
                            <Lightbulb className="h-4 w-4" />
                          </div>

                          <div className="min-w-0">
                            <p className="text-xs font-medium uppercase tracking-wide text-violet-700">
                              Idea {index + 1}
                            </p>

                            <h3 className="mt-1 text-lg font-semibold text-slate-900">
                              {idea.title}
                            </h3>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() =>
                            sendIdeaToWorkspace(idea)
                          }
                          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700"
                        >
                          <FolderPlus className="h-4 w-4" />
                          Use in Workspace
                        </button>
                      </div>

                      <div className="mt-5 grid gap-4 lg:grid-cols-2">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Problem statement
                          </p>

                          <p className="mt-1 text-sm leading-6 text-slate-700">
                            {idea.problem_statement}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Testable hypothesis
                          </p>

                          <p className="mt-1 text-sm leading-6 text-slate-700">
                            {idea.hypothesis}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Recommended methodology
                          </p>

                          <p className="mt-1 text-sm leading-6 text-slate-700">
                            {idea.recommended_methodology}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Expected contribution
                          </p>

                          <p className="mt-1 text-sm leading-6 text-slate-700">
                            {idea.expected_contribution}
                          </p>
                        </div>
                      </div>

                      <div className="mt-5 border-t border-slate-200 pt-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Supporting paper IDs
                        </p>

                        <div className="mt-2 flex flex-wrap gap-2">
                          {idea.evidence_paper_ids.length >
                          0 ? (
                            idea.evidence_paper_ids.map(
                              (paperId) => (
                                <span
                                  key={paperId}
                                  className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm"
                                >
                                  {paperId}
                                </span>
                              ),
                            )
                          ) : (
                            <span className="text-sm text-slate-500">
                              No valid supporting paper IDs returned.
                            </span>
                          )}
                        </div>
                      </div>
                    </article>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5 flex items-center gap-2">
                <CheckSquare className="h-5 w-5 text-slate-700" />

                <h2 className="text-xl font-semibold text-slate-900">
                  Evidence inventory
                </h2>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-medium">
                        Paper
                      </th>
                      <th className="px-4 py-3 font-medium">
                        Limitation
                      </th>
                      <th className="px-4 py-3 font-medium">
                        Future work
                      </th>
                      <th className="px-4 py-3 font-medium">
                        Methodology
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {result.evidence_papers.map(
                      (paper) => (
                        <tr
                          key={paper.paper_id}
                          className="border-t border-slate-100 align-top"
                        >
                          <td className="px-4 py-4">
                            <p className="font-medium text-slate-900">
                              {paper.title}
                            </p>

                            <p className="mt-1 break-all text-xs text-slate-500">
                              {paper.paper_id}
                            </p>
                          </td>

                          <td className="max-w-xs px-4 py-4 leading-6 text-slate-600">
                            {paper.limitation || "—"}
                          </td>

                          <td className="max-w-xs px-4 py-4 leading-6 text-slate-600">
                            {paper.future_work || "—"}
                          </td>

                          <td className="max-w-xs px-4 py-4 leading-6 text-slate-600">
                            {paper.methodology || "—"}
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}