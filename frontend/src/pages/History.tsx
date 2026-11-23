
import React, { useContext } from "react";
import { Trash2, Clock3, FileJson, CheckCircle2, AlertTriangle } from "lucide-react";
import { ScanResultContext } from "../App";
import EmptyState from "../components/EmptyState";

const History: React.FC = () => {
  const { history, clearHistory } = useContext(ScanResultContext);

  const handleClear = () => {
    if (window.confirm("Clear all locally saved scan history?")) {
      clearHistory();
    }
  };

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="eyebrow">Previous analyses</p>
          <h1 className="page-title mt-2">Scan history</h1>
          <p className="page-subtitle">
            Recent scans saved locally in this browser.
          </p>
        </div>

        {history.length > 0 && (
          <button onClick={handleClear} className="button-secondary border-rose-400/20 text-rose-300 hover:bg-rose-400/10">
            <Trash2 size={16} /> Clear history
          </button>
        )}
      </div>

      {history.length === 0 ? (
        <EmptyState
          title="No scan history available"
          description="Your completed scans will appear here."
        />
      ) : (
        <div className="space-y-3">
          {history.map((item) => (
            <article key={item.id} className="panel panel-hover p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex min-w-0 items-center gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300">
                    <FileJson size={22} />
                  </div>

                  <div className="min-w-0">
                    <h2 className="truncate font-bold text-white">
                      {item.file_name}
                    </h2>
                    <p className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                      <Clock3 size={13} />
                      {new Date(item.scanned_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {item.status === "complete" ? (
                    <span className="flex items-center gap-1.5 rounded-full bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-300">
                      <CheckCircle2 size={14} /> Complete
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 rounded-full bg-amber-400/10 px-3 py-1.5 text-xs font-semibold text-amber-300">
                      <AlertTriangle size={14} /> Partial
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/[0.06] pt-4 sm:grid-cols-5">
                {(["critical", "high", "medium", "low", "unknown"] as const).map((level) => (
                  <div key={level}>
                    <p className="text-[10px] uppercase tracking-wider text-slate-500">
                      {level}
                    </p>
                    <p className="mt-1 text-lg font-bold text-white">
                      {item.risk_summary[level] ?? 0}
                    </p>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}

      <p className="text-xs leading-5 text-slate-600">
        Scan history is stored in your browser's local storage. It is not
        persisted by the backend or synchronized between devices.
      </p>
    </div>
  );
};

export default History;

