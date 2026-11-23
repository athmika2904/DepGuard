
import React, { createContext, useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import Sidebar from "./components/Sidebar";

import Dashboard from "./pages/Dashboard";
import ScanPage from "./pages/Scan";
import Vulnerabilities from "./pages/Vulnerabilities";
import DependencyGraph from "./pages/DependencyGraph";
import RiskAnalysis from "./pages/RiskAnalysis";
import Remediation from "./pages/Remediation";
import History from "./pages/History";

import type { ScanResult, ScanHistoryEntry } from "./types";
import { Bell, ShieldCheck } from "lucide-react";

interface ScanContextType {
  result: ScanResult | null;
  setResult: React.Dispatch<React.SetStateAction<ScanResult | null>>;
  history: ScanHistoryEntry[];
  addHistory: (entry: ScanHistoryEntry) => void;
  clearHistory: () => void;
}

export const ScanResultContext = createContext<ScanContextType>({
  result: null,
  setResult: () => {},
  history: [],
  addHistory: () => {},
  clearHistory: () => {},
});

const pageNames: Record<string, string> = {
  "/dashboard": "Overview",
  "/scan": "New Scan",
  "/vulnerabilities": "Vulnerabilities",
  "/graph": "Dependency Graph",
  "/risk": "Risk Intelligence",
  "/remediation": "Remediation",
  "/history": "Scan History",
};

const App: React.FC = () => {
  const location = useLocation();

  const [scanResult, setScanResult] = useState<ScanResult | null>(null);

  const [history, setHistory] = useState<ScanHistoryEntry[]>(() => {
    try {
      const saved = localStorage.getItem("depguard-history");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem("depguard-history", JSON.stringify(history));
  }, [history]);

  const addHistory = (entry: ScanHistoryEntry) => {
    setHistory((previous) => [entry, ...previous].slice(0, 20));
  };

  const clearHistory = () => setHistory([]);

  return (
    <ScanResultContext.Provider
      value={{
        result: scanResult,
        setResult: setScanResult,
        history,
        addHistory,
        clearHistory,
      }}
    >
      <div className="flex min-h-screen flex-col md:flex-row">
        <Sidebar />

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 flex items-center justify-between border-b border-white/[0.06] bg-[#090e1b]/85 px-5 py-4 backdrop-blur-xl md:px-8">
            <div>
              <p className="eyebrow">DepGuard / Workspace</p>
              <h2 className="mt-1 text-sm font-semibold text-white">
                {pageNames[location.pathname] ?? "Security Workspace"}
              </h2>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-full border border-emerald-400/15 bg-emerald-400/[0.06] px-3 py-2 sm:flex">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="text-xs font-medium text-emerald-300">
                  Local workspace
                </span>
              </div>

              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
                <Bell size={16} className="text-slate-400" />
              </div>

              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
                <ShieldCheck size={18} />
              </div>
            </div>
          </header>

          <div className="mx-auto w-full max-w-[1600px] p-5 md:p-8">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/scan" element={<ScanPage />} />
              <Route path="/vulnerabilities" element={<Vulnerabilities />} />
              <Route path="/graph" element={<DependencyGraph />} />
              <Route path="/risk" element={<RiskAnalysis />} />
              <Route path="/remediation" element={<Remediation />} />
              <Route path="/history" element={<History />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>

            <footer className="mt-12 border-t border-white/[0.06] py-5 text-center text-xs text-slate-600">
              DepGuard · Explainable Software Dependency Risk Analysis
            </footer>
          </div>
        </main>
      </div>
    </ScanResultContext.Provider>
  );
};

export default App;


