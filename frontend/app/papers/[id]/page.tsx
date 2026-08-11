"use client";

import { useEffect, useState, type KeyboardEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeftCircle,
  Database,
  FileText,
  FlaskConical,
  Search,
  Sparkles,
} from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import {
  extractPaper,
  getExtraction,
  getPaper,
  parsePaper,
  searchPaper,
} from "@/lib/api";
import { ChunkResult, Extraction, Paper } from "@/lib/types";


type ExtractionResponse = Extraction | { extraction?: Extraction } | null;

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

function normalizeExtraction(
  data: ExtractionResponse,
): Extraction | null {
  if (!data) {
    return null;
  }

  if ("extraction" in data && data.extraction) {
    return data.extraction;
  }

  return (data as Extraction) || null;
}

export default function PaperDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [paper, setPaper] = useState<Paper | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [results, setResults] = useState<ChunkResult[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadPaper() {
    if (!id) return;

    try {
      setLoading(true);
      setErrorMessage("");

      const [paperData, extractionData] = await Promise.all([
        getPaper(id),
        getExtraction(id).catch(() => null),
      ]);

      setPaper(paperData as Paper);
      setExtraction(
        normalizeExtraction(extractionData as ExtractionResponse),
      );
    } catch (error) {
      console.error("Failed to load paper:", error);
      setErrorMessage(
        getErrorMessage(error, "Failed to load the paper."),
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPaper();
  }, [id]);

  async function handleParse() {
    if (!id || parsing || extracting) return;

    try {
      setParsing(true);
      setErrorMessage("");
      await parsePaper(id);
      await loadPaper();
    } catch (error) {
      console.error("Parsing failed:", error);
      setErrorMessage(getErrorMessage(error, "Parsing failed."));
    } finally {
      setParsing(false);
    }
  }

  async function handleExtract() {
    if (!id || extracting || parsing) return;

    try {
      setExtracting(true);
      setErrorMessage("");

      // Parse first so the backend has the latest cleaned text.
      await parsePaper(id);

      // Extract only after parsing succeeds.
      const extractionResponse = await extractPaper(id);
      const normalized = normalizeExtraction(
        extractionResponse as ExtractionResponse,
      );

      setExtraction(normalized);
      await loadPaper();
    } catch (error) {
      console.error("Extraction failed:", error);
      setErrorMessage(getErrorMessage(error, "Extraction failed."));
    } finally {
      setExtracting(false);
    }
  }

  async function handleSearch() {
    const trimmedQuery = query.trim();

    if (!id || !trimmedQuery || searching) return;

    try {
      setSearching(true);
      setErrorMessage("");

      const data = await searchPaper(id, trimmedQuery);
      setResults(data as ChunkResult[]);
    } catch (error) {
      console.error("Search failed:", error);
      setErrorMessage(getErrorMessage(error, "Search failed."));
    } finally {
      setSearching(false);
    }
  }

  function handleSearchKeyDown(
    event: KeyboardEvent<HTMLInputElement>,
  ) {
    if (event.key === "Enter") {
      void handleSearch();
    }
  }

  const extractedCards = [
    { label: "Objective", value: extraction?.objective, icon: FlaskConical },
    { label: "Methodology", value: extraction?.methodology, icon: Database },
    { label: "Dataset", value: extraction?.dataset, icon: FileText },
    { label: "Metric", value: extraction?.evaluation_metric, icon: Sparkles },
    { label: "Limitations", value: extraction?.limitations, icon: Search },
    {
      label: "Future work",
      value: extraction?.future_work,
      icon: ArrowLeftCircle,
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

        {errorMessage && (
          <div
            role="alert"
            className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {errorMessage}
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

                  <h1 className="wrap-break-word text-3xl font-semibold tracking-tight text-slate-900">
                    {paper.title || "Untitled paper"}
                  </h1>

                  <p className="mt-3 wrap-break-word text-sm leading-6 text-slate-600">
                    {paper.filename}
                  </p>

                  {paper.abstract && (
                    <div className="mt-6 rounded-2xl bg-slate-50 p-5">
                      <h2 className="text-sm font-semibold text-slate-900">
                        Abstract
                      </h2>
                      <p className="mt-2 whitespace-pre-wrap wrap-break-word text-sm leading-7 text-slate-600">
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
                    {extracting ? "Parsing and extracting..." : "Run extraction"}
                  </button>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">
                  Structured extraction
                </h2>
                <p className="text-sm text-slate-500">
                  Key fields extracted from the paper
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {extractedCards.map((item) => {
                  const Icon = item.icon;

                  return (
                    <div
                      key={item.label}
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                    >
                      <div className="mb-3 flex items-center gap-3">
                        <div className="rounded-xl bg-white p-2 shadow-sm">
                          <Icon className="h-4 w-4 text-blue-600" />
                        </div>
                        <h3 className="font-semibold text-slate-900">
                          {item.label}
                        </h3>
                      </div>

                      <p className="whitespace-pre-wrap wrap-break-word text-sm leading-6 text-slate-600">
                        {item.value || "Not extracted yet."}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">
                  Semantic search
                </h2>
                <p className="text-sm text-slate-500">
                  Search relevant chunks from this paper
                </p>
              </div>

              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={handleSearchKeyDown}
                  placeholder="e.g. What dataset is used in this paper?"
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />

                <button
                  type="button"
                  onClick={() => void handleSearch()}
                  disabled={searching || !query.trim()}
                  className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {searching ? "Searching..." : "Search"}
                </button>
              </div>

              <div className="mt-6 space-y-4">
                {results.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                    No search results yet.
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
                          Page {chunk.page ?? "—"}
                        </span>

                        {typeof chunk.score === "number" && (
                          <span className="rounded-full bg-blue-50 px-3 py-1 text-blue-700">
                            Score {chunk.score.toFixed(2)}
                          </span>
                        )}
                      </div>

                      <p className="whitespace-pre-wrap wrap-break-word text-sm leading-7 text-slate-700">
                        {chunk.text}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}