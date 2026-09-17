"use client";

import {
  useState,
  type FormEvent,
} from "react";
import {
  BookOpen,
  ExternalLink,
  Globe,
  Loader2,
  Search,
} from "lucide-react";

import { searchDiscoveryPapers } from "@/lib/api";
import type { PaperMetadata } from "@/lib/types";


export function GlobalLiteratureSearch() {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(5);
  const [results, setResults] = useState<PaperMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const value = query.trim();

    if (!value || loading) {
      return;
    }

    try {
      setLoading(true);
      setError("");

      const data = await searchDiscoveryPapers(
        value,
        limit,
      );

      setResults(data);
    } catch (requestError) {
      setResults([]);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Global search failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-3xl border border-indigo-100 bg-gradient-to-b from-indigo-50/40 to-white p-8 shadow-sm">
      <div className="mb-6 flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-700 shadow-sm">
          <Globe className="h-6 w-6" />
        </div>

        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              Global Literature Discovery
            </h1>

            <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-800">
              arXiv + OpenAlex
            </span>
          </div>

          <p className="mt-1 text-sm leading-6 text-slate-600">
            Discover open-access papers, preprints,
            citation counts, and DOIs worldwide.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-3 sm:flex-row"
      >
        <input
          value={query}
          onChange={(event) =>
            setQuery(event.target.value)
          }
          placeholder="Search worldwide literature by title, keywords, or research field..."
          className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
        />

        <select
          value={limit}
          onChange={(event) =>
            setLimit(Number(event.target.value))
          }
          aria-label="Results per source"
          className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm font-medium text-slate-700 outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
        >
          <option value={3}>3 per source</option>
          <option value={5}>5 per source</option>
          <option value={10}>10 per source</option>
        </select>

        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? (
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

      {error && (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <div className="mt-6 space-y-4 border-t border-slate-100 pt-6">
          <h3 className="text-sm font-semibold text-slate-900">
            Global Results ({results.length} found)
          </h3>

          <div className="space-y-3">
            {results.map((paper, index) => (
              <article
                key={`${paper.source_id}-${index}`}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
              >
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span
                    className={[
                      "rounded-full px-2.5 py-0.5",
                      "text-xs font-semibold",
                      paper.source === "arXiv"
                        ? "bg-rose-100 text-rose-800"
                        : "bg-emerald-100 text-emerald-800",
                    ].join(" ")}
                  >
                    {paper.source}
                  </span>

                  {paper.year && (
                    <span className="text-xs font-medium text-slate-500">
                      {paper.year}
                    </span>
                  )}

                  {paper.venue && (
                    <span className="max-w-xs truncate text-xs text-slate-500">
                      • {paper.venue}
                    </span>
                  )}

                  {paper.citation_count !== undefined &&
                    paper.citation_count > 0 && (
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                        {paper.citation_count} citations
                      </span>
                    )}
                </div>

                <h4 className="text-base font-semibold text-slate-900">
                  {paper.title}
                </h4>

                {paper.authors?.length > 0 && (
                  <p className="mt-1 text-xs text-slate-500">
                    {paper.authors.slice(0, 4).join(", ")}
                    {paper.authors.length > 4
                      ? ` +${paper.authors.length - 4} more`
                      : ""}
                  </p>
                )}

                <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-slate-600">
                  {paper.abstract}
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-4 border-t border-slate-100 pt-3">
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
                      href={
                        paper.doi.startsWith("http")
                          ? paper.doi
                          : `https://doi.org/${paper.doi}`
                      }
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      DOI link
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}