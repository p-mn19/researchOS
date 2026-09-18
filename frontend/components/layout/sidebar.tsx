"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  ClipboardCheck,
  FileCode2,
  FlaskConical,
  GitCompareArrows,
  LayoutDashboard,
  Lightbulb,
  Search,
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
];


export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-slate-200 bg-slate-50 px-5 py-6 md:flex">
      <div className="mb-8 flex items-center gap-3">
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

      <nav className="space-y-2">
        {items.map((item) => {
          const Icon = item.icon;

          const active =
            pathname === item.href ||
            pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-all",
                active
                  ? "bg-white text-blue-700 shadow-sm ring-1 ring-blue-100"
                  : "text-slate-600 hover:bg-white hover:text-slate-900 hover:shadow-sm",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-2xl border border-blue-100 bg-blue-50 p-4">
        <p className="text-xs font-semibold text-blue-900">
          ResearchOS AI Workspace
        </p>

        <p className="mt-1 text-xs leading-5 text-blue-700">
          Extract, compare, ideate, and generate content with LaTeX from your research corpus.
        </p>
      </div>
    </aside>
  );
}