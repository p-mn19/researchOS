"use client";

import {
  ExternalLink,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from "lucide-react";
import { PaperMetadata } from "@/lib/types";

type RecommendedPapersProps = {
  papers: PaperMetadata[];
  loading?: boolean;
  query?: string;
};

function getPaperTitle(paper: PaperMetadata) {
  return paper.title || "Untitled paper";
}

function getAuthors(paper: PaperMetadata) {
  if (!paper.authors) return "Authors unavailable";

  if (Array.isArray(paper.authors)) {
    return paper.authors.slice(0, 3).join(", ");
  }

  return String(paper.authors);
}

function getReason(
  paper: PaperMetadata,
  query: string
) {
  const title = getPaperTitle(paper);

  const queryWords = query
    .toLowerCase()
    .split(/[\s,.;:()[\]{}"'/-]+/)
    .filter((word) => word.length > 3);

  const titleWords = title
    .toLowerCase()
    .split(/[\s,.;:()[\]{}"'/-]+/)
    .filter((word) => word.length > 3);

  const overlappingWords = queryWords.filter((word) =>
    titleWords.includes(word)
  );

  const uniqueWords = [...new Set(overlappingWords)];

  if (uniqueWords.length >= 3) {
    return `Recommended because it shares key research concepts with your paper, including ${uniqueWords
      .slice(0, 3)
      .join(", ")}.`;
  }

  if (uniqueWords.length > 0) {
    return `Recommended because its research topic overlaps with your paper, particularly around ${uniqueWords.join(
      " and "
    )}.`;
  }

  return "Recommended because it was identified as related literature for the extracted research topic.";
}

function getPaperUrl(paper: PaperMetadata) {
  return (
    paper.pdf_url ||
    paper.url ||
    undefined
  );
}

export function RecommendedPapers({
  papers,
  loading = false,
  query = "",
}: RecommendedPapersProps) {
  const scroll = (direction: "left" | "right") => {
    const container = document.getElementById(
      "recommended-papers-scroll"
    );

    if (!container) return;

    container.scrollBy({
      left: direction === "left" ? -380 : 380,
      behavior: "smooth",
    });
  };

  if (!loading && papers.length === 0) {
    return null;
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">
            <Sparkles className="h-5 w-5" />
          </div>

          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              Recommended Literature
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Related research discovered from your extracted paper.
            </p>
          </div>
        </div>

        {!loading && papers.length > 1 && (
          <div className="hidden gap-2 sm:flex">
            <button
              onClick={() => scroll("left")}
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
              aria-label="Previous papers"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <button
              onClick={() => scroll("right")}
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
              aria-label="Next papers"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="mt-6 flex gap-5 overflow-hidden">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="min-w-[320px] rounded-2xl border border-slate-200 bg-slate-50 p-5"
            >
              <div className="h-5 w-4/5 animate-pulse rounded bg-slate-200" />

              <div className="mt-3 h-4 w-1/3 animate-pulse rounded bg-slate-200" />

              <div className="mt-5 space-y-2">
                <div className="h-3 w-full animate-pulse rounded bg-slate-200" />
                <div className="h-3 w-5/6 animate-pulse rounded bg-slate-200" />
                <div className="h-3 w-4/6 animate-pulse rounded bg-slate-200" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div
          id="recommended-papers-scroll"
          className="mt-6 flex gap-5 overflow-x-auto scroll-smooth pb-4 [scrollbar-width:thin]"
        >
          {papers.map((paper, index) => {
            const title = getPaperTitle(paper);
            const url = getPaperUrl(paper);
            const reason = getReason(paper, query);

            return (
              <article
                key={`${title}-${index}`}
                className="flex min-w-[340px] max-w-[340px] shrink-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-slate-600 shadow-sm">
                    <BookOpen className="h-4 w-4" />
                  </div>

                  {url && (
                    <a
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:text-slate-900"
                      aria-label={`Open ${title}`}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>

                <h3 className="mt-4 line-clamp-3 text-base font-semibold leading-6 text-slate-900">
                  {title}
                </h3>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  {paper.source && (
                    <span className="rounded-full bg-white px-2.5 py-1 font-medium text-slate-600">
                      {paper.source}
                    </span>
                  )}

                  {paper.year && (
                    <span className="rounded-full bg-white px-2.5 py-1 text-slate-500">
                      {paper.year}
                    </span>
                  )}
                </div>

                <p className="mt-4 line-clamp-3 text-xs leading-5 text-slate-500">
                  {getAuthors(paper)}
                </p>

                <div className="mt-5 rounded-xl border border-violet-100 bg-violet-50 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">
                    Why recommended
                  </p>

                  <p className="mt-1 text-xs leading-5 text-violet-900">
                    {reason}
                  </p>
                </div>

                <div className="mt-auto pt-5">
                  {url ? (
                    <a
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
                    >
                      Read paper
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  ) : (
                    <div className="rounded-xl bg-slate-200 px-4 py-2.5 text-center text-sm text-slate-500">
                      Paper link unavailable
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {!loading && papers.length > 0 && (
        <p className="mt-2 text-xs text-slate-400">
          Swipe horizontally to explore more papers.
        </p>
      )}
    </section>
  );
}