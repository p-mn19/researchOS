"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  ChevronDown,
  Code2,
  Copy,
  Download,
  FileCode2,
  FileText,
  FolderPlus,
  Loader2,
  Save,
  Sparkles,
} from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import {
  createWorkspace,
  generateWorkspaceContent,
  getPapers,
  getWorkspaces,
  saveWorkspaceVersion,
} from "@/lib/api";
import type {
  Paper,
  ResearchIdea,
  Workspace,
  WorkspaceContentType,
  WorkspaceGenerationResponse,
} from "@/lib/types";


const IDEA_STORAGE_KEY = "researchos_ideation_ideas";


const contentTypes: Array<{
  value: WorkspaceContentType;
  label: string;
  description: string;
}> = [
  {
    value: "introduction",
    label: "Introduction",
    description:
      "Introduce the research domain, motivation, and proposed study direction.",
  },
  {
    value: "research_problem",
    label: "Research Problem",
    description:
      "Define the problem, motivation, scope, and evidence gap.",
  },
  {
    value: "research_objectives",
    label: "Research Objectives",
    description:
      "Convert the selected idea into specific research objectives.",
  },
  {
    value: "research_questions",
    label: "Research Questions",
    description:
      "Generate focused and answerable research questions.",
  },
  {
    value: "hypotheses",
    label: "Research Hypotheses",
    description:
      "Develop testable hypotheses while distinguishing proposed claims from evidence.",
  },
  {
    value: "related_work",
    label: "Related Work",
    description:
      "Synthesize selected evidence with traceable citations.",
  },
  {
    value: "methodology",
    label: "Proposed Methodology",
    description:
      "Describe a proposed methodology based on the selected idea and evidence.",
  },
  {
    value: "proposed_framework",
    label: "Proposed Framework",
    description:
      "Describe components and flow of a proposed research framework.",
  },
  {
    value: "experimental_design",
    label: "Experimental Design",
    description:
      "Outline proposed experiments, baselines, datasets, and controls.",
  },
  {
    value: "evaluation_plan",
    label: "Evaluation Plan",
    description:
      "Propose evaluation metrics and validation procedures grounded in source practices.",
  },
  {
    value: "expected_contributions",
    label: "Expected Contributions",
    description:
      "State expected contributions cautiously as proposed outcomes.",
  },
  {
    value: "limitations_and_scope",
    label: "Limitations and Scope",
    description:
      "State anticipated limitations, boundaries, and research risks.",
  },
  {
    value: "abstract_draft",
    label: "Abstract Draft",
    description:
      "Create an early abstract draft from the workspace objective and idea.",
  },
  {
    value: "conclusion",
    label: "Conclusion",
    description:
      "Summarize the proposed study without claiming completed results.",
  },
];


function errorMessage(
  error: unknown,
  fallback: string,
): string {
  if (error instanceof Error && error.message) {
    const message = error.message;

    if (
      /rate_limit|tokens per minute|status code: 429/i.test(
        message,
      )
    ) {
      return (
        "Generation is temporarily rate-limited. Wait about a minute, " +
        "then retry. Your workspace has not been changed."
      );
    }

    return message;
  }

  return fallback;
}


function normalizeIdeas(
  value: unknown,
): ResearchIdea[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (idea): idea is ResearchIdea =>
      typeof idea === "object" &&
      idea !== null &&
      "title" in idea &&
      "problem_statement" in idea,
  );
}


function readSavedIdeas(): ResearchIdea[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const stored = window.localStorage.getItem(
      IDEA_STORAGE_KEY,
    );

    return stored
      ? normalizeIdeas(JSON.parse(stored))
      : [];
  } catch {
    return [];
  }
}


function copyText(text: string) {
  if (!text) {
    return;
  }

  void navigator.clipboard.writeText(text);
}


function downloadTextFile(
  filename: string,
  content: string,
  mimeType: string,
) {
  if (!content.trim()) {
    return;
  }

  const blob = new Blob(
    [content],
    {
      type: mimeType,
    },
  );

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = filename;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  URL.revokeObjectURL(url);
}


