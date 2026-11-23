
import React, { useContext, useRef, useState } from "react";
import {
  UploadCloud, FileJson, Download, LoaderCircle,
  CheckCircle2, AlertCircle, X, ScanSearch,
} from "lucide-react";

import { ScanResultContext } from "../App";
import { uploadLockfile } from "../api/client";
import type { ScanResult } from "../types";

const ScanPage: React.FC = () => {
  const { result, setResult, addHistory } = useContext(ScanResultContext);

  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const selectFile = (selected: File | undefined) => {
    if (!selected) return;
    setError("");
    setSuccess("");

    if (!selected.name.toLowerCase().endsWith(".json")) {
      setFile(null);
      setError("Please select a JSON npm lockfile.");
      return;
    }

    if (selected.size > 5 * 1024 * 1024) {
      setFile(null);
      setError("File size must be below 5 MB.");
      return;
    }

    setFile(selected);
  };

  const handleScan = async () => {
    if (!file) {
      setError("Please select a package-lock.json file.");
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const data: ScanResult = await uploadLockfile(file);
      setResult(data);

      addHistory({
        id: `${Date.now()}`,
        file_name: file.name,
        scanned_at: new Date().toISOString(),
        status: data.status,
        risk_summary: data.risk_summary,
      });

      setSuccess(
        data.status === "partial"
          ? "Scan completed with some lookup errors."
          : "Your dependency scan completed successfully."
      );
    } catch (err: unknown) {
      if (typeof err === "object" && err !== null && "response" in err) {
        const response = (err as {
          response?: { data?: { detail?: string } };
        }).response;
        setError(response?.data?.detail || "The scan request failed.");
      } else {
        setError("Unable to connect to the backend. Make sure the API is running.");
      }
    } finally {
      setLoading(false);
    }
  };

  const exportJson = () => {
    if (!result) return;

    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `depguard-scan-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-7">
      <div>
        <p className="eyebrow">Dependency analysis</p>
        <h1 className="page-title mt-2">Run a security scan</h1>
        <p className="page-subtitle">
          Upload your npm lockfile to analyze dependencies against known
          vulnerability information.
        </p>
      </div>

      <section className="panel relative max-w-4xl overflow-hidden p-6 md:p-9">
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-violet-500/10 blur-3xl" />

        <div className="relative">
          <div className="mb-7 flex items-center gap-3">
            <div className="rounded-xl bg-violet-400/10 p-3 text-violet-300">
              <ScanSearch size={23} />
            </div>
            <div>
              <h2 className="font-bold text-white">Upload lockfile</h2>
              <p className="mt-1 text-xs text-slate-500">
                npm package-lock.json or npm-shrinkwrap.json
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              selectFile(event.dataTransfer.files?.[0]);
            }}
            className="flex min-h-64 w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-violet-400/25 bg-violet-400/[0.035] px-5 text-center transition hover:border-violet-400/60 hover:bg-violet-400/[0.07] disabled:opacity-50"
          >
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-400/10 text-violet-300">
              <UploadCloud size={30} />
            </div>
            <p className="font-semibold text-white">
              Drop your lockfile here
            </p>
            <p className="mt-2 text-sm text-slate-500">
              or browse files from your computer
            </p>
            <span className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold text-slate-300">
              Choose file
            </span>
          </button>

          <input
            ref={inputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={(event) => selectFile(event.target.files?.[0])}
            disabled={loading}
          />

          <p className="mt-3 text-center text-xs text-slate-600">
            JSON format · Maximum 5 MB
          </p>

          {file && (
            <div className="mt-5 flex items-center justify-between gap-3 rounded-xl border border-violet-400/20 bg-violet-400/[0.06] p-4">
              <div className="flex min-w-0 items-center gap-3">
                <FileJson className="shrink-0 text-violet-300" size={22} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">
                    {file.name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setFile(null)}
                disabled={loading}
                className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
                aria-label="Remove selected file"
              >
                <X size={17} />
              </button>
            </div>
          )}

          <button
            onClick={handleScan}
            disabled={loading || !file}
            className="button-primary mt-6 w-full"
          >
            {loading ? (
              <>
                <LoaderCircle className="animate-spin" size={18} />
                Analyzing dependencies...
              </>
            ) : (
              <>
                <ScanSearch size={18} />
                Start security scan
              </>
            )}
          </button>

          {loading && (
            <p className="soft-pulse mt-4 text-center text-xs text-violet-300">
              Parsing lockfile and checking vulnerability data...
            </p>
          )}

          {error && (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] p-4 text-sm text-rose-200">
              <AlertCircle size={18} className="shrink-0" />
              {error}
            </div>
          )}

          {success && (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] p-4 text-sm text-emerald-200">
              <CheckCircle2 size={18} className="shrink-0" />
              {success}
            </div>
          )}
        </div>
      </section>

      {result && (
        <section className="panel p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="eyebrow">Latest scan result</p>
              <h2 className="mt-2 text-xl font-bold text-white">
                {result.risk_summary.total} findings detected
              </h2>
              <p className="mt-1 text-xs capitalize text-slate-500">
                Scan status: {result.status}
              </p>
            </div>
            <button onClick={exportJson} className="button-secondary">
              <Download size={16} /> Export JSON
            </button>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
            {(["critical", "high", "medium", "low", "unknown"] as const).map((level) => (
              <div key={level} className="rounded-xl bg-white/[0.035] p-4">
                <p className="text-xs capitalize text-slate-500">{level}</p>
                <p className="mt-2 text-2xl font-bold text-white">
                  {result.risk_summary[level]}
                </p>
              </div>
            ))}
          </div>

          {Object.keys(result.errors ?? {}).length > 0 && (
            <p className="mt-5 text-sm text-amber-300">
              {Object.keys(result.errors).length} package lookup error(s).
              Check the JSON export for details.
            </p>
          )}
        </section>
      )}
    </div>
  );
};

export default ScanPage;

