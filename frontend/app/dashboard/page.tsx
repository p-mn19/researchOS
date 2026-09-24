"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app_shell";
import { UploadCard } from "@/components/papers/upload_card";
import { PaperStatusBadge } from "@/components/papers/paper_status_badge";
import {
  deletePaper,
  getPapers,
} from "@/lib/api";
import { Paper } from "@/lib/types";
import Link from "next/link";
import {
  ArrowRight,
  FileText,
  Database,
  Sparkles,
  SearchCheck,
  Trash2,
  X,
  AlertTriangle,
} from "lucide-react";

export default function DashboardPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [paperToDelete, setPaperToDelete] =
    useState<Paper | null>(null);

  const [deletingPaper, setDeletingPaper] =
    useState(false);

  const [deleteError, setDeleteError] =
    useState("");

  async function loadPapers() {
    try {
      setLoading(true);
      setError("");

      const data = await getPapers();
      setPapers(data);
    } catch (err) {
      console.error(err);

      setError(
        "Could not connect to backend. Start FastAPI on port 8000.",
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
    [
      "parsed",
      "indexed",
      "extracted",
    ].includes(p.status),
  ).length;

  const indexed = papers.filter((p) =>
    [
      "indexed",
      "extracted",
    ].includes(p.status),
  ).length;

  const extracted = papers.filter(
    (p) => p.status === "extracted",
  ).length;

  const stats = [
    {
      label: "Total papers",
      value: total,
      icon: FileText,
      color:
        "bg-blue-50 text-blue-700",
    },
    {
      label: "Parsed",
      value: parsed,
      icon: Database,
      color:
        "bg-cyan-50 text-cyan-700",
    },
    {
      label: "Indexed",
      value: indexed,
      icon: SearchCheck,
      color:
        "bg-emerald-50 text-emerald-700",
    },
    {
      label: "Extracted",
      value: extracted,
      icon: Sparkles,
      color:
        "bg-violet-50 text-violet-700",
    },
  ];

  async function handleDeletePaper() {
    if (!paperToDelete) {
      return;
    }

    try {
      setDeletingPaper(true);
      setDeleteError("");

      await deletePaper(
        paperToDelete.id,
      );

      setPapers((prev) =>
        prev.filter(
          (paper) =>
            paper.id !==
            paperToDelete.id,
        ),
      );

      setPaperToDelete(null);
    } catch (err) {
      console.error(err);

      setDeleteError(
        err instanceof Error
          ? err.message
          : "Failed to remove paper.",
      );
    } finally {
      setDeletingPaper(false);
    }
  }

  function openDeleteDialog(
    paper: Paper,
  ) {
    setDeleteError("");
    setPaperToDelete(paper);
  }

  function closeDeleteDialog() {
    if (deletingPaper) {
      return;
    }

    setPaperToDelete(null);
    setDeleteError("");
  }

  return (
    <AppShell>
      <div className="space-y-8">

        {/* ================================================= */}
        {/* GENERAL ERROR */}
        {/* ================================================= */}

        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {/* ================================================= */}
        {/* HERO */}
        {/* ================================================= */}

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

          <UploadCard
            onUploaded={loadPapers}
          />

        </section>

        {/* ================================================= */}
        {/* STATS */}
        {/* ================================================= */}

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

        {/* ================================================= */}
        {/* PAPER LIBRARY */}
        {/* ================================================= */}

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

            <table className="min-w-full">

              <thead className="bg-slate-50">

                <tr className="text-left text-sm text-slate-500">

                  <th className="whitespace-nowrap px-6 py-4 font-medium">
                    Title
                  </th>

                  <th className="whitespace-nowrap px-6 py-4 font-medium">
                    Filename
                  </th>

                  <th className="whitespace-nowrap px-6 py-4 font-medium">
                    Status
                  </th>

                  <th className="whitespace-nowrap px-6 py-4 font-medium">
                    Year
                  </th>

                  <th className="whitespace-nowrap px-6 py-4 font-medium">
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

                      {/* TITLE */}

                      <td className="px-6 py-4 font-medium text-slate-900">

                        <div className="max-w-[260px] truncate">
                          {paper.title ||
                            "Untitled paper"}
                        </div>

                      </td>

                      {/* FILENAME */}

                      <td className="px-6 py-4 text-slate-600">

                        <div className="max-w-[260px] truncate">
                          {paper.filename}
                        </div>

                      </td>

                      {/* STATUS */}

                      <td className="px-6 py-4">

                        <PaperStatusBadge
                          status={
                            paper.status
                          }
                        />

                      </td>

                      {/* YEAR */}

                      <td className="px-6 py-4 text-slate-600">
                        {paper.year ||
                          "—"}
                      </td>

                      {/* ACTIONS */}

                      <td className="px-6 py-4">

                        <div className="flex items-center gap-2 whitespace-nowrap">

                          {/* OPEN */}

                          <Link
                            href={`/papers/${paper.id}`}
                            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                          >
                            <span>
                              Open
                            </span>

                            <ArrowRight className="h-4 w-4" />
                          </Link>

                          {/* REMOVE */}

                          <button
                            type="button"
                            onClick={() =>
                              openDeleteDialog(
                                paper,
                              )
                            }
                            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-rose-200 bg-white px-3 text-sm font-medium text-rose-600 transition hover:border-rose-300 hover:bg-rose-50"
                            aria-label={`Remove ${
                              paper.title ||
                              paper.filename
                            }`}
                          >
                            <Trash2 className="h-4 w-4" />

                            <span className="hidden xl:inline">
                              Remove
                            </span>
                          </button>

                        </div>

                      </td>

                    </tr>

                  ))

                )}

              </tbody>

            </table>

          </div>

        </section>

      </div>

      {/* =================================================== */}
      {/* REMOVE CONFIRMATION MODAL */}
      {/* =================================================== */}

      {paperToDelete && (

        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeDeleteDialog();
            }
          }}
        >

          <div
            className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="remove-paper-title"
          >

            {/* HEADER */}

            <div className="flex items-start justify-between gap-4">

              <div className="flex items-center gap-3">

                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
                  <AlertTriangle className="h-5 w-5" />
                </div>

                <div>

                  <h3
                    id="remove-paper-title"
                    className="text-lg font-semibold text-slate-900"
                  >
                    Remove paper?
                  </h3>

                  <p className="text-sm text-slate-500">
                    This action cannot be undone.
                  </p>

                </div>

              </div>

              <button
                type="button"
                onClick={
                  closeDeleteDialog
                }
                disabled={
                  deletingPaper
                }
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>

            </div>

            {/* PAPER */}

            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">

              <p className="line-clamp-3 text-sm font-medium leading-5 text-slate-800">
                {paperToDelete.title ||
                  paperToDelete.filename ||
                  "Untitled paper"}
              </p>

              {paperToDelete.filename &&
                paperToDelete.title !==
                  paperToDelete.filename && (
                  <p className="mt-1 truncate text-xs text-slate-500">
                    {paperToDelete.filename}
                  </p>
                )}

            </div>

            <p className="mt-4 text-sm leading-6 text-slate-500">
              This will remove the paper, extracted data,
              indexed chunks, vector embeddings, and stored PDF
              from ResearchOS.
            </p>

            {/* DELETE ERROR */}

            {deleteError && (
              <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-5 text-rose-700">
                {deleteError}
              </div>
            )}

            {/* ACTIONS */}

            <div className="mt-6 flex justify-end gap-3">

              <button
                type="button"
                disabled={
                  deletingPaper
                }
                onClick={
                  closeDeleteDialog
                }
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={
                  deletingPaper
                }
                onClick={
                  handleDeletePaper
                }
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >

                <Trash2 className="h-4 w-4" />

                {deletingPaper
                  ? "Removing..."
                  : "Remove paper"}

              </button>

            </div>

          </div>

        </div>

      )}

    </AppShell>
  );
}