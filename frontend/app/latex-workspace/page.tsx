"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Columns2,
  FileText,
  FileType2,
  Loader2,
  Trash2,
} from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import {
  deleteWorkspace,
  getWorkspaceVersions,
  getWorkspaces,
} from "@/lib/api";
import type {
  DocumentFormat,
  Workspace,
  WorkspaceVersion,
} from "@/lib/types";

type SavedWorkspace = {
  workspace: Workspace;
  version: WorkspaceVersion;
  documentFormat: DocumentFormat;
};

function errorMessage(error: unknown): string {
  return error instanceof Error && error.message
    ? error.message
    : "Could not load saved manuscript workspaces.";
}

function resolveDocumentFormat(
  latexCode: string,
  savedFormat?: DocumentFormat,
): DocumentFormat {
  if (savedFormat) {
    return savedFormat;
  }

  return latexCode.includes("\\documentclass[conference]{IEEEtran}")
    ? "ieee"
    : "normal";
}

function formatLabel(format: DocumentFormat): string {
  return format === "ieee"
    ? "IEEE double-column"
    : "Normal single-column";
}

export default function LatexWorkspaceIndexPage() {
  const router = useRouter();

  const [savedWorkspaces, setSavedWorkspaces] = useState<
    SavedWorkspace[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingWorkspaceId, setDeletingWorkspaceId] = useState("");

  useEffect(() => {
    async function loadSavedWorkspaces() {
      try {
        setLoading(true);
        setError("");

        const workspaces = await getWorkspaces();

        const results = await Promise.all(
          workspaces.map(async (workspace) => {
            const versions = await getWorkspaceVersions(workspace.id);

            const latestVersion = versions.reduce<WorkspaceVersion | null>(
              (latest, candidate) =>
                latest === null ||
                candidate.version > latest.version
                  ? candidate
                  : latest,
              null,
            );

            if (!latestVersion) {
              return null;
            }

            const documentFormat = resolveDocumentFormat(
              latestVersion.latex_code,
              latestVersion.document_format,
            );

            return {
              workspace,
              version: latestVersion,
              documentFormat,
            };
          }),
        );

        setSavedWorkspaces(
          results.filter(
            (item): item is SavedWorkspace => item !== null,
          ),
        );
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setLoading(false);
      }
    }

    void loadSavedWorkspaces();
  }, []);

  async function handleDeleteWorkspace(workspace: Workspace) {
    const confirmed = window.confirm(
      `Delete "${workspace.title}" and all of its saved manuscript versions? This cannot be undone.`,
    );

    if (!confirmed || deletingWorkspaceId) {
      return;
    }

    try {
      setDeletingWorkspaceId(workspace.id);
      setError("");
      await deleteWorkspace(workspace.id);
      setSavedWorkspaces((current) =>
        current.filter((item) => item.workspace.id !== workspace.id),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDeletingWorkspaceId("");
    }
  }

  return (
    <AppShell>
      <div className="space-y-5">
        <section className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-violet-50 p-2 text-violet-700">
              <FileText className="h-5 w-5" />
            </div>

            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                LaTeX Workspace
              </h1>

              <p className="mt-1 text-sm text-slate-600">
                Open a saved manuscript to edit its LaTeX draft,
                choose a document format, and compile it with Tectonic.
              </p>
            </div>
          </div>
        </section>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {loading ? (
          <section className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading saved manuscripts...
          </section>
        ) : savedWorkspaces.length === 0 ? (
          <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600 shadow-sm">
            No saved manuscripts are available. Create and save a
            manuscript in Research Workspace first.
          </section>
        ) : (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {savedWorkspaces.map(
              ({ workspace, version, documentFormat }) => {
                const isIEEE = documentFormat === "ieee";

                return (
                  <article
                    key={workspace.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs font-medium text-violet-700">
                        Saved manuscript · version {version.version}
                      </p>

                      <span
                        className={[
                          "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
                          isIEEE
                            ? "bg-blue-50 text-blue-700"
                            : "bg-slate-100 text-slate-700",
                        ].join(" ")}
                      >
                        {isIEEE ? (
                          <Columns2 className="h-3.5 w-3.5" />
                        ) : (
                          <FileType2 className="h-3.5 w-3.5" />
                        )}

                        {formatLabel(documentFormat)}
                      </span>
                    </div>

                    <h2 className="mt-3 text-lg font-semibold text-slate-900">
                      {workspace.title}
                    </h2>

                    <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-600">
                      {workspace.description ||
                        "No workspace description provided."}
                    </p>

                    <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
                      {isIEEE
                        ? "Uses IEEEtran conference layout with two columns."
                        : "Uses the normal article layout with one column."}
                    </div>

                    <div className="mt-5 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          router.push(`/workspace/${workspace.id}/latex`)
                        }
                        disabled={Boolean(deletingWorkspaceId)}
                        className="inline-flex rounded-xl bg-violet-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                      >
                        Open manuscript
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          void handleDeleteWorkspace(workspace)
                        }
                        disabled={Boolean(deletingWorkspaceId)}
                        className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-white px-3.5 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        aria-label={`Delete ${workspace.title}`}
                      >
                        <Trash2 className="h-4 w-4" />
                        {deletingWorkspaceId === workspace.id
                          ? "Deleting..."
                          : "Delete"}
                      </button>
                    </div>
                  </article>
                );
              },
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}
