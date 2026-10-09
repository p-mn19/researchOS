"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Check,
  Clipboard,
  FileDown,
  FileText,
  Play,
  Save,
} from "lucide-react";

import {
  compileWorkspaceLatexPdf,
  compileWorkspaceLatexStatus,
  type LatexCompileError,
} from "@/lib/api";

import { LatexCompileErrors } from "./latex_compile_errors";
import { LatexEditor } from "./latex_editor";
import { LatexPdfPreview } from "./latex_pdf_preview";

export type DocumentFormat = "normal" | "ieee";

type LatexWorkspacePanelProps = {
  workspaceId: string;
  initialLatexCode: string;
  initialDocumentFormat?: DocumentFormat;
  referencesBib?: string;
  onSave?: (
    latexCode: string,
    documentFormat: DocumentFormat,
  ) => Promise<void> | void;
};

function downloadTextFile(
  filename: string,
  content: string,
  contentType: string,
) {
  const blob = new Blob([content], {
    type: contentType,
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

function formatLabel(format: DocumentFormat): string {
  return format === "ieee"
    ? "IEEE double-column"
    : "Normal single-column";
}

export function LatexWorkspacePanel({
  workspaceId,
  initialLatexCode,
  initialDocumentFormat = "normal",
  referencesBib = "",
  onSave,
}: LatexWorkspacePanelProps) {
  const [latexCode, setLatexCode] = useState(initialLatexCode);
  const [documentFormat, setDocumentFormat] =
    useState<DocumentFormat>(initialDocumentFormat);

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  const [compileError, setCompileError] = useState("");
  const [compileErrors, setCompileErrors] = useState<
    LatexCompileError[]
  >([]);
  const [compileLog, setCompileLog] = useState("");

  const pdfUrlRef = useRef<string | null>(null);

  useEffect(() => {
    setLatexCode(initialLatexCode);
  }, [initialLatexCode]);

  useEffect(() => {
    setDocumentFormat(initialDocumentFormat);
  }, [initialDocumentFormat]);

  useEffect(() => {
    return () => {
      if (pdfUrlRef.current) {
        URL.revokeObjectURL(pdfUrlRef.current);
      }
    };
  }, []);

  function replacePdfUrl(nextUrl: string | null) {
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
    }

    pdfUrlRef.current = nextUrl;
    setPdfUrl(nextUrl);
  }

  async function handleCompile() {
    if (!workspaceId || !latexCode.trim() || compiling) {
      return;
    }

    try {
      setCompiling(true);
      setCompileError("");
      setCompileErrors([]);
      setCompileLog("");

      const status = await compileWorkspaceLatexStatus(
        workspaceId,
        latexCode,
        referencesBib,
        documentFormat,
      );

      if (!status.success) {
        setCompileError("LaTeX compilation failed.");
        setCompileErrors(status.errors);
        setCompileLog(status.log);
        return;
      }

      const pdfBlob = await compileWorkspaceLatexPdf(
        workspaceId,
        latexCode,
        referencesBib,
        documentFormat,
      );

      const nextPdfUrl = URL.createObjectURL(pdfBlob);
      replacePdfUrl(nextPdfUrl);
    } catch (error) {
      setCompileError(
        error instanceof Error
          ? error.message
          : "LaTeX compilation failed.",
      );
    } finally {
      setCompiling(false);
    }
  }

  async function handleSave() {
    if (!onSave || saving) {
      return;
    }

    try {
      setSaving(true);
      await onSave(latexCode, documentFormat);
    } finally {
      setSaving(false);
    }
  }

  function handleFormatChange(
    event: React.ChangeEvent<HTMLSelectElement>,
  ) {
    const nextFormat = event.target.value as DocumentFormat;

    if (nextFormat === documentFormat) {
      return;
    }

    const confirmed = window.confirm(
      `Switch to ${formatLabel(nextFormat)}? Review the LaTeX preamble after changing the format.`,
    );

    if (!confirmed) {
      return;
    }

    setDocumentFormat(nextFormat);
    replacePdfUrl(null);
  }

  async function handleCopyLatex() {
    try {
      await navigator.clipboard.writeText(latexCode);
      setCopied(true);

      window.setTimeout(() => {
        setCopied(false);
      }, 1800);
    } catch {
      setCompileError(
        "Unable to copy LaTeX. Please select and copy it manually.",
      );
    }
  }

  function handleDownloadTex() {
    downloadTextFile(
      "main.tex",
      latexCode,
      "application/x-tex",
    );
  }

  function handleDownloadBib() {
    downloadTextFile(
      "references.bib",
      referencesBib,
      "application/x-bibtex",
    );
  }

  return (
    <section className="space-y-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex items-center gap-2">
          <div className="rounded-xl bg-violet-50 p-2 text-violet-700">
            <FileText className="h-5 w-5" />
          </div>

          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              LaTeX workspace
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Edit your research draft, compile it with Tectonic,
              and preview the resulting PDF.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2">
            <label
              htmlFor="document-format"
              className="text-xs font-medium text-slate-600"
            >
              Format
            </label>

            <select
              id="document-format"
              value={documentFormat}
              onChange={handleFormatChange}
              disabled={compiling || saving}
              className="bg-transparent text-sm font-medium text-slate-800 outline-none disabled:cursor-not-allowed disabled:opacity-60"
            >
              <option value="normal">
                Normal single-column
              </option>

              <option value="ieee">
                IEEE double-column
              </option>
            </select>
          </div>

          {onSave && (
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save className="h-4 w-4" />
              {saving ? "Saving..." : "Save version"}
            </button>
          )}

          <button
            type="button"
            onClick={() => void handleCopyLatex()}
            disabled={!latexCode.trim()}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {copied ? (
              <Check className="h-4 w-4 text-emerald-600" />
            ) : (
              <Clipboard className="h-4 w-4" />
            )}

            {copied ? "Copied" : "Copy LaTeX"}
          </button>

          <button
            type="button"
            onClick={handleDownloadTex}
            disabled={!latexCode.trim()}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FileDown className="h-4 w-4" />
            Download .tex
          </button>

          {referencesBib.trim() && (
            <button
              type="button"
              onClick={handleDownloadBib}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <FileDown className="h-4 w-4" />
              Download .bib
            </button>
          )}

          <button
            type="button"
            onClick={() => void handleCompile()}
            disabled={compiling || !latexCode.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            <Play className="h-4 w-4" />
            {compiling ? "Compiling..." : "Compile PDF"}
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        <span className="font-semibold">
          Active layout: {formatLabel(documentFormat)}.
        </span>{" "}
        The selected layout is included in save and compile requests.
      </div>

      <LatexCompileErrors
        errorMessage={compileError}
        errors={compileErrors}
        log={compileLog}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <LatexEditor
          value={latexCode}
          onChange={setLatexCode}
          disabled={compiling}
        />

        <LatexPdfPreview
          pdfUrl={pdfUrl}
          compiling={compiling}
        />
      </div>

      {referencesBib.trim() && (
        <details className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-slate-700">
            View references.bib
          </summary>

          <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-950 p-4 font-mono text-xs leading-5 text-emerald-200">
            {referencesBib}
          </pre>
        </details>
      )}
    </section>
  );
}