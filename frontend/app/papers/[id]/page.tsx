"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  useCallback,
  useEffect,
  useState,
  type KeyboardEvent,
} from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeftCircle,
  BarChart3,
  Database,
  FileText,
  FlaskConical,
  Lightbulb,
  Search,
  Sparkles,
  Tag,
  Target,
} from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import {
  askPaper,
  extractPaper,
  getExtraction,
  getPaper,
  parsePaper,
  searchPaper,
  type ExtractionResponse,
} from "@/lib/api";
import type {
  AnswerSource,
  ChunkResult,
  Extraction,
  Paper,
} from "@/lib/types";


type SearchPaperResponse =
  | ChunkResult[]
  | {
      query?: string;
      top_k?: number;
      count?: number;
      results?: ChunkResult[];
    };


function getErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}


function normalizeExtraction(
  data: ExtractionResponse | null,
): Extraction | null {
  if (!data) {
    return null;
  }

  if (
    typeof data === "object" &&
    data !== null &&
    "extraction" in data
  ) {
    return data.extraction || null;
  }

  return data as Extraction;
}


function normalizeSearchResults(
  data: SearchPaperResponse,
): ChunkResult[] {
  if (Array.isArray(data)) {
    return data;
  }

  if (
    data &&
    typeof data === "object" &&
    Array.isArray(data.results)
  ) {
    return data.results;
  }

  return [];
}


function textValue(
  value: string | string[] | null | undefined,
): string {
  if (Array.isArray(value)) {
    return value
      .filter(Boolean)
      .join(", ")
      .trim();
  }

  return typeof value === "string"
    ? value.trim()
    : "";
}


