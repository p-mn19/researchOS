import { ChunkResult } from "@/lib/types";

export function ChunkResults({ results }: { results: ChunkResult[] }) {
  return (
    <div className="space-y-3">
      {results.map((chunk) => (
        <div key={chunk.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <div className="mb-2 flex items-center justify-between text-xs text-zinc-400">
            <span>{chunk.section_title || "Section"}</span>
            <span>Page {chunk.page || "-"}</span>
          </div>
          <p className="text-sm leading-6 text-zinc-300">{chunk.text}</p>
        </div>
      ))}
    </div>
  );
}