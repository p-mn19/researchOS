import { CompareRow, Paper } from "@/lib/types";

export function CompareTable({
  rows,
  selectedPapers,
}: {
  rows: CompareRow[];
  selectedPapers: Paper[];
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-6 py-5">
        <h3 className="text-lg font-semibold text-slate-900">Comparison table</h3>
        <p className="text-sm text-slate-500">Structured output across selected research papers</p>
      </div>

      {rows.length === 0 ? (
        <div className="px-6 py-10 text-center text-slate-500">No comparison generated yet.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full table-fixed">
            <thead className="bg-slate-50">
              <tr className="text-left text-sm text-slate-500">
                <th className="px-6 py-4 font-medium">Field</th>
                {selectedPapers.map((paper) => (
                  <th key={paper.id} className="px-6 py-4 font-medium">
                    <div className="max-w-[220px]">
                      <p className="truncate font-semibold text-slate-700">{paper.title}</p>
                      <p className="truncate text-xs text-slate-400">{paper.filename}</p>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.field} className="border-t border-slate-100 align-top">
                  <td className="whitespace-nowrap px-6 py-4 font-medium text-slate-900">
                    {row.field}
                  </td>
                  {selectedPapers.map((paper) => (
                    <td key={paper.id} className="px-6 py-4 text-sm leading-6 text-slate-600">
                      {row.values[paper.id] || "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}