"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import { LatexWorkspacePanel } from "@/components/workspace/latex_workspace_panel";
import {
  getWorkspaceVersions,
  getWorkspaces,
  saveWorkspaceVersion,
} from "@/lib/api";
import type {
  DocumentFormat,
  Workspace,
  WorkspaceVersion,
} from "@/lib/types";

function errorMessage(error: unknown): string {
  return error instanceof Error && error.message
    ? error.message
    : "Could not load the saved manuscript.";
}

function resolveDocumentFormat(
  latexCode: string,
  savedFormat?: DocumentFormat,
): DocumentFormat {
  if (savedFormat === "ieee" || savedFormat === "normal") {
    return savedFormat;
  }

  return latexCode.includes("\\documentclass[conference]{IEEEtran}")
    ? "ieee"
    : "normal";
}

function formatLabel(documentFormat: DocumentFormat): string {
  return documentFormat === "ieee"
    ? "IEEE double-column"
    : "normal single-column";
}

export default function LatexWorkspacePage() {
  const params = useParams<{ workspaceId?: string }>();
  const workspaceId = params.workspaceId;
  const router = useRouter();

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [version, setVersion] = useState<WorkspaceVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    async function loadSavedManuscript() {
      if (!workspaceId) {
        router.replace("/research-workspace");
        return;
      }

      try {
        setLoading(true);
        setError("");
        setNotice("");

        const [workspaces, versions] = await Promise.all([
          getWorkspaces(),
          getWorkspaceVersions(workspaceId),
        ]);

        const latestVersion = versions.reduce<WorkspaceVersion | null>(
          (latest, item) =>
            latest === null || item.version > latest.version
              ? item
              : latest,
          null,
        );

        const activeWorkspace =
          workspaces.find((item) => item.id === workspaceId) || null;

        setWorkspace(activeWorkspace);
        setVersion(latestVersion);

        if (!activeWorkspace) {
          setError("The requested workspace could not be found.");
        }
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setLoading(false);
      }
    }

    void loadSavedManuscript();
  }, [router, workspaceId]);

  async function handleSave(
    latexCode: string,
    documentFormat: DocumentFormat,
  ) {
    if (!workspace || !version) {
      throw new Error(
        "Cannot save because the workspace or manuscript version is unavailable.",
      );
    }

    setError("");
    setNotice("");

    try {
      const saved = await saveWorkspaceVersion(workspace.id, {
        content_type: version.content_type,
        content_markdown: version.content_markdown,
        latex_code: latexCode,
        citations: version.citations,
        warnings: version.warnings,
        source_chunk_ids: version.source_chunk_ids,
        document_format: documentFormat,
      });

      setVersion(saved);

      setNotice(
        `Workspace version ${saved.version} saved successfully in ${formatLabel(
          documentFormat,
        )} format.`,
      );
    } catch (err) {
      const message = errorMessage(err);
      setError(message);
      throw new Error(message);
    }
  }

  const initialDocumentFormat = resolveDocumentFormat(
    version?.latex_code ?? "",
    version?.document_format,
  );

  return (
    <AppShell>
      <div className="space-y-5">
        <section className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            LaTeX workspace
          </h1>

          <p className="mt-2 text-sm text-slate-600">
            {workspace
              ? `Editing the latest saved manuscript for ${workspace.title}.`
              : "Editing the latest saved manuscript version."}
          </p>
        </section>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {notice && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {notice}
          </div>
        )}

        {loading ? (
          <section className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading saved manuscript...
          </section>
        ) : version && workspaceId ? (
          <LatexWorkspacePanel
            workspaceId={workspaceId}
            initialLatexCode={version.latex_code}
            initialDocumentFormat={initialDocumentFormat}
            referencesBib={version.bibtex ?? ""}
            onSave={handleSave}
          />
        ) : (
          <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600 shadow-sm">
            No saved manuscript version is available. Return to the
            Research Workspace, generate or save a manuscript version,
            and then reopen the LaTeX workspace.
          </section>
        )}
      </div>
    </AppShell>
  );
}
