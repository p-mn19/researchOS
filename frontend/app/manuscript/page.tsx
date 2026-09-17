"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  BookOpenText,
  FilePenLine,
  Loader2,
  Save,
  Sparkles,
} from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import {
  createSectionPlan,
  generateManuscriptSection,
  getPapers,
} from "@/lib/api";
import type {
  CitationSource,
  DraftSectionResponse,
  Paper,
  SectionPlanResponse,
  SentencePlan,
} from "@/lib/types";


function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Something went wrong while composing the manuscript section.";
}


export default function ManuscriptPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [sectionType, setSectionType] = useState<"related_work" | "methodology">(
    "related_work",
  );
  const [researchTopic, setResearchTopic] = useState("");
  const [targetWords, setTargetWords] = useState(500);
  const [plan, setPlan] = useState<SectionPlanResponse | null>(null);
  const [draft, setDraft] = useState<DraftSectionResponse | null>(null);
  const [draftText, setDraftText] = useState("");
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [planning, setPlanning] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");


  const extractedPapers = useMemo(
    () => papers.filter((paper) => paper.status === "extracted"),
    [papers],
  );


  useEffect(() => {
    async function loadPapers() {
      try {
        setLoadingPapers(true);
        setError("");

        const data = await getPapers();
        setPapers(data);

        setSelectedPaperIds(
          data
            .filter((paper) => paper.status === "extracted")
            .map((paper) => paper.id),
        );
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


  function resetGeneratedContent() {
    setPlan(null);
    setDraft(null);
    setDraftText("");
  }


  function handleSectionTypeChange(
    value: "related_work" | "methodology",
  ) {
    setSectionType(value);
    resetGeneratedContent();
  }


  function updatePlanItem(
    index: number,
    key: "purpose" | "claim",
    value: string,
  ) {
    setPlan((current) => {
      if (!current) {
        return current;
      }

      const sentencePlan = [...current.sentence_plan];
      sentencePlan[index] = {
        ...sentencePlan[index],
        [key]: value,
      };

      return {
        ...current,
        sentence_plan: sentencePlan,
      };
    });
  }


  async function handleCreatePlan() {
    if (selectedPaperIds.length === 0 || planning) {
      return;
    }

    try {
      setPlanning(true);
      setError("");
      setDraft(null);
      setDraftText("");

      const response = await createSectionPlan({
        paper_ids: selectedPaperIds,
        section_type: sectionType,
        research_topic: researchTopic.trim() || undefined,
        target_word_count: targetWords,
      });

      setPlan(response);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPlanning(false);
    }
  }


  async function handleGenerateDraft() {
    if (selectedPaperIds.length === 0 || generating) {
      return;
    }

    try {
      setGenerating(true);
      setError("");

      const response = await generateManuscriptSection({
        paper_ids: selectedPaperIds,
        section_type: sectionType,
        research_topic: researchTopic.trim() || undefined,
        target_word_count: targetWords,
        sentence_plan: plan?.sentence_plan || [],
      });

      setDraft(response);
      setDraftText(response.markdown);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setGenerating(false);
    }
  }


  function handleSaveLocalDraft() {
    const blob = new Blob([draftText], {
      type: "text/markdown;charset=utf-8",
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = `${sectionType}-${Date.now()}.md`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(url);
  }


  return (
    <AppShell>
      <div className="space-y-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                <FilePenLine className="h-3.5 w-3.5" />
                Module 9
              </div>

              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                Manuscript Composer
              </h1>

              <p className="mt-3 text-sm leading-6 text-slate-600">
                Build a controllable sentence plan, then generate a citation-grounded Related Work or Methodology section using your selected extracted papers.
              </p>
            </div>
          </div>
        </section>

        {error && (
          <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Source corpus
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Choose extracted papers. For a proper draft, each selected paper must be parsed, indexed, and extracted.
              </p>

              <div className="mt-5 max-h-[360px] space-y-3 overflow-y-auto pr-1">
                {loadingPapers ? (
                  <p className="text-sm text-slate-500">Loading papers...</p>
                ) : extractedPapers.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
                    No extracted papers are available. Run extraction on your papers before using the manuscript composer.
                  </div>
                ) : (
                  extractedPapers.map((paper) => {
                    const checked = selectedPaperIds.includes(paper.id);

                    return (
                      <label
                        key={paper.id}
                        className={`flex cursor-pointer items-start gap-3 rounded-2xl border p-4 transition ${
                          checked
                            ? "border-blue-300 bg-blue-50"
                            : "border-slate-200 bg-white hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            togglePaper(paper.id);
                            resetGeneratedContent();
                          }}
                          className="mt-1 h-4 w-4 accent-blue-600"
                        />

                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-slate-900">
                            {paper.title || "Untitled paper"}
                          </span>
                          <span className="mt-1 block text-xs text-slate-500">
                            {paper.year || "Year unavailable"} · {paper.filename}
                          </span>
                        </span>
                      </label>
                    );
                  })
                )}
              </div>
            </div>

            <div className="space-y-5 rounded-2xl bg-slate-50 p-5">
              <div>
                <label className="text-sm font-medium text-slate-800">
                  Manuscript section
                </label>

                <select
                  value={sectionType}
                  onChange={(event) =>
                    handleSectionTypeChange(
                      event.target.value as "related_work" | "methodology",
                    )
                  }
                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
                >
                  <option value="related_work">Related Work</option>
                  <option value="methodology">Methodology</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium text-slate-800">
                  Research topic or proposed study
                </label>

                <textarea
                  value={researchTopic}
                  onChange={(event) => {
                    setResearchTopic(event.target.value);
                    resetGeneratedContent();
                  }}
                  rows={5}
                  placeholder="Example: An explainable hybrid deep learning pipeline for exoplanet detection from noisy Kepler light curves..."
                  className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-slate-800">
                  Target length: {targetWords} words
                </label>

                <input
                  type="range"
                  min="200"
                  max="1200"
                  step="100"
                  value={targetWords}
                  onChange={(event) => {
                    setTargetWords(Number(event.target.value));
                    resetGeneratedContent();
                  }}
                  className="mt-3 w-full accent-blue-600"
                />
              </div>

              <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                {selectedPaperIds.length} paper{selectedPaperIds.length === 1 ? "" : "s"} selected
              </div>

              <button
                type="button"
                onClick={() => void handleCreatePlan()}
                disabled={planning || selectedPaperIds.length === 0}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {planning ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <BookOpenText className="h-4 w-4" />
                )}
                {planning ? "Creating plan..." : "Generate section plan"}
              </button>
            </div>
          </div>
        </section>

        {plan && (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 border-b border-slate-100 pb-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  Controllable sentence plan
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Edit purposes and claims before generating the final section.
                </p>
              </div>

              <button
                type="button"
                onClick={() => void handleGenerateDraft()}
                disabled={generating}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-violet-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                {generating ? "Drafting..." : "Generate grounded draft"}
              </button>
            </div>

            <div className="mt-5 rounded-2xl bg-slate-50 p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Section objective
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                {plan.objective}
              </p>
            </div>

            <div className="mt-5 space-y-4">
              {plan.sentence_plan.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                  The model did not return an editable sentence plan. You may still generate a draft, but ensure your extracted paper fields are populated for stronger results.
                </div>
              ) : (
                plan.sentence_plan.map((item, index) => (
                  <article
                    key={`${item.sentence_number}-${index}`}
                    className="rounded-2xl border border-slate-200 bg-white p-5"
                  >
                    <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                      Sentence {item.sentence_number}
                    </p>

                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <div>
                        <label className="text-xs font-medium text-slate-500">
                          Purpose
                        </label>

                        <textarea
                          value={item.purpose}
                          onChange={(event) =>
                            updatePlanItem(
                              index,
                              "purpose",
                              event.target.value,
                            )
                          }
                          rows={3}
                          className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-medium text-slate-500">
                          Claim or content direction
                        </label>

                        <textarea
                          value={item.claim}
                          onChange={(event) =>
                            updatePlanItem(
                              index,
                              "claim",
                              event.target.value,
                            )
                          }
                          rows={3}
                          className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
                        />
                      </div>
                    </div>

                    <div className="mt-4">
                      <p className="text-xs font-medium text-slate-500">
                        Allowed source paper IDs
                      </p>

                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.citation_paper_ids.length > 0 ? (
                          item.citation_paper_ids.map((paperId) => (
                            <span
                              key={paperId}
                              className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
                            >
                              {paperId}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-400">
                            No citations suggested for this sentence.
                          </span>
                        )}
                      </div>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        )}

        {draft && (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 border-b border-slate-100 pb-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  Generated {draft.section_title}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Edit the text below. Citations use paper IDs in the format <code>[paper_id]</code>.
                </p>
              </div>

              <button
                type="button"
                onClick={handleSaveLocalDraft}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700"
              >
                <Save className="h-4 w-4" />
                Download Markdown
              </button>
            </div>

            <div className="mt-6 grid gap-6 xl:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Editable draft
                </h3>

                <textarea
                  value={draftText}
                  onChange={(event) => setDraftText(event.target.value)}
                  rows={24}
                  className="mt-3 w-full resize-y rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 font-mono text-sm leading-6 text-slate-800 outline-none focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
                />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Preview
                </h3>

                <div className="mt-3 min-h-[580px] rounded-2xl border border-slate-200 bg-slate-50 p-6 text-sm leading-7 text-slate-700">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {draftText || "No draft content is available."}
                  </ReactMarkdown>
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <h3 className="text-sm font-semibold text-slate-900">
                Available citation sources
              </h3>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {draft.citations.map((source: CitationSource) => (
                  <div
                    key={source.paper_id}
                    className="rounded-xl border border-slate-200 bg-white p-4"
                  >
                    <p className="break-all text-xs font-semibold text-blue-700">
                      [{source.paper_id}]
                    </p>
                    <p className="mt-1 text-sm font-medium text-slate-900">
                      {source.title}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                      {source.authors.length > 0
                        ? source.authors.join(", ")
                        : "Authors unavailable"}
                      {source.year ? ` · ${source.year}` : ""}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}