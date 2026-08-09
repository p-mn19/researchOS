"use client";

import { FormEvent, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import { semanticSearch } from "@/lib/api";
import { SearchResult } from "@/lib/types";
import { Search, Loader2 } from "lucide-react";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchedQuery, setSearchedQuery] = useState("");

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setError("Enter a search query.");
      setResults([]);
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResults([]);

      const response = await semanticSearch(trimmedQuery, undefined, 5);

      setResults(response.results || []);
      setSearchedQuery(response.query);
    } catch (err) {
      console.error(err);
      setError("Search failed. Make sure the backend is running.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-6 flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
              <Search className="h-6 w-6" />
            </div>

            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                Global semantic search
              </h1>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Search across the indexed research-paper corpus.
              </p>
            </div>
          </div>

          <form
            onSubmit={handleSearch}
            className="flex flex-col gap-3 sm:flex-row"
          >
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask something about your research papers..."
              className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
            />

            <button
              type="submit"
              disabled={loading}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-slate-900 px-6 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Search
                </>
              )}
            </button>
          </form>

          {error ? (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}
        </section>

        {searchedQuery && !loading ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  Search results
                </h2>
                <p className="text-sm text-slate-500">
                  Results for:{" "}
                  <span className="font-medium text-slate-700">
                    “{searchedQuery}”
                  </span>
                </p>
              </div>

              <span className="text-sm text-slate-500">
                {results.length} result{results.length === 1 ? "" : "s"}
              </span>
            </div>

            {results.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">
                No matching results were found in the uploaded papers.
              </div>
            ) : (
              <div className="space-y-4">
                {results.map((result, index) => (
                  <article
                    key={`${result.paper_id}-${result.page ?? "page"}-${index}`}
                    className="min-w-0 rounded-2xl border border-slate-200 bg-slate-50 p-5"
                  >
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      {result.section_title ? (
                        <span className="rounded-full bg-white px-3 py-1 text-xs text-slate-600">
                          {result.section_title}
                        </span>
                      ) : null}

                      {result.page !== undefined ? (
                        <span className="rounded-full bg-white px-3 py-1 text-xs text-slate-600">
                          Page {result.page}
                        </span>
                      ) : null}

                      {result.score !== undefined ? (
                        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700">
                          Score {result.score.toFixed(2)}
                        </span>
                      ) : null}
                    </div>

                    <h3 className="mt-4 break-words text-base font-semibold text-slate-900">
                      {result.paper_title}
                    </h3>

                    {result.filename ? (
                      <p className="mt-1 break-all text-xs text-slate-500">
                        {result.filename}
                      </p>
                    ) : null}

                    <p className="mt-4 break-words whitespace-pre-wrap text-sm leading-7 text-slate-700">
                      {result.text}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}