export default function PaperDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [paper, setPaper] = useState<Paper | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [results, setResults] = useState<ChunkResult[]>([]);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [answerSources, setAnswerSources] = useState<AnswerSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [answering, setAnswering] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [errorText, setErrorText] = useState("");

  const loadPaper = useCallback(async () => {
    if (!id) {
      return;
    }

    try {
      setLoading(true);
      setErrorText("");

      const [paperData, extractionData] = await Promise.all([
        getPaper(id),
        getExtraction(id).catch(() => null),
      ]);

      setPaper(paperData);
      setExtraction(normalizeExtraction(extractionData));
    } catch (error) {
      console.error("Failed to load paper:", error);
      setErrorText(
        getErrorMessage(error, "Failed to load the paper."),
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadPaper();
  }, [loadPaper]);

  async function handleParse() {
    if (!id || parsing || extracting) {
      return;
    }

    try {
      setParsing(true);
      setErrorText("");

      await parsePaper(id);
      await loadPaper();
    } catch (error) {
      console.error("Parsing failed:", error);
      setErrorText(
        getErrorMessage(error, "Parsing failed."),
      );
    } finally {
      setParsing(false);
    }
  }

  async function handleExtract() {
    if (!id || extracting || parsing) {
      return;
    }

    try {
      setExtracting(true);
      setErrorText("");

      const response = await extractPaper(id);
      const nextExtraction = normalizeExtraction(response);

      setExtraction(nextExtraction);
      await loadPaper();
    } catch (error) {
      console.error("Extraction failed:", error);
      setErrorText(
        getErrorMessage(error, "Extraction failed."),
      );
    } finally {
      setExtracting(false);
    }
  }

  async function handleSearch() {
    const value = query.trim();

    if (!id || !value || searching) {
      return;
    }

    try {
      setSearching(true);
      setErrorText("");
      setAnswer("");
      setAnswerSources([]);

      const response = await searchPaper(id, value);

      setResults(
        normalizeSearchResults(
          response as SearchPaperResponse,
        ),
      );
    } catch (error) {
      console.error("Search failed:", error);
      setErrorText(
        getErrorMessage(error, "Search failed."),
      );
    } finally {
      setSearching(false);
    }
  }

  async function handleAskAI() {
    const value = query.trim();

    if (!id || !value || answering) {
      return;
    }

    try {
      setAnswering(true);
      setErrorText("");
      setResults([]);

      const response = await askPaper(id, value, 5);

      setAnswer(
        response.answer || "No answer was generated.",
      );

      setAnswerSources(
        response.sources || [],
      );
    } catch (error) {
      console.error("AI answer failed:", error);
      setErrorText(
        getErrorMessage(
          error,
          "AI answer generation failed.",
        ),
      );
    } finally {
      setAnswering(false);
    }
  }

  function handleQueryKeyDown(
    event: KeyboardEvent<HTMLInputElement>,
  ) {
    if (event.key === "Enter") {
      event.preventDefault();
      void handleAskAI();
    }
  }

  const extractedCards = [
    {
      label: "Objective",
      value: extraction?.objective || paper?.objective,
      icon: Target,
      tone: "text-blue-600",
    },
    {
      label: "Methodology",
      value: extraction?.methodology || paper?.methodology,
      icon: FlaskConical,
      tone: "text-violet-600",
    },
    {
      label: "Dataset",
      value: extraction?.dataset || paper?.dataset,
      icon: Database,
      tone: "text-cyan-600",
    },
    {
      label: "Evaluation metric",
      value:
        extraction?.evaluation_metric ||
        paper?.evaluation_metric,
      icon: BarChart3,
      tone: "text-emerald-600",
    },
    {
      label: "Limitations",
      value:
        extraction?.limitations ||
        paper?.limitations,
      icon: Search,
      tone: "text-orange-600",
    },
    {
      label: "Future work",
      value:
        extraction?.future_work ||
        paper?.future_work,
      icon: ArrowLeftCircle,
      tone: "text-rose-600",
    },
    {
      label: "Research gap",
      value:
        extraction?.research_gap ||
        paper?.research_gap,
      icon: Lightbulb,
      tone: "text-amber-600",
    },
    {
      label: "Findings",
      value:
        extraction?.findings ||
        paper?.findings,
      icon: Sparkles,
      tone: "text-indigo-600",
    },
    {
      label: "Keywords",
      value:
        extraction?.keywords ||
        paper?.keywords,
      icon: Tag,
      tone: "text-slate-600",
    },
  ];

  return (
    <AppShell>
      <div className="space-y-8">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm transition hover:bg-slate-50"
          >
            <ArrowLeftCircle className="h-4 w-4" />
            Back to dashboard
          </Link>
        </div>

        {errorText && (
          <div
            role="alert"
            className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {errorText}
          </div>
        )}

        {loading ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-500 shadow-sm">
            Loading paper...
          </div>
        ) : !paper ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-500 shadow-sm">
            Paper not found.
          </div>
        ) : (
          <>
            <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <div className="mb-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                    Paper detail
                  </div>

                  <h1 className="break-words text-3xl font-semibold tracking-tight text-slate-900">
                    {paper.title || "Untitled paper"}
                  </h1>

                  <p className="mt-3 break-words text-sm leading-6 text-slate-600">
                    {paper.filename}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
                    {paper.authors && paper.authors.length > 0 && (
                      <span className="rounded-full bg-slate-100 px-3 py-1">
                        {paper.authors.join(", ")}
                      </span>
                    )}

                    {paper.year && (
                      <span className="rounded-full bg-slate-100 px-3 py-1">
                        {paper.year}
                      </span>
                    )}

                    {paper.keywords &&
                      paper.keywords.length > 0 && (
                        <span className="rounded-full bg-slate-100 px-3 py-1">
                          {paper.keywords.length} keyword
                          {paper.keywords.length === 1 ? "" : "s"}
                        </span>
                      )}
                  </div>

                  {paper.abstract && (
                    <div className="mt-6 rounded-2xl bg-slate-50 p-5">
                      <h2 className="text-sm font-semibold text-slate-900">
                        Abstract
                      </h2>

                      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-slate-600">
                        {paper.abstract}
                      </p>
                    </div>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:w-[320px] lg:grid-cols-1">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">
                      Year
                    </p>

                    <p className="mt-2 text-lg font-semibold text-slate-900">
                      {paper.year || "—"}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">
                      Status
                    </p>

                    <p className="mt-2 text-lg font-semibold capitalize text-slate-900">
                      {paper.status || "unknown"}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => void handleParse()}
                    disabled={parsing || extracting}
                    className="rounded-2xl bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {parsing ? "Parsing..." : "Parse paper"}
                  </button>

                  <button
                    type="button"
                    onClick={() => void handleExtract()}
                    disabled={extracting || parsing}
                    className="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {extracting
                      ? "Extracting..."
                      : "Run extraction"}
                  </button>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    Structured extraction
                  </h2>

                  <p className="text-sm text-slate-500">
                    Research fields extracted from this paper. Module 8 uses these fields for corpus-level gap analysis.
                  </p>
                </div>

                {paper.status !== "extracted" && (
                  <p className="text-xs text-amber-700">
                    Run extraction to populate all available fields.
                  </p>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {extractedCards.map((item) => {
                  const Icon = item.icon;
                  const value = textValue(item.value);

                  return (
                    <div
                      key={item.label}
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                    >
                      <div className="mb-3 flex items-center gap-3">
                        <div className="rounded-xl bg-white p-2 shadow-sm">
                          <Icon
                            className={`h-4 w-4 ${item.tone}`}
                          />
                        </div>

                        <h3 className="font-semibold text-slate-900">
                          {item.label}
                        </h3>
                      </div>

                      <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">
                        {value || "Not available from extraction."}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">
                  Ask the paper
                </h2>

                <p className="text-sm text-slate-500">
                  Retrieve evidence from this paper, then ask an AI question grounded in the retrieved passages.
                </p>
              </div>

              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  value={query}
                  onChange={(event) =>
                    setQuery(event.target.value)
                  }
                  onKeyDown={handleQueryKeyDown}
                  placeholder="e.g. What dataset is used and why?"
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />

                <button
                  type="button"
                  onClick={() => void handleAskAI()}
                  disabled={answering || !query.trim()}
                  className="rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {answering ? "Thinking..." : "Ask AI"}
                </button>

                <button
                  type="button"
                  onClick={() => void handleSearch()}
                  disabled={searching || !query.trim()}
                  className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {searching ? "Searching..." : "Search"}
                </button>
              </div>

              {answer && (
                <div className="mt-6 rounded-2xl border border-blue-100 bg-blue-50 p-6">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-blue-600" />

                    <h3 className="text-lg font-semibold text-slate-900">
                      AI research assistant
                    </h3>
                  </div>

                  <div className="ai-answer mt-4 break-words text-sm leading-7 text-slate-700">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {answer}
                    </ReactMarkdown>
                  </div>

                  {answerSources.length > 0 && (
                    <div className="mt-5 border-t border-blue-100 pt-4">
                      <h4 className="text-sm font-semibold text-slate-900">
                        Retrieved sources
                      </h4>

                      <div className="mt-2 space-y-1 text-xs text-slate-600">
                        {answerSources.map(
                          (source, index) => (
                            <p
                              key={`${source.paper_title || "paper"}-${source.page || "page"}-${index}`}
                            >
                              Source{" "}
                              {source.source_number ||
                                index + 1}
                              :{" "}
                              {source.paper_title || "Paper"}
                              {source.page
                                ? `, page ${source.page}`
                                : ""}
                              {source.section_title
                                ? `, ${source.section_title}`
                                : ""}
                            </p>
                          ),
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-6 space-y-4">
                {results.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                    No search results yet. Enter a query and click
                    Search to retrieve passages from this paper.
                  </div>
                ) : (
                  results.map((chunk) => (
                    <div
                      key={chunk.id}
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                    >
                      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span className="rounded-full bg-white px-3 py-1">
                          {chunk.section_title || "Section"}
                        </span>

                        <span className="rounded-full bg-white px-3 py-1">
                          Page{" "}
                          {chunk.page ??
                            chunk.page_number ??
                            "—"}
                        </span>

                        {typeof chunk.score === "number" && (
                          <span className="rounded-full bg-blue-50 px-3 py-1 text-blue-700">
                            Score {chunk.score.toFixed(2)}
                          </span>
                        )}
                      </div>

                      <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700">
                        {chunk.text}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-3xl border border-violet-100 bg-violet-50 p-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-violet-950">
                    Continue with corpus-level research tools
                  </h2>

                  <p className="mt-1 max-w-2xl text-sm leading-6 text-violet-800">
                    Once this paper has been extracted, select it with other relevant papers in Research Gap & Ideation or Manuscript Composer.
                  </p>
                </div>

                <div className="flex flex-wrap gap-3">
                  <Link
                    href="/ideation"
                    className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700"
                  >
                    Open Ideation
                  </Link>

                  <Link
                    href="/manuscript"
                    className="rounded-xl border border-violet-200 bg-white px-4 py-2 text-sm font-medium text-violet-800 transition hover:bg-violet-100"
                  >
                    Open Composer
                  </Link>
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}