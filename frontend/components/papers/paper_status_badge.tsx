import { PaperStatus } from "@/lib/types";

const styles: Record<PaperStatus, string> = {
  uploaded: "bg-slate-100 text-slate-700",
  parsed: "bg-blue-50 text-blue-700",
  indexed: "bg-amber-50 text-amber-700",
  extracted: "bg-emerald-50 text-emerald-700",
};

export function PaperStatusBadge({ status }: { status: PaperStatus }) {
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${styles[status]}`}>
      {status}
    </span>
  );
}