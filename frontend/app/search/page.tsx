import { AppShell } from "@/components/layout/app_shell";
import { Search } from "lucide-react";

export default function SearchPage() {
  return (
    <AppShell>
      <div className="rounded-3xl border border-slate-200 bg-white p-10 shadow-sm">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
          <Search className="h-6 w-6" />
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
          Global semantic search
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
          This page can later support cross-paper search across the uploaded corpus.
        </p>
      </div>
    </AppShell>
  );
}