
import React, {
  memo,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
} from "reactflow";

import ELK from "elkjs/lib/elk.bundled.js";
import {
  Search,
  ShieldAlert,
  ShieldCheck,
  Package,
  Layers3,
  X,
  GitBranch,
  Activity,
} from "lucide-react";

import "reactflow/dist/style.css";

import { ScanResultContext } from "../App";
import EmptyState from "../components/EmptyState";

import type { ScanResult } from "../types";

type GraphNode = NonNullable<ScanResult["graph"]>["nodes"][number];

type CustomNodeData = {
  title: string;
  version: string;
  kind: string;
  vulnerable: boolean;
  findingCount: number;
  isRoot: boolean;
  direct: boolean;
  dimmed: boolean;
};

const elk = new ELK();

const NODE_WIDTH = 250;
const NODE_HEIGHT = 112;

/* --------------------------------
   CUSTOM DEPENDENCY NODE
--------------------------------- */

const DependencyNode = memo(
  ({ data, selected }: NodeProps<CustomNodeData>) => {
    const {
      title,
      version,
      kind,
      vulnerable,
      findingCount,
      isRoot,
      direct,
      dimmed,
    } = data;

    const borderColor = isRoot
      ? "#22d3ee"
      : vulnerable
        ? "#fb5252"
        : direct
          ? "#60a5fa"
          : "#475569";

    const glow = isRoot
      ? "0 0 22px rgba(34,211,238,0.22)"
      : vulnerable
        ? "0 0 24px rgba(239,68,68,0.28)"
        : selected
          ? "0 0 20px rgba(96,165,250,0.25)"
          : "0 5px 20px rgba(0,0,0,0.25)";

    return (
      <div
        className="relative transition-all duration-300"
        style={{
          width: NODE_WIDTH,
          minHeight: NODE_HEIGHT,
          opacity: dimmed ? 0.18 : 1,
          transform: selected ? "scale(1.04)" : "scale(1)",
          borderRadius: 16,
          background: isRoot
            ? "linear-gradient(135deg,#103c50,#10283d)"
            : vulnerable
              ? "linear-gradient(135deg,#541d2a,#271b2a)"
              : direct
                ? "linear-gradient(135deg,#172e50,#15253d)"
                : "linear-gradient(135deg,#1b293d,#111d30)",
          border: `1px solid ${borderColor}`,
          boxShadow: glow,
          padding: 14,
        }}
      >
        <Handle
          type="target"
          position={Position.Left}
          style={{
            background: borderColor,
            width: 9,
            height: 9,
            border: "2px solid #0b1220",
          }}
        />

        <div className="flex items-start gap-3">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
            style={{
              background: `${borderColor}22`,
              color: borderColor,
            }}
          >
            {isRoot ? (
              <ShieldCheck size={19} />
            ) : vulnerable ? (
              <ShieldAlert size={19} />
            ) : direct ? (
              <Package size={19} />
            ) : (
              <Layers3 size={19} />
            )}
          </div>

          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-bold text-white">
              {title}
            </div>

            <div className="mt-1 text-xs text-slate-400">
              {version}
            </div>
          </div>

          {vulnerable && (
            <span className="h-2 w-2 shrink-0 rounded-full bg-red-400 shadow-[0_0_10px_#ef4444]" />
          )}
        </div>

        <div className="mt-3 flex items-center justify-between">
          <span
            className="rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-wider"
            style={{
              background: `${borderColor}20`,
              color: borderColor,
            }}
          >
            {kind}
          </span>

          {vulnerable && (
            <span className="text-[10px] font-bold text-red-300">
              {findingCount} finding{findingCount === 1 ? "" : "s"}
            </span>
          )}
        </div>

        <Handle
          type="source"
          position={Position.Right}
          style={{
            background: borderColor,
            width: 9,
            height: 9,
            border: "2px solid #0b1220",
          }}
        />
      </div>
    );
  }
);

DependencyNode.displayName = "DependencyNode";

const nodeTypes = {
  dependency: DependencyNode,
};

/* --------------------------------
   MAIN GRAPH
--------------------------------- */

