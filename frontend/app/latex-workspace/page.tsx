"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, FileText, Loader2 } from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import { getWorkspaceVersions, getWorkspaces } from "@/lib/api";
import type { Workspace } from "@/lib/types";


type SavedWorkspace = {
  workspace: Workspace;
  version: number;
};


function errorMessage(error: unknown): string {
  return error instanceof Error && error.message
    ? error.message
    : "Could not load saved manuscript workspaces.";
}


export default function LatexWorkspaceIndexPage() {
  const router = useRouter();
  const [savedWorkspaces, setSavedWorkspaces] = useState<SavedWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSavedWorkspaces() {
      try {
        setLoading(true);
        setError("");

        const workspaces = await getWorkspaces();
        const results = await Promise.all(
          workspaces.map(async (workspace) => {
            const versions = await getWorkspaceVersions(workspace.id);
            const latestVersion = versions.reduce<number | null>(
              (latest, version) =>
                latest === null || version.version > latest
                  ? version.version
                  : latest,
              null,
            );

            return latestVersion === null
              ? null
              : { workspace, version: latestVersion };
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
                Open a saved manuscript to edit its full LaTeX draft and compile it with Tectonic.
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
            No saved manuscripts are available. Create and save a manuscript in Research Workspace first.
          </section>
        ) : (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {savedWorkspaces.map(({ workspace, version }) => (
              <article
                key={workspace.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <p className="text-xs font-medium text-violet-700">
                  Saved manuscript · version {version}
                </p>

                <h2 className="mt-2 text-lg font-semibold text-slate-900">
                  {workspace.title}
                </h2>

                <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-600">
                  {workspace.description || "No workspace description provided."}
                </p>

                <button
                  type="button"
                  onClick={() =>
                    router.push(`/workspace/${workspace.id}/latex`)
                  }
                  className="mt-5 inline-flex rounded-xl bg-violet-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-800"
                >
                  Open manuscript
                </button>
              </article>
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}
