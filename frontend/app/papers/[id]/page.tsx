"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/layout/app_shell";
import { extractPaper, getExtraction, getPaper, parsePaper, searchPaper } from "@/lib/api";
import { ChunkResult, Extraction, Paper } from "@/lib/types";
import {
  FileText,
  Sparkles,
  Search,
  Database,
  FlaskConical,
  ArrowLeftCircle,
} from "lucide-react";
import Link from "next/link";

export default function PaperDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [paper, setPaper] = useState<Paper | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [results, setResults] = useState<ChunkResult[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [extracting, setExtracting] = useState(false);

  async function loadPaper() {
    try {
      setLoading(true);
      const [paperData, extractionData] = await Promise.all([
        getPaper(id),
        getExtraction(id).catch(() => null),
      ]);

      setPaper(paperData);
      setExtraction(extractionData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (id) loadPaper();
  }, [id]);

  async function handleParse() {
    try {
      setParsing(true);
      await parsePaper(id);
      await loadPaper();
    } catch (err) {
      console.error(err);
      alert("Parsing failed");
    } finally {
      setParsing(false);
    }
  }

  async function handleExtract() {
    try {
      setExtracting(true);
      await extractPaper(id);
      await loadPaper();
    } catch (err) {
      console.error(err);
      alert("Extraction failed");
    } finally {
      setExtracting(false);
    }
  }

  async function handleSearch() {
    if (!query.trim()) return;
    try {
      setSearching(true);
      const data = await searchPaper(id, query);
      setResults(data);
    } catch (err) {
      console.error(err);
      alert("Search failed");
    } finally {
      setSearching(false);
    }
  }

  const extractedCards = [
    { label: "Objective", value: extraction?.objective, icon: FlaskConical },
    { label: "Methodology", value: extraction?.methodology, icon: Database },
    { label: "Dataset", value: extraction?.dataset, icon: FileText },
    { label: "Metric", value: extraction?.evaluation_metric, icon: Sparkles },
    { label: "Limitations", value: extraction?.limitations, icon: Search },
    { label: "Future work", value: extraction?.future_work, icon: ArrowLeftCircle },
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
                  <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                    {paper.title || "Untitled paper"}
                  </h1>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{paper.filename}</p>

                  {paper.abstract && (
                    <div className="mt-6 rounded-2xl bg-slate-50 p-5">
                      <h2 className="text-sm font-semibold text-slate-900">Abstract</h2>
                      <p className="mt-2 text-sm leading-7 text-slate-600">{paper.abstract}</p>
                    </div>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:w-[320px] lg:grid-cols-1">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">Year</p>
                    <p className="mt-2 text-lg font-semibold text-slate-900">{paper.year || "—"}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">Status</p>
                    <p className="mt-2 text-lg font-semibold capitalize text-slate-900">{paper.status}</p>
                  </div>
                  <button
                    onClick={handleParse}
                    disabled={parsing}
                    className="rounded-2xl bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:bg-slate-300"
                  >
                    {parsing ? "Parsing..." : "Parse paper"}
                  </button>
                  <button
                    onClick={handleExtract}
                    disabled={extracting}
                    className="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:bg-slate-300"
                  >
                    {extracting ? "Extracting..." : "Run extraction"}
                  </button>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">Structured extraction</h2>
                <p className="text-sm text-slate-500">Key fields extracted from the paper</p>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {extractedCards.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.label} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                      <div className="mb-3 flex items-center gap-3">
                        <div className="rounded-xl bg-white p-2 shadow-sm">
                          <Icon className="h-4 w-4 text-blue-600" />
                        </div>
                        <h3 className="font-semibold text-slate-900">{item.label}</h3>
                      </div>
                      <p className="text-sm leading-6 text-slate-600">
                        {item.value || "Not extracted yet."}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">Semantic search</h2>
                <p className="text-sm text-slate-500">Search relevant chunks from this paper</p>
              </div>

              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. What dataset is used in this paper?"
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />
                <button
                  onClick={handleSearch}
                  disabled={searching}
                  className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:bg-slate-300"
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
                    <div key={chunk.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span className="rounded-full bg-white px-3 py-1">
                          {chunk.section_title || "Section"}
                        </span>
                        <span className="rounded-full bg-white px-3 py-1">
                          Page {chunk.page || "—"}
                        </span>
                        {typeof chunk.score === "number" && (
                          <span className="rounded-full bg-blue-50 px-3 py-1 text-blue-700">
                            Score {chunk.score.toFixed(2)}
                          </span>
                        )}
                      </div>
                      <p className="text-sm leading-7 text-slate-700">{chunk.text}</p>
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