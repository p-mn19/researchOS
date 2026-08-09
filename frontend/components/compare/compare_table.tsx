import { CompareRow, Paper } from "@/lib/types";

export function CompareTable({
  rows,
  selectedPapers,
}: {
  rows: CompareRow[];
  selectedPapers: Paper[];
}) {
  if (!selectedPapers.length) {
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Comparison table</h3>
        <p className="mt-2 text-sm text-slate-500">
          Select at least two papers and click compare to see structured results.
        </p>
      </section>
    );
  }

  if (!rows.length) {
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Comparison table</h3>
        <p className="mt-2 text-sm text-slate-500">
          No comparison generated yet.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-6 py-5">
        <h3 className="text-lg font-semibold text-slate-900">Comparison table</h3>
        <p className="mt-1 text-sm text-slate-500">
          Structured output across selected research papers
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left">
          <thead className="bg-slate-50">
            <tr>
              <th className="w-40 border-b border-slate-200 px-6 py-4 text-sm font-medium text-slate-600">
                Field
              </th>
              {selectedPapers.map((paper) => (
                <th
                  key={paper.id}
                  className="min-w-[260px] border-b border-slate-200 px-6 py-4 text-sm font-medium text-slate-700"
                >
                  <div className="max-w-[280px]">
                    <div className="truncate font-semibold text-slate-900">
                      {paper.title || "Untitled paper"}
                    </div>
                    <div className="truncate text-xs text-slate-500">{paper.filename}</div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, idx) => (
              <tr key={`${row.field}-${idx}`} className="even:bg-slate-50/60">
                <td className="border-b border-slate-200 px-6 py-4 text-sm font-semibold text-slate-900">
                  {row.field}
                </td>
                {selectedPapers.map((paper) => (
                  <td
                    key={paper.id}
                    className="border-b border-slate-200 px-6 py-4 text-sm leading-6 text-slate-600"
                  >
                    {row.values?.[paper.id] || "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}