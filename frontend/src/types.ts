
export interface SeverityItem {
  type?: string;
  score?: string | number;
}

export type RiskLevel =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "unknown";

export interface Vulnerability {
  id: string;
  summary?: string | null;
  details?: string | null;
  aliases?: string[] | null;

  package_name: string;
  ecosystem: string;
  installed_version: string;

  affected_ranges?: unknown[] | null;
  fixed_versions?: string[] | null;
  recommended_fixed_versions?: string[] | null;

  remediation_status?:
    | "fix_available"
    | "no_fix_available"
    | "unknown"
    | null;

  references?: string[] | null;
  severity?: SeverityItem[] | null;

  published?: string | null;
  modified?: string | null;

  dependency_paths?: string[][] | null;
  direct?: boolean | null;
  dependency_depth?: number | null;

  cvss_score?: number | null;
  cvss_severity?: string | null;

  risk_score?: number | null;
  risk_level?: RiskLevel | null;
  risk_factors?: Record<string, number>;
  risk_reasons?: string[];
  score_confidence?: "high" | "medium" | "low" | null;
}

export interface GraphNode {
  id: string;
  name?: string;
  version?: string;
  path?: string;
  direct?: boolean;
  scope?: string[];
  parents?: string[];
  depth?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  dep_type?: string[] | string;
}

export interface DependencyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RiskSummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  unknown: number;
  total: number;
}

export interface ScanResult {
  status: "complete" | "partial";
  vulnerabilities: Record<string, Vulnerability[]>;
  errors: Record<string, string>;
  graph: DependencyGraph | null;
  risk_summary: RiskSummary;
}

export interface ScanHistoryEntry {
  id: string;
  file_name: string;
  scanned_at: string;
  status: "complete" | "partial";
  risk_summary: RiskSummary;
}
