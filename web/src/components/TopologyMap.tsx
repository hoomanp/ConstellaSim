import type { Topology } from "../api/client";

type Props = { topology: Topology | null };

export function TopologyMap({ topology }: Props) {
  if (!topology) {
    return (
      <svg className="topo-svg" viewBox="0 0 640 220" role="img" aria-label="Awaiting topology">
        <text x="320" y="112" textAnchor="middle" fill="#8b9bb4" fontSize="14" fontFamily="IBM Plex Mono, monospace">
          Run a diagnostic to illuminate the route
        </text>
      </svg>
    );
  }

  const W = 640;
  const H = 220;
  const sats = topology.nodes.filter((n) => n.type === "satellite").map((n) => n.id).sort();
  const grounds = topology.nodes.filter((n) => n.type === "ground").map((n) => n.id);
  const ordered = [grounds[0], ...sats, grounds[1]].filter(Boolean);
  const positions: Record<string, { x: number; y: number }> = {};
  ordered.forEach((id, i) => {
    positions[id] = {
      x: Math.round(48 + (i / Math.max(ordered.length - 1, 1)) * (W - 96)),
      y: H / 2,
    };
  });

  const routeEdges = new Set<string>();
  for (let i = 0; i < topology.route.length - 1; i++) {
    routeEdges.add(`${topology.route[i]}|${topology.route[i + 1]}`);
    routeEdges.add(`${topology.route[i + 1]}|${topology.route[i]}`);
  }

  return (
    <svg className="topo-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Live packet route">
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {topology.edges.map((e) => {
        const a = positions[e.source];
        const b = positions[e.target];
        if (!a || !b) return null;
        const onRoute = routeEdges.has(`${e.source}|${e.target}`) && !topology.dropped;
        return (
          <g key={`${e.source}-${e.target}`}>
            <line
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={onRoute ? "#3ee0c5" : "#2a3a52"}
              strokeWidth={onRoute ? 3 : 1.5}
              strokeDasharray={onRoute ? "7 5" : undefined}
              filter={onRoute ? "url(#glow)" : undefined}
            >
              {onRoute && (
                <animate attributeName="stroke-dashoffset" from="0" to="-24" dur="0.7s" repeatCount="indefinite" />
              )}
            </line>
            <text
              x={(a.x + b.x) / 2}
              y={(a.y + b.y) / 2 - 10}
              textAnchor="middle"
              fill={onRoute ? "#9ef5e4" : "#5b6b84"}
              fontSize="11"
              fontFamily="IBM Plex Mono, monospace"
            >
              {e.weight}ms
            </text>
          </g>
        );
      })}

      {topology.nodes.map((n) => {
        const p = positions[n.id];
        if (!p) return null;
        const onRoute = topology.route.includes(n.id) && !topology.dropped;
        if (n.type === "satellite") {
          return (
            <g key={n.id}>
              <circle
                cx={p.x}
                cy={p.y}
                r={onRoute ? 12 : 8}
                fill={onRoute ? "#0d3d36" : "#0c182a"}
                stroke={onRoute ? "#3ee0c5" : "#4a5d78"}
                strokeWidth="2"
                filter={onRoute ? "url(#glow)" : undefined}
              />
              <text x={p.x} y={p.y + 28} textAnchor="middle" fill="#8b9bb4" fontSize="11">
                {n.id}
              </text>
            </g>
          );
        }
        const sz = onRoute ? 13 : 10;
        const pts = `${p.x},${p.y - sz} ${p.x + sz},${p.y + sz * 0.65} ${p.x - sz},${p.y + sz * 0.65}`;
        return (
          <g key={n.id}>
            <polygon
              points={pts}
              fill={topology.dropped ? "#3a1515" : onRoute ? "#123528" : "#0c182a"}
              stroke={topology.dropped ? "#ff6b6b" : onRoute ? "#4ade80" : "#4a5d78"}
              strokeWidth="2"
            />
            <text x={p.x} y={p.y + 30} textAnchor="middle" fill="#8b9bb4" fontSize="11">
              {n.id.length > 12 ? `${n.id.slice(0, 11)}…` : n.id}
            </text>
          </g>
        );
      })}

      {topology.dropped && (
        <text x={W / 2} y={28} textAnchor="middle" fill="#ff6b6b" fontSize="14" fontFamily="IBM Plex Mono, monospace">
          ⚠ Packet dropped
        </text>
      )}
    </svg>
  );
}
