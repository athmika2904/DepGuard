
import React, { useContext, useMemo, useState } from "react";
import { Search, ShieldAlert, Filter } from "lucide-react";
import { ScanResultContext } from "../App";
import type { Vulnerability, RiskLevel } from "../types";
import EmptyState from "../components/EmptyState";

interface Finding extends Vulnerability {
  installation_path: string;
}

const riskColor: Record<RiskLevel, string> = {
  critical: "border-rose-400/20 bg-rose-400/10 text-rose-300",
  high: "border-orange-400/20 bg-orange-400/10 text-orange-300",
  medium: "border-amber-400/20 bg-amber-400/10 text-amber-300",
  low: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
  unknown: "border-slate-400/20 bg-slate-400/10 text-slate-300",
};

const Vulnerabilities: React.FC = () => {
  const { result } = useContext(ScanResultContext);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const findings = useMemo<Finding[]>(() => {
    if (!result) return [];
    return Object.entries(result.vulnerabilities).flatMap(([path, items]) =>
      items.map((item) => ({ ...item, installation_path: path }))
    );
  }, [result]);

  const filtered = findings.filter((item) => {
    const text = [
      item.id, item.package_name, item.installed_version,
      item.summary, item.installation_path,
    ].filter(Boolean).join(" ").toLowerCase();

    return text.includes(search.toLowerCase()) &&
      (filter === "all" || (item.risk_level ?? "unknown") === filter);
  });

  if (!result) {
    return (
      <EmptyState
        title="No scan results"
        description="Run a dependency scan before viewing vulnerabilities."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="eyebrow">Security findings</p>
        <h1 className="page-title mt-2">Vulnerabilities</h1>
        <p className="page-subtitle">
          {findings.length} finding(s) returned by the latest scan.
        </p>
      </div>

      <div className="panel flex flex-col gap-3 p-4 md:flex-row">
        <div className="relative flex-1">
          <Search size={17} className="absolute left-3 top-3.5 text-slate-500" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search advisory, package or dependency path..."
            className="input-dark pl-10"
          />
        </div>

        <div className="relative md:w-52">
          <Filter size={15} className="pointer-events-none absolute left-3 top-3.5 text-slate-500" />
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            className="input-dark appearance-none pl-9"
          >
            <option value="all">All risk levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {(["critical", "high", "medium", "low", "unknown"] as RiskLevel[]).map((level) => (
          <button
            key={level}
            onClick={() => setFilter(filter === level ? "all" : level)}
            className={`rounded-xl border p-3 text-left transition ${
              filter === level ? riskColor[level] : "border-white/[0.07] bg-[#111a2c] text-slate-400"
            }`}
          >
            <p className="text-xs capitalize">{level}</p>
            <p className="mt-1 text-xl font-bold text-white">
              {result.risk_summary[level] ?? 0}
            </p>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No matching vulnerabilities"
          description="Try a different search term or risk-level filter."
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((item, index) => {
            const level = item.risk_level ?? "unknown";

            return (
              <article
                key={`${item.id}-${item.installation_path}-${index}`}
                className="panel panel-hover p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-violet-300">{item.id}</span>
                      <span className={`rounded-full border px-3 py-1 text-[11px] font-bold capitalize ${riskColor[level]}`}>
                        {level}
                      </span>
                    </div>
                    <h2 className="mt-3 text-lg font-bold text-white">
                      {item.package_name}
                      <span className="ml-2 text-sm font-normal text-slate-500">
                        @{item.installed_version}
                      </span>
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      {item.summary || "No advisory summary supplied."}
                    </p>
                  </div>
                  <ShieldAlert className="shrink-0 text-slate-500" size={21} />
                </div>

                <div className="mt-5 grid gap-3 border-t border-white/[0.06] pt-4 sm:grid-cols-3">
                  <div>
                    <p className="eyebrow">CVSS</p>
                    <p className="mt-1 text-sm font-semibold text-white">
                      {item.cvss_score != null ? `${item.cvss_score.toFixed(1)} / 10` : "Unavailable"}
                    </p>
                  </div>
                  <div>
                    <p className="eyebrow">DepGuard risk score</p>
                    <p className="mt-1 text-sm font-semibold text-white">
                      {item.risk_score != null ? `${item.risk_score}/100` : "Unknown"}
                    </p>
                  </div>
                  <div>
                    <p className="eyebrow">Recommended fix</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-300">
                      {item.recommended_fixed_versions?.join(", ") || "Not available"}
                    </p>
                  </div>
                </div>

                <div className="mt-4 rounded-xl bg-white/[0.035] p-3">
                  <p className="eyebrow">Dependency path</p>
                  <p className="mt-2 break-words text-xs leading-5 text-slate-400">
                    {item.dependency_paths?.[0]?.join(" → ") ?? item.installation_path}
                  </p>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {result.status === "partial" && (
        <p className="rounded-xl border border-amber-400/15 bg-amber-400/[0.05] p-4 text-sm text-amber-200">
          This scan is partial. Some OSV lookups failed, so findings may be incomplete.
        </p>
      )}
    </div>
  );
};

export default Vulnerabilities;


