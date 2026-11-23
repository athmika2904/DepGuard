
import React, { useContext } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  ShieldAlert, ShieldCheck, AlertTriangle, Activity,
  ArrowUpRight, ScanSearch, GitBranch, Clock3,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ScanResultContext } from "../App";
import EmptyState from "../components/EmptyState";

const levels = [
  { key: "critical", label: "Critical", color: "#f43f5e" },
  { key: "high", label: "High", color: "#fb923c" },
  { key: "medium", label: "Medium", color: "#facc15" },
  { key: "low", label: "Low", color: "#34d399" },
  { key: "unknown", label: "Unknown", color: "#64748b" },
] as const;

const Dashboard: React.FC = () => {
  const { result, history } = useContext(ScanResultContext);
  const navigate = useNavigate();

  if (!result) {
    return (
      <div className="space-y-7">
        <div>
          <p className="eyebrow">Security command center</p>
          <h1 className="page-title mt-2">Welcome to DepGuard.</h1>
          <p className="page-subtitle">
            Your software supply chain security overview starts here.
          </p>
        </div>

        <div className="panel relative overflow-hidden p-8 md:p-12">
          <div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-violet-500/10 blur-3xl" />
          <div className="relative max-w-xl">
            <div className="mb-5 inline-flex rounded-xl border border-violet-400/20 bg-violet-400/10 p-3 text-violet-300">
              <ShieldCheck size={27} />
            </div>
            <h2 className="text-3xl font-bold text-white">
              Understand your dependency risks.
            </h2>
            <p className="mt-4 leading-7 text-slate-400">
              Upload your npm package-lock.json to discover known
              vulnerabilities, explore dependency paths and prioritize
              available fixes.
            </p>
            <button
              onClick={() => navigate("/scan")}
              className="button-primary mt-7"
            >
              <ScanSearch size={17} /> Start your first scan
            </button>
          </div>
        </div>

        <EmptyState
          title="No scan data yet"
          description="Complete your first dependency scan to populate the dashboard."
        />
      </div>
    );
  }

  const summary = result.risk_summary;

  const chartData = levels
    .map((level) => ({
      name: level.label,
      value: summary[level.key] ?? 0,
      color: level.color,
    }))
    .filter((item) => item.value > 0);

  const stats = [
    {
      label: "Total findings",
      value: summary.total,
      icon: ShieldAlert,
      color: "text-violet-300",
      background: "bg-violet-400/10",
    },
    {
      label: "Critical",
      value: summary.critical,
      icon: AlertTriangle,
      color: "text-rose-300",
      background: "bg-rose-400/10",
    },
    {
      label: "High",
      value: summary.high,
      icon: Activity,
      color: "text-orange-300",
      background: "bg-orange-400/10",
    },
    {
      label: "Medium",
      value: summary.medium,
      icon: ShieldAlert,
      color: "text-amber-300",
      background: "bg-amber-400/10",
    },
  ];

  const lookupErrors = Object.keys(result.errors ?? {}).length;

  return (
    <div className="space-y-7">
      <section className="relative overflow-hidden rounded-3xl border border-violet-400/15 bg-gradient-to-br from-[#1b2140] via-[#151b32] to-[#101a2c] p-7 md:p-9">
        <div className="absolute -right-10 -top-24 h-72 w-72 rounded-full bg-violet-500/15 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div>
            <p className="eyebrow text-violet-300">Security command center</p>
            <h1 className="mt-3 text-3xl font-bold text-white md:text-4xl">
              Security overview
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
              Monitor vulnerability findings and understand the current
              security posture of your dependency ecosystem.
            </p>
          </div>

          <button
            onClick={() => navigate("/scan")}
            className="button-primary shrink-0"
          >
            <ScanSearch size={17} /> New scan
          </button>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="panel panel-hover p-5">
              <div className="flex items-center justify-between">
                <div className={`rounded-xl p-3 ${stat.background} ${stat.color}`}>
                  <Icon size={20} />
                </div>
                <ArrowUpRight size={16} className="text-slate-600" />
              </div>
              <p className="mt-5 text-3xl font-bold text-white">
                {stat.value ?? 0}
              </p>
              <p className="mt-1 text-sm text-slate-400">{stat.label}</p>
            </div>
          );
        })}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="panel p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="eyebrow">Finding breakdown</p>
              <h2 className="mt-2 text-xl font-bold text-white">
                Risk distribution
              </h2>
            </div>
            <div className="rounded-xl bg-violet-400/10 p-3 text-violet-300">
              <Activity size={20} />
            </div>
          </div>

          {chartData.length === 0 ? (
            <div className="flex h-64 items-center justify-center text-sm text-slate-500">
              No vulnerability findings in this scan.
            </div>
          ) : (
            <div className="grid items-center gap-4 md:grid-cols-2">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={67}
                      outerRadius={100}
                      paddingAngle={4}
                      stroke="none"
                    >
                      {chartData.map((item) => (
                        <Cell key={item.name} fill={item.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "#111a2c",
                        border: "1px solid #344158",
                        borderRadius: 12,
                        color: "#fff",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-4">
                {levels.map((level) => (
                  <div key={level.key} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ background: level.color }}
                      />
                      <span className="text-sm text-slate-400">
                        {level.label}
                      </span>
                    </div>
                    <span className="text-sm font-bold text-white">
                      {summary[level.key] ?? 0}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="panel p-6">
          <p className="eyebrow">Latest analysis</p>
          <h2 className="mt-2 text-xl font-bold text-white">Scan status</h2>

          <div className="mt-7 flex items-center gap-4">
            <div className={`flex h-14 w-14 items-center justify-center rounded-2xl ${
              result.status === "complete"
                ? "bg-emerald-400/10 text-emerald-300"
                : "bg-amber-400/10 text-amber-300"
            }`}>
              {result.status === "complete"
                ? <ShieldCheck size={26} />
                : <AlertTriangle size={26} />}
            </div>
            <div>
              <p className="text-lg font-bold capitalize text-white">
                {result.status}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Latest scan result
              </p>
            </div>
          </div>

          <div className="mt-7 space-y-4 border-t border-white/[0.07] pt-5">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Lookup errors</span>
              <span className="font-semibold text-white">{lookupErrors}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Findings returned</span>
              <span className="font-semibold text-white">{summary.total}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Previous local scans</span>
              <span className="font-semibold text-white">{history.length}</span>
            </div>
          </div>

          {result.status === "partial" && (
            <p className="mt-5 rounded-xl border border-amber-400/15 bg-amber-400/[0.06] p-3 text-xs leading-5 text-amber-200">
              Some vulnerability lookups failed. Findings may be incomplete.
            </p>
          )}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <button
          onClick={() => navigate("/vulnerabilities")}
          className="panel panel-hover flex items-center justify-between p-5 text-left"
        >
          <div>
            <p className="font-semibold text-white">Explore vulnerabilities</p>
            <p className="mt-1 text-xs text-slate-400">
              Inspect advisories and affected packages.
            </p>
          </div>
          <ShieldAlert className="text-violet-300" />
        </button>

        <button
          onClick={() => navigate("/graph")}
          className="panel panel-hover flex items-center justify-between p-5 text-left"
        >
          <div>
            <p className="font-semibold text-white">Explore dependency graph</p>
            <p className="mt-1 text-xs text-slate-400">
              Understand direct and transitive relationships.
            </p>
          </div>
          <GitBranch className="text-cyan-300" />
        </button>
      </section>

      {history.length > 0 && (
        <section className="panel p-6">
          <div className="flex items-center gap-2">
            <Clock3 size={18} className="text-violet-300" />
            <h2 className="font-bold text-white">Recent local scan</h2>
          </div>
          <p className="mt-3 text-sm text-slate-300">{history[0].file_name}</p>
          <p className="mt-1 text-xs text-slate-500">
            {new Date(history[0].scanned_at).toLocaleString()}
          </p>
        </section>
      )}
    </div>
  );
};

export default Dashboard;


