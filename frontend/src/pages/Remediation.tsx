
import React, { useContext, useMemo, useState } from "react";
import { Copy, Wrench, Check, ShieldCheck } from "lucide-react";
import { ScanResultContext } from "../App";
import EmptyState from "../components/EmptyState";
import type { Vulnerability } from "../types";

interface RemediationFinding extends Vulnerability {
  installation_path: string;
}

const Remediation: React.FC = () => {
  const { result } = useContext(ScanResultContext);
  const [copied, setCopied] = useState("");

  const findings = useMemo<RemediationFinding[]>(() => {
    if (!result) return [];
    return Object.entries(result.vulnerabilities).flatMap(([path, items]) =>
      items.map((item) => ({ ...item, installation_path: path }))
    );
  }, [result]);

  const copyCommand = async (command: string, id: string) => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(id);
      window.setTimeout(() => setCopied(""), 1800);
    } catch {
      setCopied("");
      window.alert("Clipboard access unavailable. Please copy the command manually.");
    }
  };

  if (!result) {
    return (
      <EmptyState
        title="No remediation data"
        description="Run a dependency scan to see available fixes."
      />
    );
  }

  const uniquePackages = new Set(
    findings.filter((item) => item.recommended_fixed_versions?.length)
      .map((item) => item.package_name)
  );

  return (
    <div className="space-y-7">
      <div>
        <p className="eyebrow">Security improvements</p>
        <h1 className="page-title mt-2">Remediation center</h1>
        <p className="page-subtitle">
          Review fixed-version information reported by OSV for affected packages.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="panel p-5">
          <p className="eyebrow">Findings reviewed</p>
          <p className="mt-3 text-3xl font-bold text-white">{findings.length}</p>
        </div>
        <div className="panel p-5">
          <p className="eyebrow">Packages with reported fixes</p>
          <p className="mt-3 text-3xl font-bold text-emerald-300">
            {uniquePackages.size}
          </p>
        </div>
      </div>

      {findings.length === 0 ? (
        <EmptyState
          title="No remediation actions"
          description="No vulnerability findings were returned in the latest scan."
        />
      ) : (
        <div className="space-y-4">
          {findings.map((item, index) => {
            const fixes = item.recommended_fixed_versions ?? [];
            const hasFix = item.remediation_status === "fix_available" && fixes.length > 0;
            const command = hasFix
              ? `npm install ${item.package_name}@${fixes[0]}`
              : "";
            const key = `${item.id}-${index}`;

            return (
              <article key={key} className="panel p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Wrench size={17} className="text-violet-300" />
                      <h2 className="font-bold text-white">{item.package_name}</h2>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      {item.id} · Installed: {item.installed_version}
                    </p>
                  </div>

                  {hasFix ? (
                    <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">
                      Fix reported
                    </span>
                  ) : (
                    <span className="rounded-full bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-300">
                      Review required
                    </span>
                  )}
                </div>

                {hasFix ? (
                  <>
                    <div className="mt-5">
                      <p className="eyebrow">Compatible fixed version(s)</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {fixes.map((version) => (
                          <span key={version} className="rounded-lg border border-emerald-400/15 bg-emerald-400/[0.06] px-3 py-1.5 text-sm font-semibold text-emerald-300">
                            {version}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="mt-4 flex flex-col justify-between gap-3 rounded-xl bg-[#0b1323] p-4 sm:flex-row sm:items-center">
                      <code className="break-all text-sm text-slate-300">
                        {command}
                      </code>
                      <button
                        onClick={() => copyCommand(command, key)}
                        className="button-secondary shrink-0"
                      >
                        {copied === key ? <Check size={15} /> : <Copy size={15} />}
                        {copied === key ? "Copied" : "Copy command"}
                      </button>
                    </div>
                  </>
                ) : (
                  <p className="mt-4 text-sm leading-6 text-amber-200">
                    {item.remediation_status === "no_fix_available"
                      ? "OSV reports no fixed version for the matching affected range. Monitor the advisory for updates."
                      : "A compatible fix could not be determined from the available advisory data."}
                  </p>
                )}

                <p className="mt-4 break-all border-t border-white/[0.06] pt-3 text-xs text-slate-500">
                  Installation path: {item.installation_path}
                </p>
              </article>
            );
          })}
        </div>
      )}

      <div className="flex gap-3 rounded-xl border border-sky-400/15 bg-sky-400/[0.05] p-4">
        <ShieldCheck className="shrink-0 text-sky-300" size={18} />
        <p className="text-xs leading-6 text-slate-400">
          Review package compatibility and test upgrades before applying them
          to production. A reported fixed version is not a guarantee that an
          upgrade is safe for your application.
        </p>
      </div>
    </div>
  );
};

export default Remediation;

