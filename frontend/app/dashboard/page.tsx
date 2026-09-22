"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import { UploadCard } from "@/components/papers/upload_card";
import { PaperStatusBadge } from "@/components/papers/paper_status_badge";
import { getPapers } from "@/lib/api";
import { Paper } from "@/lib/types";
import Link from "next/link";
import {
  ArrowRight,
  FileText,
  Database,
  Sparkles,
  SearchCheck,
} from "lucide-react";

export default function DashboardPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadPapers() {
    try {
      setLoading(true);
      setError("");

      const data = await getPapers();
      setPapers(data);
    } catch (err) {
      console.error(err);
      setError(
        "Could not connect to backend. Start FastAPI on port 8000."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPapers();
  }, []);

  const total = papers.length;

  const parsed = papers.filter((p) =>
    ["parsed", "indexed", "extracted"].includes(p.status)
  ).length;

  const indexed = papers.filter((p) =>
    ["indexed", "extracted"].includes(p.status)
  ).length;

  const extracted = papers.filter(
    (p) => p.status === "extracted"
  ).length;

  const stats = [
    {
      label: "Total papers",
      value: total,
      icon: FileText,
      color: "bg-blue-50 text-blue-700",
    },
    {
      label: "Parsed",
      value: parsed,
      icon: Database,
      color: "bg-cyan-50 text-cyan-700",
    },
    {
      label: "Indexed",
      value: indexed,
      icon: SearchCheck,
      color: "bg-emerald-50 text-emerald-700",
    },
    {
      label: "Extracted",
      value: extracted,
      icon: Sparkles,
      color: "bg-violet-50 text-violet-700",
    },
  ];

  return (
    <AppShell>
      <div className="space-y-8">
        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="max-w-2xl">
              <div className="mb-4 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                Research pipeline
              </div>

              <h2 className="text-4xl font-semibold tracking-tight text-slate-900">
                Organize papers into structured,
                searchable research knowledge
              </h2>

              <p className="mt-4 text-base leading-7 text-slate-600">
                Upload papers, parse sections, retrieve relevant
                evidence, and compare methods, datasets, metrics,
                and limitations in one workspace.
              </p>
            </div>
          </div>

          <UploadCard onUploaded={loadPapers} />
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;

            return (
              <div
                key={stat.label}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-slate-500">
                      {stat.label}
                    </p>

                    <p className="mt-3 text-3xl font-semibold text-slate-900">
                      {stat.value}
                    </p>
                  </div>

                  <div
                    className={`rounded-2xl p-3 ${stat.color}`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                </div>
              </div>
            );
          })}
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                Paper library
              </h3>

              <p className="text-sm text-slate-500">
                Uploaded papers and processing status
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full table-fixed">
              <thead className="bg-slate-50">
                <tr className="text-left text-sm text-slate-500">
                  <th className="px-6 py-4 font-medium">
                    Title
                  </th>

                  <th className="px-6 py-4 font-medium">
                    Filename
                  </th>

                  <th className="px-6 py-4 font-medium">
                    Status
                  </th>

                  <th className="px-6 py-4 font-medium">
                    Year
                  </th>

                  <th className="px-6 py-4 font-medium">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-6 py-10 text-center text-slate-500"
                    >
                      Loading papers...
                    </td>
                  </tr>
                ) : papers.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-6 py-10 text-center text-slate-500"
                    >
                      No papers uploaded yet.
                    </td>
                  </tr>
                ) : (
                  papers.map((paper) => (
                    <tr
                      key={paper.id}
                      className="border-t border-slate-100"
                    >
                      <td className="px-6 py-4 font-medium text-slate-900">
                        <div className="max-w-[260px] truncate">
                          {paper.title || "Untitled paper"}
                        </div>
                      </td>

                      <td className="px-6 py-4 text-slate-600">
                        <div className="max-w-[260px] truncate">
                          {paper.filename}
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <PaperStatusBadge
                          status={paper.status}
                        />
                      </td>

                      <td className="px-6 py-4 text-slate-600">
                        {paper.year || "—"}
                      </td>

                      <td className="px-6 py-4">
                        <Link
                          href={`/papers/${paper.id}`}
                          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
                        >
                          Open

                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppShell>
  );
}