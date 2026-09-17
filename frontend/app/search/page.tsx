"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import { Search, FileText, ArrowRight, Globe, ExternalLink, BookOpen, Loader2 } from "lucide-react";
import Link from "next/link";
import { searchDiscoveryPapers } from "@/lib/api";
import { PaperMetadata } from "@/lib/types";

const PAPERS = [
  {
    id: "1",
    title: "The Kepler end-to-end data pipeline from photons to planets",
    filename: "The_Kepler_end-to-end_data_pipeline_from_photons_to_planets.pdf",
    year: 2024,
    tags: ["dataset", "pipeline", "astronomy", "photons", "planets"],
  },
  {
    id: "2",
    title: "AstroFusion: A GAN-Augmented Approach for Exoplanet Detection",
    filename: "AstroFusion_A_GAN-Augmented_Approach_for_Exoplanet_Detection.pdf",
    year: 2023,
    tags: ["architecture", "gan", "exoplanet", "detection", "augmentation"],
  },
  {
    id: "3",
    title: "A Study of Light Intensity of Stars for Exoplanet Detection",
    filename: "A_Study_of_Light_Intensity_of_Stars_for_Exoplanet_Detection.pdf",
    year: 2026,
    tags: ["light intensity", "stars", "exoplanet", "analysis", "dataset"],
  },
  {
    id: "4",
    title: "Statistical and Machine Learning Perspectives on Exoplanet Detection",
    filename: "Statistical_and_Machine_Learning_Perspectives_on_Exoplanet_Detection.pdf",
    year: 2026,
    tags: ["machine learning", "statistics", "review", "detection", "survey"],
  },
  {
    id: "5",
    title: "AI-Driven Research Assistant for Automated Summarization of Generative AI Flaws",
    filename: "AI-Driven-Research-Assistant-for-Automated-Summarization-of-Generative-AI-Flaws.pdf",
    year: 2026,
    tags: ["ai assistant", "summarization", "review", "limitations", "automation"],
  },
  {
    id: "6",
    title: "Transformative Automation in Scientific Literature Review",
    filename: "Transformative_Automation_in_Scientific_Literature_Review.pdf",
    year: 2026,
    tags: ["literature review", "automation", "research", "workflow", "review"],
  },
];

