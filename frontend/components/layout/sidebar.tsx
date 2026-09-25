"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  ClipboardCheck,
  FileCode2,
  FileText,
  FlaskConical,
  GitCompareArrows,
  LayoutDashboard,
  Lightbulb,
  Search,
  X,
} from "lucide-react";


const items = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    href: "/compare",
    label: "Compare Papers",
    icon: GitCompareArrows,
  },
  {
    href: "/search",
    label: "Search",
    icon: Search,
  },
  {
    href: "/review-simulation",
    label: "Review Simulation",
    icon: ClipboardCheck,
  },
  {
    href: "/ideation",
    label: "Research Gap & Ideation",
    icon: Lightbulb,
  },
  {
    href: "/workspace",
    label: "Research Workspace",
    icon: FileCode2,
  },
  {
    href: "/latex-workspace",
    label: "LaTeX Workspace",
    icon: FileText,
  },
];


type SidebarProps = {
  collapsed: boolean;
  mobileOpen: boolean;
  onCloseMobile: () => void;
};


export function Sidebar({
  collapsed,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname();

  function isActive(href: string): boolean {
    return (
      pathname === href ||
      pathname.startsWith(`${href}/`) ||
      (href === "/latex-workspace" &&
        /^\/workspace\/[^/]+\/latex$/.test(pathname))
    );
  }

  function renderNavigation(
    isCompact: boolean,
    closeAfterNavigation = false,
  ) {
    return (
      <nav className="space-y-2">
        {items.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={
                closeAfterNavigation
                  ? onCloseMobile
                  : undefined
              }
              title={isCompact ? item.label : undefined}
              className={clsx(
                "group flex items-center rounded-2xl text-sm font-medium transition-all",
                isCompact
                  ? "justify-center px-3 py-3"
                  : "gap-3 px-4 py-3",
                active
                  ? "bg-white text-blue-700 shadow-sm ring-1 ring-blue-100"
                  : "text-slate-600 hover:bg-white hover:text-slate-900 hover:shadow-sm",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />

              {!isCompact && (
                <span className="truncate">
                  {item.label}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-slate-950/35 md:hidden"
        />
      )}

      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-slate-50 px-5 py-6 shadow-xl transition-transform duration-200 md:hidden",
          mobileOpen
            ? "translate-x-0"
            : "-translate-x-full",
        )}
      >
        <div className="mb-8 flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-md">
              <FlaskConical className="h-5 w-5" />
            </div>

            <div className="min-w-0">
              <h1 className="text-lg font-semibold text-slate-900">
                ResearchOS
              </h1>

              <p className="text-xs text-slate-500">
                Research workflow copilot
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Close navigation menu"
            className="rounded-xl p-2 text-slate-500 transition hover:bg-white hover:text-slate-900"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {renderNavigation(false, true)}

        <div className="mt-auto rounded-2xl border border-blue-100 bg-blue-50 p-4">
          <p className="text-xs font-semibold text-blue-900">
            ResearchOS AI Workspace
          </p>

          <p className="mt-1 text-xs leading-5 text-blue-700">
            Extract, compare, ideate, and generate content with LaTeX from your research corpus.
          </p>
        </div>
      </aside>

      <aside
        className={clsx(
          "hidden shrink-0 flex-col border-r border-slate-200 bg-slate-50 py-6 transition-[width] duration-200 md:flex",
          collapsed
            ? "w-20 px-3"
            : "w-72 px-5",
        )}
      >
        <div
          className={clsx(
            "mb-8 flex items-center",
            collapsed
              ? "justify-center"
              : "gap-3",
          )}
        >
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-md">
            <FlaskConical className="h-5 w-5" />
          </div>

          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-lg font-semibold text-slate-900">
                ResearchOS
              </h1>

              <p className="text-xs text-slate-500">
                Research workflow copilot
              </p>
            </div>
          )}
        </div>

        {renderNavigation(collapsed)}

        {!collapsed && (
          <div className="mt-auto rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <p className="text-xs font-semibold text-blue-900">
              ResearchOS AI Workspace
            </p>

            <p className="mt-1 text-xs leading-5 text-blue-700">
              Extract, compare, ideate, and generate content with LaTeX from your research corpus.
            </p>
          </div>
        )}
      </aside>
    </>
  );
}