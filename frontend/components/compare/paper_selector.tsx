"use client";

import { Paper } from "@/lib/types";

export function PaperSelector({
  papers,
  selected,
  onChange,
}: {
  papers: Paper[];
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  const toggle = (id: string) => {
    if (selected.includes(id)) onChange(selected.filter((x) => x !== id));
    else if (selected.length < 3) onChange([...selected, id]);
  };

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {papers.map((paper) => (
        <label
          key={paper.id}
          className="flex cursor-pointer items-start gap-3 rounded-xl border border-zinc-800 bg-zinc-900 p-4"
        >
          <input
            type="checkbox"
            checked={selected.includes(paper.id)}
            onChange={() => toggle(paper.id)}
            className="mt-1"
          />
          <div>
            <p className="font-medium">{paper.title}</p>
            <p className="text-sm text-zinc-400">{paper.filename}</p>
          </div>
        </label>
      ))}
    </div>
  );
}