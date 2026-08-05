"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import { getPapers, comparePapers } from "@/lib/api";
import { CompareRow, Paper } from "@/lib/types";
import { GitCompareArrows, CheckCircle2 } from "lucide-react";
import { CompareTable } from "@/components/compare/compare_table";

export default function ComparePage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [loadingCompare, setLoadingCompare] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        setLoadingPapers(true);
        const data = await getPapers();
        setPapers(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingPapers(false);
      }
    }
    load();
  }, []);

  function togglePaper(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id].slice(0, 4)
    );
  }

  async function handleCompare() {
    if (selected.length < 2) {
      alert("Select at least 2 papers to compare");
      return;
    }

    try {
      setLoadingCompare(true);
      const data = await comparePapers(selected);
      setRows(data);
    } catch (err) {
      console.error(err);
      alert("Comparison failed");
    } finally {
      setLoadingCompare(false);
    }
  }

  const selectedPapers = papers.filter((p) => selected.includes(p.id));

  return (
    <AppShell>
      <div className="space-y-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <div className="mb-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                Cross-paper analysis
              </div>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
                Compare research papers side by side
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Select papers to compare methods, datasets, metrics, baselines, and limitations
                in one structured view.
              </p>
            </div>

            <div className="hidden rounded-2xl bg-slate-50 p-3 md:block">
              <GitCompareArrows className="h-8 w-8 text-blue-600" />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {loadingPapers ? (
              <div className="text-sm text-slate-500">Loading papers...</div>
            ) : papers.length === 0 ? (
              <div className="text-sm text-slate-500">No papers available for comparison.</div>
            ) : (
              papers.map((paper) => {
                const active = selected.includes(paper.id);

                return (
                  <button
                    key={paper.id}
                    onClick={() => togglePaper(paper.id)}
                    className={`rounded-2xl border p-5 text-left transition ${
                      active
                        ? "border-blue-200 bg-blue-50 ring-1 ring-blue-100"
                        : "border-slate-200 bg-white hover:border-blue-100 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="line-clamp-2 text-base font-semibold text-slate-900">
                          {paper.title || "Untitled paper"}
                        </h3>
                        <p className="mt-2 text-sm text-slate-500">{paper.filename}</p>
                        <p className="mt-1 text-xs text-slate-400">{paper.year || "Year unavailable"}</p>
                      </div>

                      {active && <CheckCircle2 className="h-5 w-5 shrink-0 text-blue-600" />}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="mt-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-slate-500">
              Selected: <span className="font-semibold text-slate-900">{selected.length}</span> / 4
            </p>

            <button
              onClick={handleCompare}
              disabled={selected.length < 2 || loadingCompare}
              className="inline-flex items-center justify-center rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {loadingCompare ? "Generating comparison..." : "Compare selected papers"}
            </button>
          </div>
        </section>

        <CompareTable rows={rows} selectedPapers={selectedPapers} />
      </div>
    </AppShell>
  );
}