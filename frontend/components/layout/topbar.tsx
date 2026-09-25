"use client";

import { Menu, PanelLeftClose, PanelLeftOpen } from "lucide-react";


type TopbarProps = {
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  onOpenMobileSidebar: () => void;
};


export function Topbar({
  sidebarCollapsed,
  onToggleSidebar,
  onOpenMobileSidebar,
}: TopbarProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="flex min-h-20 items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8 xl:px-10">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={onOpenMobileSidebar}
            aria-label="Open navigation menu"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-slate-950 md:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label={
              sidebarCollapsed
                ? "Expand navigation sidebar"
                : "Collapse navigation sidebar"
            }
            title={
              sidebarCollapsed
                ? "Expand sidebar"
                : "Collapse sidebar"
            }
            className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-slate-950 md:inline-flex"
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen className="h-5 w-5" />
            ) : (
              <PanelLeftClose className="h-5 w-5" />
            )}
          </button>

          <div className="min-w-0">
            <h1 className="truncate text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl lg:text-3xl">
              Research Workflow Dashboard
            </h1>

            <p className="mt-1 hidden text-sm text-slate-500 sm:block">
              Upload, extract, search, and compare research papers
            </p>
          </div>
        </div>

        <div className="hidden shrink-0 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-600 lg:block">
          Ethical • Citation-grounded • Structured
        </div>
      </div>
    </header>
  );
}