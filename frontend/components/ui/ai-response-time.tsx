import { Clock3 } from "lucide-react";

type AiResponseTimeProps = {
  milliseconds: number | null;
  label?: string;
};

function formatSeconds(milliseconds: number): string {
  const seconds = Math.max(0, milliseconds / 1000);

  return seconds < 10
    ? `${seconds.toFixed(1)}s`
    : `${Math.round(seconds)}s`;
}

export function AiResponseTime({
  milliseconds,
  label = "AI responded",
}: AiResponseTimeProps) {
  if (milliseconds === null) {
    return null;
  }

  return (
    <p className="inline-flex items-center gap-1.5 text-xs text-slate-400">
      <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
      {label} in {formatSeconds(milliseconds)}
    </p>
  );
}
