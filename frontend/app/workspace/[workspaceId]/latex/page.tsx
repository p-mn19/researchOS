"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import { LatexWorkspacePanel } from "@/components/workspace/latex_workspace_panel";
import {
  getWorkspaceVersions,
  getWorkspaces,
  saveWorkspaceVersion,
} from "@/lib/api";
import type { Workspace, WorkspaceVersion } from "@/lib/types";


function errorMessage(error: unknown): string {
  return error instanceof Error && error.message
    ? error.message
    : "Could not load the saved manuscript.";
}


export default function LatexWorkspacePage() {
  const params = useParams<{ workspaceId: string }>();
  const workspaceId = params.workspaceId;
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [version, setVersion] = useState<WorkspaceVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    async function loadSavedManuscript() {
      try {
        setLoading(true);
        setError("");

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

        setWorkspace(
          workspaces.find((item) => item.id === workspaceId) || null,
        );
        setVersion(latestVersion);
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setLoading(false);
      }
    }

    void loadSavedManuscript();
  }, [workspaceId]);

  async function handleSave(latexCode: string) {
    const activeWorkspace = workspace;
    const activeVersion = version;

    if (!activeWorkspace || !activeVersion) {
      return;
    }

    setError("");
    setNotice("");

    try {
      const saved = await saveWorkspaceVersion(activeWorkspace.id, {
        content_type: activeVersion.content_type,
        content_markdown: activeVersion.content_markdown,
        latex_code: latexCode,
        citations: activeVersion.citations,
        warnings: activeVersion.warnings,
        source_chunk_ids: activeVersion.source_chunk_ids,
      });

      setVersion(saved);
      setNotice(`Workspace version ${saved.version} saved successfully.`);
    } catch (err) {
      setError(errorMessage(err));
      throw err;
    }
  }

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
        ) : version ? (
          <LatexWorkspacePanel
            workspaceId={workspaceId}
            initialLatexCode={version.latex_code}
            referencesBib={version.bibtex}
            onSave={handleSave}
          />
        ) : (
          <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600 shadow-sm">
            No saved manuscript version is available. Return to the workspace and save the manuscript before opening the LaTeX workspace.
          </section>
        )}
      </div>
    </AppShell>
  );
}
