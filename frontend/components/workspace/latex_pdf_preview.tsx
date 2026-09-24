"use client";

type LatexPdfPreviewProps = {
  pdfUrl: string | null;
  compiling?: boolean;
};

export function LatexPdfPreview({
  pdfUrl,
  compiling = false,
}: LatexPdfPreviewProps) {
  if (compiling) {
    return (
      <div className="flex min-h-[620px] items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 p-6 text-center">
        <div>
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />

          <p className="mt-4 text-sm font-medium text-slate-700">
            Compiling LaTeX with Tectonic...
          </p>

          <p className="mt-1 text-xs text-slate-500">
            This may take longer on the first compilation.
          </p>
        </div>
      </div>
    );
  }

  if (!pdfUrl) {
    return (
      <div className="flex min-h-[620px] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
        <div className="max-w-xs">
          <p className="text-sm font-semibold text-slate-700">
            PDF preview
          </p>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            Edit the LaTeX source and select Compile PDF to create
            a preview.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            PDF preview
          </p>

          <p className="mt-0.5 text-xs text-slate-500">
            Generated locally by the ResearchOS workspace.
          </p>
        </div>

        <a
          href={pdfUrl}
          download="researchos-document.pdf"
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
        >
          Download PDF
        </a>
      </div>

      <iframe
        title="Compiled LaTeX PDF preview"
        src={pdfUrl}
        className="h-[620px] w-full bg-slate-100"
      />
    </div>
  );
}