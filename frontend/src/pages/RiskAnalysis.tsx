
import React, { useContext } from "react";
import { ShieldAlert, Info } from "lucide-react";
import { ScanResultContext } from "../App";
import EmptyState from "../components/EmptyState";
import type { Vulnerability, RiskLevel } from "../types";

const colors: Record<RiskLevel, string> = {
  critical: "text-rose-300 bg-rose-400/10",
  high: "text-orange-300 bg-orange-400/10",
  medium: "text-amber-300 bg-amber-400/10",
  low: "text-emerald-300 bg-emerald-400/10",
  unknown: "text-slate-300 bg-slate-400/10",
};

const RiskAnalysis: React.FC = () => {
  const { result } = useContext(ScanResultContext);

  if (!result) {
    return (
      <EmptyState
        title="No risk analysis available"
        description="Run a dependency scan to calculate risk scores."
      />
    );
  }

  const findings: Vulnerability[] = Object.values(result.vulnerabilities).flat();
  const summary = result.risk_summary;

  return (
    <div className="space-y-7">
      <div>
        <p className="eyebrow">Explainable security scoring</p>
        <h1 className="page-title mt-2">Risk intelligence</h1>
        <p className="page-subtitle">
          Understand how vulnerability data is prioritized by DepGuard.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {(["critical", "high", "medium", "low", "unknown"] as RiskLevel[]).map((level) => (
          <div key={level} className="panel p-4">
            <span className={`rounded-lg px-2.5 py-1 text-xs font-bold capitalize ${colors[level]}`}>
              {level}
            </span>
            <p className="mt-4 text-3xl font-bold text-white">
              {summary[level] ?? 0}
            </p>
            <p className="mt-1 text-xs text-slate-500">Findings</p>
          </div>
        ))}
      </div>

      <section className="panel p-6">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-violet-400/10 p-3 text-violet-300">
            <ShieldAlert size={22} />
          </div>
          <div>
            <p className="eyebrow">Scoring model</p>
            <h2 className="mt-1 text-xl font-bold text-white">
              How DepGuard calculates risk
            </h2>
          </div>
        </div>

        <p className="mt-4 text-sm leading-7 text-slate-400">
          DepGuard uses a project-specific heuristic model. It considers CVSS
          severity, dependency directness and remediation availability.
          Available factor weights are normalized when some inputs are missing.
          A finding without a supported CVSS score is classified as unknown.
        </p>

        <div className="mt-6 space-y-5">
          {[
            { label: "CVSS severity", weight: 70, color: "#8b7cff" },
            { label: "Dependency directness", weight: 20, color: "#38bdf8" },
            { label: "Remediation availability", weight: 10, color: "#34d399" },
          ].map((item) => (
            <div key={item.label}>
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-slate-300">{item.label}</span>
                <span className="font-bold text-white">{item.weight}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${item.weight}%`, background: item.color }}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex gap-3 rounded-xl border border-sky-400/15 bg-sky-400/[0.05] p-4">
          <Info size={18} className="shrink-0 text-sky-300" />
          <p className="text-xs leading-6 text-slate-400">
            These weights are DepGuard project heuristics, not an official
            industry-standard risk formula. CVSS and DepGuard risk scores are
            different measures.
          </p>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="eyebrow">Finding-level explanations</p>
          <h2 className="mt-2 text-xl font-bold text-white">
            Why each finding received its score
          </h2>
        </div>

        {findings.length === 0 ? (
          <EmptyState
            title="No vulnerability findings"
            description="No vulnerability findings were returned by this scan."
          />
        ) : findings.map((item, index) => {
          const level = item.risk_level ?? "unknown";

          return (
            <article key={`${item.id}-${index}`} className="panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-white">
                    {item.package_name}@{item.installed_version}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">{item.id}</p>
                  <p className="mt-2 text-sm text-slate-400">
                    {item.summary || "No summary supplied"}
                  </p>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-bold capitalize ${colors[level]}`}>
                  {level}
                </span>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-white/[0.035] p-3">
                  <p className="eyebrow">Risk score</p>
                  <p className="mt-1 text-xl font-bold text-white">
                    {item.risk_score != null ? `${item.risk_score}/100` : "Unknown"}
                  </p>
                </div>
                <div className="rounded-xl bg-white/[0.035] p-3">
                  <p className="eyebrow">CVSS</p>
                  <p className="mt-1 text-xl font-bold text-white">
                    {item.cvss_score != null ? `${item.cvss_score}/10` : "N/A"}
                  </p>
                </div>
                <div className="rounded-xl bg-white/[0.035] p-3">
                  <p className="eyebrow">Confidence</p>
                  <p className="mt-1 text-xl font-bold capitalize text-white">
                    {item.score_confidence ?? "Unknown"}
                  </p>
                </div>
              </div>

              {item.risk_reasons?.length ? (
                <ul className="mt-4 space-y-2">
                  {item.risk_reasons.map((reason, reasonIndex) => (
                    <li key={reasonIndex} className="flex gap-2 text-sm text-slate-400">
                      <span className="mt-1 text-violet-300">•</span>
                      {reason}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-4 text-xs text-slate-500">
                  No additional scoring explanation was supplied.
                </p>
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
};

export default RiskAnalysis;

