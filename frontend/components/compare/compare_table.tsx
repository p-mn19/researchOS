import { CompareRow } from "@/lib/types";

export function CompareTable({
  rows,
  paperTitles,
}: {
  rows: CompareRow[];
  paperTitles: Record<string, string>;
}) {
  const paperIds = Object.keys(paperTitles);

  return (
    <div className="overflow-x-auto rounded-2xl border border-zinc-800 bg-zinc-900">
      <table className="w-full min-w-[800px] text-left text-sm">
        <thead className="border-b border-zinc-800 bg-zinc-950/50">
          <tr>
            <th className="px-4 py-3">Field</th>
            {paperIds.map((id) => (
              <th key={id} className="px-4 py-3">{paperTitles[id]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field} className="border-b border-zinc-800/70">
              <td className="px-4 py-3 font-medium text-emerald-300">{row.field}</td>
              {paperIds.map((id) => (
                <td key={id} className="px-4 py-3 text-zinc-300">
                  {row.values[id] || "-"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}