"use client";

import type { ChangeEvent } from "react";

type LatexEditorProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

export function LatexEditor({
  value,
  onChange,
  disabled = false,
}: LatexEditorProps) {
  function handleChange(
    event: ChangeEvent<HTMLTextAreaElement>,
  ) {
    onChange(event.target.value);
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900 px-4 py-3">
        <div>
          <p className="font-mono text-sm font-semibold text-slate-100">
            main.tex
          </p>

          <p className="mt-0.5 text-xs text-slate-400">
            Edit the LaTeX source before compiling.
          </p>
        </div>

        <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
          LaTeX
        </span>
      </div>

      <textarea
        value={value}
        onChange={handleChange}
        disabled={disabled}
        spellCheck={false}
        aria-label="LaTeX source editor"
        className="min-h-[520px] w-full resize-y bg-slate-950 p-5 font-mono text-sm leading-6 text-emerald-200 outline-none placeholder:text-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
        placeholder={"\\section{Related Work}\n\nWrite your LaTeX content here."}
      />
    </div>
  );
}