function safeFilename(value: string): string {
  const cleaned = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return cleaned || "researchos-workspace";
}


function wordCount(text: string): number {
  const plain = text
    .replace(/[`*_>#\[\]()]/g, " ")
    .replace(/\\cite\{[^}]+\}/g, " ")
    .trim();

  return plain
    ? plain.split(/\s+/).length
    : 0;
}


export default function WorkspacePage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [savedIdeas, setSavedIdeas] =
    useState<ResearchIdea[]>([]);

  const [selectedPaperIds, setSelectedPaperIds] =
    useState<string[]>([]);

  const [selectedIdea, setSelectedIdea] =
    useState<ResearchIdea | null>(null);

  const [workspace, setWorkspace] =
    useState<Workspace | null>(null);

  const [workspaceTitle, setWorkspaceTitle] =
    useState("");

  const [workspaceDescription, setWorkspaceDescription] =
    useState("");

  const [researchObjective, setResearchObjective] =
    useState("");

  const [contentType, setContentType] =
    useState<WorkspaceContentType>("related_work");

  const [targetWords, setTargetWords] =
    useState(500);

  const [instructions, setInstructions] =
    useState("");

  const [generation, setGeneration] =
    useState<WorkspaceGenerationResponse | null>(
      null,
    );

  const [contentMarkdown, setContentMarkdown] =
    useState("");

  const [latexCode, setLatexCode] =
    useState("");

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");


  const extractedPapers = useMemo(
    () =>
      papers.filter(
        (paper) =>
          paper.status === "extracted",
      ),
    [papers],
  );


  const selectedContentType = useMemo(
    () =>
      contentTypes.find(
        (item) =>
          item.value === contentType,
      ),
    [contentType],
  );


  const generatedWordCount = useMemo(
    () => wordCount(contentMarkdown),
    [contentMarkdown],
  );


  useEffect(() => {
    setSavedIdeas(readSavedIdeas());

    async function loadData() {
      try {
        setLoading(true);
        setError("");

        const [paperData, workspaceData] =
          await Promise.all([
            getPapers(),
            getWorkspaces().catch(() => []),
          ]);

        setPapers(paperData);
        setWorkspaces(workspaceData);

        setSelectedPaperIds(
          paperData
            .filter(
              (paper) =>
                paper.status === "extracted",
            )
            .map((paper) => paper.id),
        );
      } catch (err) {
        setError(
          errorMessage(
            err,
            "Could not load workspace data.",
          ),
        );
      } finally {
        setLoading(false);
      }
    }

    void loadData();
  }, []);


  function resetGeneratedOutput() {
    setGeneration(null);
    setContentMarkdown("");
    setLatexCode("");
  }


  function togglePaper(paperId: string) {
    setSelectedPaperIds((current) =>
      current.includes(paperId)
        ? current.filter(
            (id) => id !== paperId,
          )
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


  function selectIdea(idea: ResearchIdea) {
    setSelectedIdea(idea);

    setNotice(
      "Research idea selected. Create the workspace to preserve this idea snapshot.",
    );

    if (!researchObjective.trim()) {
      setResearchObjective(
        idea.problem_statement,
      );
    }

    if (!workspaceTitle.trim()) {
      setWorkspaceTitle(idea.title);
    }
  }


  async function handleCreateWorkspace() {
    if (
      !selectedIdea ||
      selectedPaperIds.length === 0 ||
      creating
    ) {
      return;
    }

    try {
      setCreating(true);
      setError("");
      setNotice("");

      const created = await createWorkspace({
        title:
          workspaceTitle.trim() ||
          selectedIdea.title,
        description:
          workspaceDescription.trim(),
        paper_ids: selectedPaperIds,
        idea: selectedIdea,
        research_objective:
          researchObjective.trim(),
      });

      setWorkspace(created);

      setWorkspaces((current) => [
        created,
        ...current,
      ]);

      resetGeneratedOutput();

      setNotice(
        "Workspace created. You can now generate a research section.",
      );
    } catch (err) {
      setError(
        errorMessage(
          err,
          "Could not create workspace.",
        ),
      );
    } finally {
      setCreating(false);
    }
  }


  async function handleGenerate() {
    if (!workspace || generating) {
      return;
    }

    try {
      setGenerating(true);
      setError("");
      setNotice("");
      resetGeneratedOutput();

      const result =
        await generateWorkspaceContent(
          workspace.id,
          {
            content_type: contentType,
            target_word_count: targetWords,
            generate_latex: true,
            citation_style: "internal",
            instructions: instructions.trim(),
          },
        );

      setGeneration(result);

      setContentMarkdown(
        result.content_markdown,
      );

      setLatexCode(result.latex_code);

      setNotice(
        "Section content and LaTeX were generated from the selected workspace evidence.",
      );
    } catch (err) {
      setError(
        errorMessage(
          err,
          "Could not generate workspace content.",
        ),
      );
    } finally {
      setGenerating(false);
    }
  }


  async function handleSaveVersion() {
    if (!workspace || !generation || saving) {
      return;
    }

    try {
      setSaving(true);
      setError("");
      setNotice("");

      const saved = await saveWorkspaceVersion(
        workspace.id,
        {
          content_type: generation.content_type,
          content_markdown: contentMarkdown,
          latex_code: latexCode,
          citations: generation.citations,
          warnings: generation.warnings,
          source_chunk_ids:
            generation.source_chunk_ids,
        },
      );

      setNotice(
        `Workspace version ${saved.version} saved successfully.`,
      );
    } catch (err) {
      setError(
        errorMessage(
          err,
          "Could not save workspace version.",
        ),
      );
    } finally {
      setSaving(false);
    }
  }


  function openExistingWorkspace(item: Workspace) {
    setWorkspace(item);
    setWorkspaceTitle(item.title);
    setWorkspaceDescription(
      item.description || "",
    );
    setResearchObjective(
      item.research_objective || "",
    );
    setSelectedPaperIds(item.paper_ids || []);
    setSelectedIdea(item.idea);

    resetGeneratedOutput();

    setNotice(
      `Opened workspace: ${item.title}`,
    );
  }


  const downloadBaseName = safeFilename(
    workspace?.title ||
      workspaceTitle ||
      "researchos-workspace",
  );


  return (
    <AppShell>
      <div className="space-y-5">
        <section className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                <FileCode2 className="h-3.5 w-3.5" />
                Module 9
              </div>

              <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                Research Workspace
              </h1>

              <p className="mt-2 text-sm leading-5 text-slate-600">
                Build a workspace from selected papers and a Module 8 idea. Generate one evidence-grounded research section with editable Markdown and LaTeX output.
              </p>
            </div>

            {workspace && (
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <p className="font-semibold">
                  Active workspace
                </p>

                <p className="mt-1 max-w-xs truncate">
                  {workspace.title}
                </p>
              </div>
            )}
          </div>
        </section>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {notice && (
          <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <Check className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{notice}</p>
          </div>
        )}

        {loading ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-8 text-sm text-slate-500 shadow-sm">
            Loading uploaded papers and workspaces...
          </section>
        ) : (
          <>
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex flex-col gap-2 border-b border-slate-100 pb-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    1. Configure workspace
                  </h2>

                  <p className="mt-1 text-sm text-slate-500">
                    Select the source corpus and lock a selected research idea into the workspace.
                  </p>
                </div>

                {workspaces.length > 0 && (
                  <select
                    defaultValue=""
                    onChange={(event) => {
                      const item = workspaces.find(
                        (workspaceItem) =>
                          workspaceItem.id ===
                          event.target.value,
                      );

                      if (item) {
                        openExistingWorkspace(item);
                      }
                    }}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-50"
                  >
                    <option value="">
                      Open saved workspace
                    </option>

                    {workspaces.map((item) => (
                      <option
                        key={item.id}
                        value={item.id}
                      >
                        {item.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900">
                        Select extracted source papers
                      </h3>

                      <p className="mt-1 text-xs text-slate-500">
                        These papers become the evidence corpus for generation.
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={selectAllExtracted}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                      Select all
                    </button>
                  </div>

                  <div className="mt-3 max-h-64 space-y-2 overflow-y-auto pr-1">
                    {extractedPapers.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
                        No extracted papers are available. Parse and extract papers before creating a workspace.
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
                            className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                              selected
                                ? "border-blue-300 bg-blue-50"
                                : "border-slate-200 bg-white hover:bg-slate-50"
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={selected}
                              onChange={() => {
                                togglePaper(paper.id);
                                resetGeneratedOutput();
                              }}
                              className="mt-1 h-4 w-4 accent-blue-600"
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
                </div>

                <div className="space-y-3 rounded-xl bg-slate-50 p-4">
                  <div>
                    <label className="text-sm font-medium text-slate-800">
                      Workspace title
                    </label>

                    <input
                      value={workspaceTitle}
                      onChange={(event) =>
                        setWorkspaceTitle(
                          event.target.value,
                        )
                      }
                      placeholder="Example: Explainable Exoplanet Detection Study"
                      className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-800">
                      Workspace description
                    </label>

                    <textarea
                      value={workspaceDescription}
                      onChange={(event) =>
                        setWorkspaceDescription(
                          event.target.value,
                        )
                      }
                      rows={2}
                      placeholder="Optional note about this research workspace..."
                      className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-800">
                      Research objective
                    </label>

                    <textarea
                      value={researchObjective}
                      onChange={(event) =>
                        setResearchObjective(
                          event.target.value,
                        )
                      }
                      rows={3}
                      placeholder="Describe what the proposed workspace study aims to investigate..."
                      className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
                    />
                  </div>

                  <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                    <p className="font-medium">
                      {selectedPaperIds.length} source paper
                      {selectedPaperIds.length === 1
                        ? ""
                        : "s"}{" "}
                      selected
                    </p>

                    <p className="mt-1 text-xs leading-5 text-blue-700">
                      The workspace stores selected papers and the selected idea as an evidence snapshot.
                    </p>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4">
                <h2 className="text-xl font-semibold text-slate-900">
                  2. Select research idea
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Run Module 8 first, then choose an idea to make it the proposed direction of this workspace.
                </p>
              </div>

              {savedIdeas.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-violet-200 bg-violet-50 p-6 text-sm text-violet-900">
                  <p className="font-medium">
                    No saved Module 8 ideas found in this browser.
                  </p>

                  <p className="mt-2 leading-6 text-violet-800">
                    Open Research Gap & Ideation, generate candidate ideas, and click “Use in Workspace” for one of them.
                  </p>
                </div>
              ) : (
                <div className="grid gap-3 lg:grid-cols-2">
                  {savedIdeas.map((idea, index) => {
                    const active =
                      selectedIdea?.title ===
                        idea.title &&
                      selectedIdea?.problem_statement ===
                        idea.problem_statement;

                    return (
                      <article
                        key={`${idea.title}-${index}`}
                        className={`rounded-xl border p-4 transition ${
                          active
                            ? "border-violet-300 bg-violet-50"
                            : "border-slate-200 bg-slate-50"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">
                              Candidate idea {index + 1}
                            </p>

                            <h3 className="mt-1 text-base font-semibold text-slate-900">
                              {idea.title}
                            </h3>
                          </div>

                          {active && (
                            <span className="rounded-full bg-violet-600 px-2.5 py-1 text-xs font-medium text-white">
                              Selected
                            </span>
                          )}
                        </div>

                        <p className="mt-2 text-sm leading-5 text-slate-700">
                          {idea.problem_statement}
                        </p>

                        {idea.hypothesis && (
                          <p className="mt-3 text-xs leading-5 text-slate-600">
                            <span className="font-semibold">
                              Hypothesis:
                            </span>{" "}
                            {idea.hypothesis}
                          </p>
                        )}

                        <button
                          type="button"
                          onClick={() =>
                            selectIdea(idea)
                          }
                          className="mt-3 inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-violet-700"
                        >
                          <Check className="h-4 w-4" />
                          Use this idea
                        </button>
                      </article>
                    );
                  })}
                </div>
              )}

              <div className="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-slate-600">
                  {selectedIdea ? (
                    <span>
                      Selected idea:{" "}
                      <span className="font-medium text-slate-900">
                        {selectedIdea.title}
                      </span>
                    </span>
                  ) : (
                    "Select a candidate idea before creating the workspace."
                  )}
                </div>

                <button
                  type="button"
                  onClick={() =>
                    void handleCreateWorkspace()
                  }
                  disabled={
                    !selectedIdea ||
                    selectedPaperIds.length === 0 ||
                    creating
                  }
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {creating ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FolderPlus className="h-4 w-4" />
                  )}

                  {creating
                    ? "Creating workspace..."
                    : workspace
                      ? "Create another workspace"
                      : "Create workspace"}
                </button>
              </div>
            </section>

            {workspace && (
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 border-b border-slate-100 pb-4">
                  <h2 className="text-xl font-semibold text-slate-900">
                    3. Generate a section
                  </h2>

                  <p className="mt-1 text-sm text-slate-500">
                    Choose the section you want to draft from workspace evidence.
                  </p>
                </div>

                <div className="grid gap-4 xl:grid-cols-[1fr_1fr_0.85fr]">
                  <div>
                    <label className="text-sm font-medium text-slate-800">
                      Content type
                    </label>

                    <div className="relative mt-2">
                      <select
                        value={contentType}
                        onChange={(event) => {
                          setContentType(
                            event.target
                              .value as WorkspaceContentType,
                          );

                          resetGeneratedOutput();
                        }}
                        className="w-full appearance-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 pr-10 text-sm text-slate-800 outline-none focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
                      >
                        {contentTypes.map((item) => (
                          <option
                            key={item.value}
                            value={item.value}
                          >
                            {item.label}
                          </option>
                        ))}
                      </select>

                      <ChevronDown className="pointer-events-none absolute right-3 top-3.5 h-4 w-4 text-slate-400" />
                    </div>

                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      {selectedContentType?.description}
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-800">
                      Target length: {targetWords} words
                    </label>

                    <input
                      type="range"
                      min="200"
                      max="1400"
                      step="100"
                      value={targetWords}
                      onChange={(event) => {
                        setTargetWords(
                          Number(event.target.value),
                        );

                        resetGeneratedOutput();
                      }}
                      className="mt-5 w-full accent-blue-600"
                    />

                    <div className="mt-2 flex justify-between text-xs text-slate-400">
                      <span>200</span>
                      <span>1400</span>
                    </div>
                  </div>

                  <div className="flex items-end">
                    <button
                      type="button"
                      onClick={() =>
                        void handleGenerate()
                      }
                      disabled={generating}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                    >
                      {generating ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4" />
                      )}

                      {generating
                        ? "Generating..."
                        : "Generate section"}
                    </button>
                  </div>
                </div>

                <div className="mt-5">
                  <label className="text-sm font-medium text-slate-800">
                    Additional generation instructions
                  </label>

                  <textarea
                    value={instructions}
                    onChange={(event) =>
                      setInstructions(
                        event.target.value,
                      )
                    }
                    rows={2}
                    placeholder="Example: Keep the proposed methodology practical for a final-year engineering project and identify evidence limitations."
                    className="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-800 outline-none focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
                  />
                </div>
              </section>
            )}

            {generation && (
              <>
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-4 border-b border-slate-100 pb-5 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <h2 className="text-xl font-semibold text-slate-900">
                        Generated {generation.title}
                      </h2>

                      <p className="mt-1 text-sm text-slate-500">
                        Edit the content before saving a version. Current draft:{" "}
                        {generatedWordCount} words.
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          downloadTextFile(
                            `${downloadBaseName}-${generation.title
                              .toLowerCase()
                              .replace(/\s+/g, "-")}.md`,
                            contentMarkdown,
                            "text/markdown;charset=utf-8",
                          )
                        }
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                      >
                        <Download className="h-4 w-4" />
                        Markdown
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          void handleSaveVersion()
                        }
                        disabled={saving}
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                      >
                        {saving ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Save className="h-4 w-4" />
                        )}

                        {saving
                          ? "Saving..."
                          : "Save version"}
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 xl:grid-cols-2">
                    <div>
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-semibold text-slate-900">
                          Editable research content
                        </h3>

                        <button
                          type="button"
                          onClick={() =>
                            copyText(contentMarkdown)
                          }
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                        >
                          <Copy className="h-3.5 w-3.5" />
                          Copy
                        </button>
                      </div>

                      <textarea
                        value={contentMarkdown}
                        onChange={(event) =>
                          setContentMarkdown(
                            event.target.value,
                          )
                        }
                        rows={20}
                        className="mt-3 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 font-mono text-sm leading-6 text-slate-800 outline-none focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-semibold text-slate-900">
                          Rendered preview
                        </h3>

                        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                          Markdown
                        </span>
                      </div>

                      <div className="mt-3 min-h-[480px] max-h-[640px] overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                        >
                          {contentMarkdown ||
                            "No generated content is available."}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-3 border-b border-slate-100 pb-5 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h2 className="flex items-center gap-2 text-xl font-semibold text-slate-900">
                        <Code2 className="h-5 w-5" />
                        LaTeX code
                      </h2>

                      <p className="mt-1 text-sm text-slate-500">
                        Generated from the same content draft and citation mapping.
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          copyText(latexCode)
                        }
                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        <Copy className="h-4 w-4" />
                        Copy LaTeX
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          downloadTextFile(
                            `${downloadBaseName}-${generation.title
                              .toLowerCase()
                              .replace(/\s+/g, "-")}.tex`,
                            latexCode,
                            "application/x-tex;charset=utf-8",
                          )
                        }
                        className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
                      >
                        <Download className="h-4 w-4" />
                        Download .tex
                      </button>
                    </div>
                  </div>

                  <textarea
                    value={latexCode}
                    onChange={(event) =>
                      setLatexCode(event.target.value)
                    }
                    rows={20}
                    spellCheck={false}
                    className="mt-5 w-full resize-y rounded-xl border border-slate-200 bg-slate-950 px-3 py-3 font-mono text-sm leading-6 text-emerald-200 outline-none focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                  />
                </section>

                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="mb-5 flex items-center gap-2">
                    <FileText className="h-5 w-5 text-slate-700" />

                    <h2 className="text-xl font-semibold text-slate-900">
                      Citation inventory
                    </h2>
                  </div>

                  {generation.citations.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
                      No citation metadata was returned for this generation.
                    </div>
                  ) : (
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                      {generation.citations.map(
                        (citation) => (
                          <article
                            key={citation.paper_id}
                            className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                          >
                            <p className="break-all text-xs font-semibold text-blue-700">
                              [{citation.paper_id}]
                            </p>

                            <p className="mt-1 font-mono text-xs text-violet-700">
                              {"\\cite{"}
                              {
                                citation.citation_key
                              }
                              {"}"}
                            </p>

                            <h3 className="mt-3 text-sm font-semibold text-slate-900">
                              {citation.title}
                            </h3>

                            <p className="mt-2 text-xs leading-5 text-slate-600">
                              {citation.authors.length >
                              0
                                ? citation.authors.join(
                                    ", ",
                                  )
                                : "Authors unavailable"}

                              {citation.year
                                ? ` · ${citation.year}`
                                : ""}
                            </p>

                            {citation.venue && (
                              <p className="mt-1 text-xs text-slate-500">
                                {citation.venue}
                              </p>
                            )}

                            {(citation.section_title ||
                              citation.page) && (
                              <p className="mt-2 text-xs text-slate-500">
                                {citation.section_title ||
                                  "Section"}

                                {citation.page
                                  ? ` · page ${citation.page}`
                                  : ""}
                              </p>
                            )}
                          </article>
                        ),
                      )}
                    </div>
                  )}
                </section>
              </>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}