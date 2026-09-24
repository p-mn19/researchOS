"use client";

import type { LatexCompileError } from "@/lib/api";

type LatexCompileErrorsProps = {
  errorMessage: string;
  errors: LatexCompileError[];
  log: string;
};

export function LatexCompileErrors({
  errorMessage,
  errors,
  log,
}: LatexCompileErrorsProps) {
  const hasErrors =
    Boolean(errorMessage) ||
    errors.length > 0 ||
    Boolean(log);

  if (!hasErrors) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-red-200 bg-red-50 p-5">
      <div>
        <h3 className="text-sm font-semibold text-red-900">
          LaTeX compilation failed
        </h3>

        {errorMessage && (
          <p className="mt-2 text-sm leading-6 text-red-700">
            {errorMessage}
          </p>
        )}
      </div>

      {errors.length > 0 && (
        <div className="mt-4 space-y-2">
          {errors.map((error, index) => (
            <div
              key={`${error.line ?? "unknown"}-${index}`}
              className="rounded-xl border border-red-200 bg-white px-4 py-3 text-sm text-red-800"
            >
              {error.line !== null && (
                <span className="mr-2 font-mono text-xs font-semibold text-red-600">
                  Line {error.line}
                </span>
              )}

              <span>{error.message}</span>
            </div>
          ))}
        </div>
      )}

      {log && (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-red-800">
            View compiler log
          </summary>

          <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-950 p-4 font-mono text-xs leading-5 text-slate-200">
            {log}
          </pre>
        </details>
      )}
    </section>
  );
}