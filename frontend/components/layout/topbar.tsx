export function Topbar() {
  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="flex min-h-20 items-center justify-between px-6 py-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            Research Workflow Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Upload, extract, search, and compare research papers
          </p>
        </div>

        <div className="hidden rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-600 md:block">
          Ethical • Citation-grounded • Structured
        </div>
      </div>
    </header>
  );
}