const DependencyGraph: React.FC = () => {
  const { result } = useContext(ScanResultContext);

  const [nodes, setNodes] = useState<Node<CustomNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [search, setSearch] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);

  const graph = result?.graph;

  const findings = useMemo(
    () => Object.values(result?.vulnerabilities ?? {}).flat(),
    [result]
  );

  const vulnerablePackages = useMemo(() => {
    const map = new Map<string, number>();

    findings.forEach((finding) => {
      const name = finding.package_name?.toLowerCase();

      if (name) {
        map.set(name, (map.get(name) ?? 0) + 1);
      }
    });

    return map;
  }, [findings]);

  const selectedFindings = useMemo(() => {
    if (!selectedNode) return [];

    return findings.filter(
      (finding) =>
        finding.package_name?.toLowerCase() ===
        selectedNode.name?.toLowerCase()
    );
  }, [findings, selectedNode]);

  /* --------------------------------
     ELK AUTOMATIC LAYOUT
  --------------------------------- */

  useEffect(() => {
    let cancelled = false;

    const generateGraph = async () => {
      if (!graph || graph.nodes.length === 0) {
        setNodes([]);
        setEdges([]);
        return;
      }

      setLoading(true);

      try {
        const layoutInput = {
          id: "depguard",
          layoutOptions: {
            "elk.algorithm": "layered",
            "elk.direction": "RIGHT",
            "elk.edgeRouting": "ORTHOGONAL",
            "elk.spacing.nodeNode": "65",
            "elk.layered.spacing.nodeNodeBetweenLayers": "145",
            "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
            "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
            "elk.padding": "[top=55,left=55,bottom=55,right=55]",
          },
          children: graph.nodes.map((node) => ({
            id: node.id,
            width: NODE_WIDTH,
            height: NODE_HEIGHT,
          })),
          edges: graph.edges.map((edge, index) => ({
            id: `edge-${index}`,
            sources: [edge.source],
            targets: [edge.target],
          })),
        };

        const layout = await elk.layout(layoutInput);

        if (cancelled) return;

        const positions = new Map(
          (layout.children ?? []).map((node) => [
            node.id,
            {
              x: node.x ?? 0,
              y: node.y ?? 0,
            },
          ])
        );

        const flowNodes: Node<CustomNodeData>[] = graph.nodes.map(
          (node) => {
            const isRoot = node.id === "<root>";

            const name = node.name ?? node.id;

            const findingCount =
              vulnerablePackages.get(name.toLowerCase()) ?? 0;

            const vulnerable = findingCount > 0;

            return {
              id: node.id,
              type: "dependency",
              position: positions.get(node.id) ?? { x: 0, y: 0 },
              draggable: false,
              data: {
                title: isRoot ? "PROJECT ROOT" : name,
                version: isRoot
                  ? "Dependency ecosystem"
                  : `Version ${node.version ?? "Unknown"}`,
                kind: isRoot
                  ? "Application"
                  : node.direct
                    ? "Direct"
                    : "Transitive",
                vulnerable,
                findingCount,
                isRoot,
                direct: Boolean(node.direct),
                dimmed: false,
              },
            };
          }
        );

        const flowEdges: Edge[] = graph.edges.map((edge, index) => {
          const source = graph.nodes.find(
            (node) => node.id === edge.source
          );

          const target = graph.nodes.find(
            (node) => node.id === edge.target
          );

          const sourceVulnerable = vulnerablePackages.has(
            (source?.name ?? "").toLowerCase()
          );

          const targetVulnerable = vulnerablePackages.has(
            (target?.name ?? "").toLowerCase()
          );

          const highlighted = sourceVulnerable || targetVulnerable;

          return {
            id: `edge-${index}`,
            source: edge.source,
            target: edge.target,
            type: "smoothstep",
            animated: highlighted,
            style: {
              stroke: highlighted ? "#fb5252" : "#526985",
              strokeWidth: highlighted ? 2.2 : 1.3,
              opacity: highlighted ? 0.95 : 0.65,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: highlighted ? "#fb5252" : "#526985",
              width: 14,
              height: 14,
            },
          };
        });

        if (!cancelled) {
          setNodes(flowNodes);
          setEdges(flowEdges);
        }
      } catch (error) {
        console.error("Graph layout error:", error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void generateGraph();

    return () => {
      cancelled = true;
    };
  }, [graph, vulnerablePackages]);

  /* --------------------------------
     SEARCH HIGHLIGHT
  --------------------------------- */

  const displayedNodes = useMemo(() => {
    const query = search.trim().toLowerCase();

    return nodes.map((node) => {
      const matches =
        !query ||
        node.data.title.toLowerCase().includes(query) ||
        node.id.toLowerCase().includes(query);

      return {
        ...node,
        data: {
          ...node.data,
          dimmed: !matches,
        },
      };
    });
  }, [nodes, search]);

  if (!result) {
    return (
      <EmptyState
        title="No dependency graph"
        description="Run a dependency scan to generate your package network."
      />
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <EmptyState
        title="Graph data unavailable"
        description="The latest scan did not return dependency graph data."
      />
    );
  }

  const directCount = graph.nodes.filter(
    (node) => node.direct && node.id !== "<root>"
  ).length;

  const transitiveCount = graph.nodes.filter(
    (node) => !node.direct && node.id !== "<root>"
  ).length;

  return (
    <div className="space-y-6">

      {/* HEADER */}

      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-2">
              <GitBranch className="text-cyan-400" size={24} />
            </div>

            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white">
                Dependency Network
              </h1>

              <p className="mt-1 text-sm text-slate-400">
                Visualize your software supply chain.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-2">
          <Activity size={15} className="text-emerald-400" />
          <span className="text-xs font-semibold text-emerald-300">
            Scan visualization ready
          </span>
        </div>
      </div>

      {/* STATISTICS */}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">

        <StatCard
          label="Total packages"
          value={graph.nodes.length - 1}
          icon={<Package size={19} />}
          color="cyan"
        />

        <StatCard
          label="Direct dependencies"
          value={directCount}
          icon={<GitBranch size={19} />}
          color="blue"
        />

        <StatCard
          label="Transitive dependencies"
          value={transitiveCount}
          icon={<Layers3 size={19} />}
          color="purple"
        />

        <StatCard
          label="Vulnerable packages"
          value={vulnerablePackages.size}
          icon={<ShieldAlert size={19} />}
          color="red"
        />

      </div>

      {/* GRAPH TOOLBAR */}

      <div className="flex flex-col justify-between gap-3 rounded-xl border border-slate-700/70 bg-[#111c2e] p-4 md:flex-row md:items-center">

        <div>
          <h2 className="font-semibold text-white">
            Package relationship map
          </h2>

          <p className="mt-1 text-xs text-slate-400">
            Follow the connections from left to right. Select a node for details.
          </p>
        </div>

        <div className="relative w-full md:max-w-xs">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />

          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Find a package..."
            className="w-full rounded-lg border border-slate-700 bg-[#0b1423] py-2.5 pl-9 pr-3 text-sm text-white outline-none transition focus:border-cyan-500"
          />
        </div>

      </div>

      {/* LEGEND */}

      <div className="flex flex-wrap gap-x-6 gap-y-3 text-xs text-slate-300">

        <Legend color="#22d3ee" label="Project root" />
        <Legend color="#60a5fa" label="Direct dependency" />
        <Legend color="#64748b" label="Transitive dependency" />
        <Legend color="#fb5252" label="Vulnerable package" />

      </div>

      {/* GRAPH CANVAS */}

      <div
        className="relative overflow-hidden rounded-2xl border border-slate-700/80"
        style={{
          height: 740,
          background:
            "radial-gradient(ellipse at 50% 50%, #17263a 0%, #0b1423 75%)",
        }}
      >

        <div className="pointer-events-none absolute inset-0 opacity-20">
          <div
            className="h-full w-full"
            style={{
              backgroundImage:
                "linear-gradient(rgba(100,116,139,0.12) 1px, transparent 1px), linear-gradient(90deg, rgba(100,116,139,0.12) 1px, transparent 1px)",
              backgroundSize: "38px 38px",
            }}
          />
        </div>

        {loading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#0b1423]/80 backdrop-blur-sm">
            <div className="text-center">
              <div className="mx-auto mb-3 h-9 w-9 animate-spin rounded-full border-2 border-slate-600 border-t-cyan-400" />
              <p className="text-sm text-slate-300">
                Building dependency network...
              </p>
            </div>
          </div>
        )}

        <ReactFlow
          nodes={displayedNodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{
            padding: 0.18,
            maxZoom: 0.9,
          }}
          minZoom={0.04}
          maxZoom={1.5}
          onNodeClick={(_, node) => {
            const original = graph.nodes.find(
              (item) => item.id === node.id
            );

            setSelectedNode(original ?? null);
          }}
          onPaneClick={() => setSelectedNode(null)}
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            color="#526985"
            gap={25}
            size={1}
          />

          <Controls
            className="!overflow-hidden !rounded-xl !border !border-slate-600 !bg-[#17263a] [&>button]:!border-slate-600 [&>button]:!bg-[#17263a] [&>button]:!fill-white"
          />

          <MiniMap
            pannable
            zoomable
            maskColor="rgba(5, 10, 20, 0.75)"
            nodeColor={(node) => {
              const original = graph.nodes.find(
                (item) => item.id === node.id
              );

              if (node.id === "<root>") return "#22d3ee";

              if (
                vulnerablePackages.has(
                  (original?.name ?? "").toLowerCase()
                )
              ) {
                return "#fb5252";
              }

              return original?.direct ? "#60a5fa" : "#475569";
            }}
            className="!border !border-slate-600 !bg-[#101b2b]"
          />
        </ReactFlow>

      </div>

      {/* SELECTED PACKAGE DETAILS */}

      {selectedNode && (
        <div className="overflow-hidden rounded-2xl border border-cyan-500/20 bg-[#111c2e]">

          <div className="flex items-center justify-between border-b border-slate-700/70 p-5">

            <div>
              <div className="flex items-center gap-2">
                <Package size={19} className="text-cyan-400" />

                <h2 className="text-lg font-bold text-white">
                  {selectedNode.name ?? selectedNode.id}
                </h2>
              </div>

              <p className="mt-1 text-xs text-slate-400">
                Package inspection
              </p>
            </div>

            <button
              onClick={() => setSelectedNode(null)}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-700 hover:text-white"
              aria-label="Close package details"
            >
              <X size={18} />
            </button>

          </div>

          <div className="grid gap-4 p-5 sm:grid-cols-3">

            <Detail
              label="Installed version"
              value={selectedNode.version ?? "Unknown"}
            />

            <Detail
              label="Dependency type"
              value={
                selectedNode.id === "<root>"
                  ? "Project root"
                  : selectedNode.direct
                    ? "Direct dependency"
                    : "Transitive dependency"
              }
            />

            <Detail
              label="Dependency depth"
              value={String(selectedNode.depth ?? "Unknown")}
            />

          </div>

          {selectedFindings.length > 0 && (
            <div className="border-t border-slate-700/70 p-5">

              <h3 className="mb-4 flex items-center gap-2 font-semibold text-red-300">
                <ShieldAlert size={18} />
                Security findings ({selectedFindings.length})
              </h3>

              <div className="space-y-3">

                {selectedFindings.map((finding) => (
                  <div
                    key={finding.id}
                    className="rounded-xl border border-red-500/20 bg-red-500/5 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-white">
                        {finding.id}
                      </span>

                      <span className="rounded-full bg-red-500/15 px-3 py-1 text-xs font-bold text-red-300">
                        {finding.risk_level ?? "Unknown"}
                      </span>
                    </div>

                    <p className="mt-2 text-sm text-slate-300">
                      {finding.summary}
                    </p>

                    <p className="mt-3 text-xs text-slate-400">
                      CVSS: {finding.cvss_score ?? "Unavailable"}
                      {" · "}
                      Risk score: {finding.risk_score ?? "Unknown"}
                    </p>
                  </div>
                ))}

              </div>
            </div>
          )}

          {selectedFindings.length === 0 && (
            <div className="border-t border-slate-700/70 p-5 text-sm text-emerald-300">
              <ShieldCheck className="mr-2 inline" size={16} />
              No vulnerability findings associated with this package.
            </div>
          )}

        </div>
      )}

      <p className="text-center text-xs text-slate-500">
        Dependency relationships are derived from the uploaded package-lock.json.
        Vulnerability highlights are based on the latest scan findings.
      </p>

    </div>
  );
};

/* --------------------------------
   SMALL REUSABLE COMPONENTS
--------------------------------- */

const StatCard = ({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}) => {
  const colors: Record<string, string> = {
    cyan: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
    blue: "text-blue-400 bg-blue-400/10 border-blue-400/20",
    purple: "text-purple-400 bg-purple-400/10 border-purple-400/20",
    red: "text-red-400 bg-red-400/10 border-red-400/20",
  };

  return (
    <div className="rounded-xl border border-slate-700/70 bg-[#111c2e] p-4 transition duration-300 hover:-translate-y-1 hover:border-slate-500">
      <div
        className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg border ${colors[color]}`}
      >
        {icon}
      </div>

      <p className="text-2xl font-bold text-white">{value}</p>

      <p className="mt-1 text-xs text-slate-400">{label}</p>
    </div>
  );
};

const Legend = ({
  color,
  label,
}: {
  color: string;
  label: string;
}) => (
  <div className="flex items-center gap-2">
    <span
      className="h-3 w-3 rounded-full"
      style={{
        background: color,
        boxShadow: `0 0 9px ${color}88`,
      }}
    />
    {label}
  </div>
);

const Detail = ({
  label,
  value,
}: {
  label: string;
  value: string;
}) => (
  <div className="rounded-xl border border-slate-700/70 bg-[#0b1423] p-4">
    <p className="text-xs text-slate-400">{label}</p>
    <p className="mt-2 break-words text-sm font-semibold text-white">
      {value}
    </p>
  </div>
);

export default DependencyGraph;

