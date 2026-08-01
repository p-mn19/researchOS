"use client";

import Link from "next/link";
import { extractPaper, parsePaper } from "@/lib/api";
import { Paper } from "@/lib/types";
import { PaperStatusBadge } from "./paper_status_badge";
import { useState } from "react";

export function PaperTable({
  papers,
  onRefresh,
}: {
  papers: Paper[];
  onRefresh: () => void;
}) {
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const runAction = async (id: string, action: "parse" | "extract") => {
    try {
      setLoadingId(`${id}-${action}`);
      if (action === "parse") await parsePaper(id);
      else await extractPaper(id);
      onRefresh();
    } catch {
      alert(`${action} failed`);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-zinc-800 bg-zinc-950/50 text-zinc-400">
          <tr>
            <th className="px-4 py-3">Title</th>
            <th className="px-4 py-3">Filename</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Year</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {papers.map((paper) => (
            <tr key={paper.id} className="border-b border-zinc-800/70">
              <td className="px-4 py-3">{paper.title || "Untitled paper"}</td>
              <td className="px-4 py-3 text-zinc-400">{paper.filename}</td>
              <td className="px-4 py-3">
                <PaperStatusBadge status={paper.status} />
              </td>
              <td className="px-4 py-3">{paper.year || "-"}</td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/papers/${paper.id}`}
                    className="rounded-lg border border-zinc-700 px-3 py-1.5"
                  >
                    View
                  </Link>
                  <button
                    onClick={() => runAction(paper.id, "parse")}
                    className="rounded-lg border border-zinc-700 px-3 py-1.5"
                  >
                    {loadingId === `${paper.id}-parse` ? "Parsing..." : "Parse"}
                  </button>
                  <button
                    onClick={() => runAction(paper.id, "extract")}
                    className="rounded-lg border border-zinc-700 px-3 py-1.5"
                  >
                    {loadingId === `${paper.id}-extract` ? "Extracting..." : "Extract"}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}