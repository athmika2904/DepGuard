
import React from "react";
import { NavLink } from "react-router-dom";
import {
  Activity,
  ScanSearch,
  ShieldAlert,
  GitBranch,
  Gauge,
  Wrench,
  History,
  ShieldCheck,
  Boxes,
} from "lucide-react";

const items = [
  { to: "/dashboard", label: "Overview", icon: Activity },
  { to: "/scan", label: "New Scan", icon: ScanSearch },
  { to: "/vulnerabilities", label: "Vulnerabilities", icon: ShieldAlert },
  { to: "/graph", label: "Dependency Graph", icon: GitBranch },
  { to: "/risk", label: "Risk Intelligence", icon: Gauge },
  { to: "/remediation", label: "Remediation", icon: Wrench },
  { to: "/history", label: "Scan History", icon: History },
];

const Sidebar: React.FC = () => {
  return (
    <aside className="z-30 flex w-full shrink-0 flex-col border-b border-white/[0.07] bg-[#0c1424] md:sticky md:top-0 md:h-screen md:w-[260px] md:border-b-0 md:border-r">
      <div className="flex items-center gap-3 border-b border-white/[0.07] px-5 py-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-cyan-500 shadow-lg shadow-violet-950/40">
          <ShieldCheck size={23} className="text-white" />
        </div>

        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">
            DepGuard<span className="text-violet-400">.</span>
          </h1>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Security Intelligence
          </p>
        </div>
      </div>

      <div className="px-5 pb-2 pt-6">
        <p className="eyebrow">Workspace</p>
      </div>

      <nav className="flex gap-1 overflow-x-auto px-3 pb-4 md:flex-col md:overflow-visible">
        {items.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                  isActive
                    ? "bg-violet-500/15 text-violet-200 ring-1 ring-violet-400/20"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="mt-auto hidden p-4 md:block">
        <div className="rounded-2xl border border-violet-400/15 bg-gradient-to-br from-violet-500/10 to-cyan-500/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Boxes size={17} className="text-violet-300" />
            <span className="text-xs font-bold text-white">DepGuard Scanner</span>
          </div>
          <p className="text-xs leading-5 text-slate-400">
            Analyze npm dependencies, discover known vulnerabilities and
            understand your software supply-chain risk.
          </p>
          <p className="mt-4 border-t border-white/[0.07] pt-3 text-[10px] text-slate-500">
            Powered by OSV vulnerability data
          </p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;


