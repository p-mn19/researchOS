"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import { Search, FileText, ArrowRight } from "lucide-react";
import Link from "next/link";

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
  const [query, setQuery] = useState("");

  const filteredPapers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return PAPERS;

    return PAPERS.filter((paper) => {
      const haystack = `${paper.title} ${paper.filename} ${paper.year} ${paper.tags.join(" ")}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [query]);

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