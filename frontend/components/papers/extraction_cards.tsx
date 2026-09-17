import { Extraction } from "@/lib/types";

const fields: { key: keyof Extraction; label: string }[] = [
  { key: "objective", label: "Objective" },
  { key: "methodology", label: "Methodology" },
  { key: "dataset", label: "Dataset" },
  { key: "evaluation_metric", label: "Evaluation Metric" },
  { key: "limitations", label: "Limitations" },
  { key: "future_work", label: "Future Work" },
];

export function ExtractionCards({ extraction }: { extraction: Extraction }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {fields.map((field) => (
        <div key={field.key} className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
          <h3 className="mb-2 text-sm font-semibold text-emerald-300">{field.label}</h3>
          <p className="text-sm leading-6 text-zinc-300">
            {extraction[field.key] || "Field does not exist."}
          </p>
        </div>
      ))}
    </div>
  );
}
