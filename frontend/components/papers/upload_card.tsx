"use client";

import { useState } from "react";
import { uploadPaper } from "@/lib/api";
import { UploadCloud } from "lucide-react";

export function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleUpload = async () => {
    if (!file) return;

    try {
      setLoading(true);
      setMessage("");
      const result = await uploadPaper(file);
      console.log("Upload result:", result);
      setFile(null);
      setMessage("Upload successful");
      onUploaded();
    } catch (e) {
      console.error(e);
      setMessage("Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
        <UploadCloud className="h-5 w-5" />
      </div>

      <h3 className="text-xl font-semibold text-slate-900">Upload paper</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">
        Add a research PDF to build your structured corpus.
      </p>

      <label className="mt-5 block rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
        <span className="mb-2 block font-medium text-slate-700">Choose PDF file</span>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-sm"
        />
      </label>

      {file && (
        <p className="mt-3 text-sm text-slate-600">
          Selected: <span className="font-medium text-slate-900">{file.name}</span>
        </p>
      )}

      {message && <p className="mt-3 text-sm text-slate-600">{message}</p>}

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="mt-5 inline-flex w-full items-center justify-center rounded-2xl bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {loading ? "Uploading..." : "Upload PDF"}
      </button>
    </div>
  );
}