export default function SearchPage() {
  // --- Local Search State (Existing) ---
  const [query, setQuery] = useState("");

  // --- Global Discovery Search State (New) ---
  const [globalQuery, setGlobalQuery] = useState("");
  const [discoveryLimit, setDiscoveryLimit] = useState(5);
  const [discoveryResults, setDiscoveryResults] = useState<PaperMetadata[]>([]);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  const filteredPapers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return PAPERS;

    return PAPERS.filter((paper) => {
      const haystack = `${paper.title} ${paper.filename} ${paper.year} ${paper.tags.join(" ")}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [query]);

  const handleDiscoverySearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!globalQuery.trim()) return;

    setIsDiscovering(true);
    setDiscoveryError(null);

    try {
      const results = await searchDiscoveryPapers(globalQuery.trim(), discoveryLimit);
      setDiscoveryResults(results);
    } catch (err: any) {
      setDiscoveryError(err.message || "Failed to search global academic literature.");
    } finally {
      setIsDiscovering(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-8">
        
        {/* ========================================================= */}
        {/* 1. GLOBAL LITERATURE DISCOVERY (Module 5: arXiv & OpenAlex) */}
        {/* ========================================================= */}
        <section className="rounded-3xl border border-indigo-100 bg-gradient-to-b from-indigo-50/40 to-white p-8 shadow-sm">
          <div className="mb-6 flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-700 shadow-sm">
              <Globe className="h-6 w-6" />
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                  Global Literature Discovery
                </h1>
                <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-800">
                  arXiv + OpenAlex
                </span>
              </div>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                Discover open-access papers, preprints, citation counts, and DOIs worldwide.
              </p>
            </div>
          </div>

          <form onSubmit={handleDiscoverySearch} className="flex flex-col gap-3 sm:flex-row">
            <input
              value={globalQuery}
              onChange={(e) => setGlobalQuery(e.target.value)}
              placeholder="Search worldwide literature by title, keywords, or research field..."
              className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100"
            />

            <select
              value={discoveryLimit}
              onChange={(e) => setDiscoveryLimit(Number(e.target.value))}
              aria-label="Number of search results per repository"
              className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm font-medium text-slate-700 outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
            >
              <option value={3}>3 per source</option>
              <option value={5}>5 per source</option>
              <option value={10}>10 per source</option>
            </select>

            <button
              type="submit"
              disabled={isDiscovering}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-60"
            >
              {isDiscovering ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Search Global
                </>
              )}
            </button>
          </form>

          {/* Discovery Error */}
          {discoveryError && (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {discoveryError}
            </div>
          )}

          {/* Discovery Results List */}
          {discoveryResults.length > 0 && (
            <div className="mt-6 space-y-4 pt-6 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">
                  Global Results ({discoveryResults.length} found)
                </h3>
              </div>

              <div className="space-y-3">
                {discoveryResults.map((paper, idx) => (
                  <div
                    key={`${paper.source_id}-${idx}`}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          paper.source === "arXiv"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-emerald-100 text-emerald-800"
                        }`}
                      >
                        {paper.source}
                      </span>
                      {paper.year && (
                        <span className="text-xs font-medium text-slate-500">
                          {paper.year}
                        </span>
                      )}
                      {paper.venue && (
                        <span className="text-xs text-slate-500 truncate max-w-xs">
                          • {paper.venue}
                        </span>
                      )}
                      {paper.citation_count !== undefined && paper.citation_count > 0 && (
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                          {paper.citation_count} citations
                        </span>
                      )}
                    </div>

                    <h4 className="text-base font-semibold text-slate-900">
                      {paper.title}
                    </h4>

                    {paper.authors && paper.authors.length > 0 && (
                      <p className="mt-1 text-xs text-slate-500">
                        {paper.authors.slice(0, 4).join(", ")}
                        {paper.authors.length > 4 ? ` +${paper.authors.length - 4} more` : ""}
                      </p>
                    )}

                    <p className="mt-2 text-xs leading-relaxed text-slate-600 line-clamp-2">
                      {paper.abstract}
                    </p>

                    <div className="mt-3 flex items-center gap-4 border-t border-slate-100 pt-3">
                      {paper.pdf_url && (
                        <a
                          href={paper.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                        >
                          <BookOpen className="h-3.5 w-3.5" />
                          View PDF
                        </a>
                      )}
                      {paper.doi && (
                        <a
                          href={paper.doi.startsWith("http") ? paper.doi : `https://doi.org/${paper.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          DOI Link
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ========================================================= */}
        {/* 2. LOCAL SEMANTIC SEARCH (Original Untouched Section)     */}
        {/* ========================================================= */}
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-6 flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
              <Search className="h-6 w-6" />
            </div>

            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
                Corpus semantic search
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Search available papers by topic, method, dataset, or keyword.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search papers by topic, dataset, method..."
              className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
            />

            <button
              type="button"
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-slate-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-blue-700"
            >
              <Search className="h-4 w-4" />
              Search
            </button>
          </div>
        </section>

        {/* ========================================================= */}
        {/* 3. AVAILABLE PAPERS GRID (Original Untouched Section)     */}
        {/* ========================================================= */}
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-900">
              Available papers
            </h2>
            <p className="text-sm text-slate-500">
              {filteredPapers.length} paper{filteredPapers.length === 1 ? "" : "s"} found
            </p>
          </div>

          {filteredPapers.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 px-5 py-10 text-center text-sm text-slate-500">
              No matching papers found.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredPapers.map((paper) => (
                <Link
                  key={paper.id}
                  href={`/papers/${paper.id}`}
                  className="group rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-blue-200 hover:bg-blue-50"
                >
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-blue-700 shadow-sm">
                    <FileText className="h-5 w-5" />
                  </div>

                  <h3 className="line-clamp-2 break-words text-base font-semibold text-slate-900">
                    {paper.title}
                  </h3>

                  <p className="mt-2 break-all text-sm text-slate-500">
                    {paper.filename}
                  </p>

                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-xs text-slate-400">{paper.year}</span>
                    <span className="inline-flex items-center gap-1 text-sm font-medium text-blue-700">
                      Open
                      <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

      </div>
    </AppShell>
  );
}