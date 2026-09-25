import React from 'react';

export default function SubgraphTopology({ caseDetail }) {
  if (!caseDetail) return null;
  const c = caseDetail.case || {};
  const W = 620, H = 220;
  const cx = W / 2, cy = H / 2 - 6;

  const nodes = [];
  const edges = [];

  const add = (id, label, x, y, type, r) => nodes.push({ id, label, x, y, type, r });

  add('card', c.card_id || 'CARD', cx, cy, 'card', 14);

  const tx = [c.flagged_txn_id, ...(c.connected_txn_ids || [])].filter(Boolean).slice(0, 5);
  tx.forEach((t, i) => {
    const ang = -Math.PI / 2 + (i - (tx.length - 1) / 2) * 0.55;
    const x = cx + Math.cos(ang) * 135;
    const y = cy + Math.sin(ang) * 115;
    add('t' + t, 'TX ' + t, x, y, 'txn', 7);
    edges.push(['card', 't' + t, 'MADE']);
  });

  const dev = (c.connected_device_profiles || [])[0];
  if (dev) {
    add('dev', 'Device', cx - 210, cy + 10, 'dev', 11);
    tx.slice(0, 3).forEach((t) => edges.push(['t' + t, 'dev', 'FROM_DEVICE']));
  }

  const cc = (c.connected_card_ids || []).slice(0, 5);
  cc.forEach((k, i) => {
    const y = 45 + (i * (H - 90)) / Math.max(cc.length - 1, 1);
    add('c' + k, k, 60, cc.length === 1 ? cy + 50 : y, 'shared', 8);
    edges.push([dev ? 'dev' : 'card', 'c' + k, 'SHARES']);
  });

  const sm = (c.similar_prior_cases || []).slice(0, 5);
  sm.forEach((k, i) => {
    const y = 45 + (i * (H - 90)) / Math.max(sm.length - 1, 1);
    add('s' + k, k, W - 60, y, 'precedent', 8);
    edges.push(['card', 's' + k, 'SIMILAR']);
  });

  const P = Object.fromEntries(nodes.map((n) => [n.id, n]));

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg viewBox="0 0 24 24">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
          Subgraph Topology
        </span>
        <span className="card-subtitle">{c.graph_case_id}</span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{
          background: '#FFFDF5',
          borderRadius: 'var(--radius-sm)',
          border: '2.5px solid #000000',
          boxShadow: 'var(--shadow-brutal-xs)',
        }}
      >
        {edges
          .filter((e) => P[e[0]] && P[e[1]])
          .map(([u, v, l], i) => (
            <line
              key={i}
              x1={P[u].x}
              y1={P[u].y}
              x2={P[v].x}
              y2={P[v].y}
              stroke="#000000"
              strokeWidth="1.6"
              strokeDasharray={l === 'SIMILAR' ? '4 3' : l === 'SHARES' ? '3 3' : undefined}
            />
          ))}

        {nodes.map((n) => {
          if (n.type === 'card') {
            return (
              <g key={n.id}>
                <circle cx={n.x} cy={n.y} r={n.r} fill="#FFE600" stroke="#000000" strokeWidth="2.5" />
                <text
                  x={n.x}
                  y={n.y + n.r + 13}
                  textAnchor="middle"
                  fill="#000000"
                  fontFamily="var(--font-mono)"
                  fontSize="10"
                  fontWeight="800"
                >
                  {n.label}
                </text>
              </g>
            );
          }
          if (n.type === 'txn') {
            return (
              <g key={n.id}>
                <circle cx={n.x} cy={n.y} r={n.r} fill="#FF7675" stroke="#000000" strokeWidth="2" />
                <text
                  x={n.x}
                  y={n.y + n.r + 12}
                  textAnchor="middle"
                  fill="#000000"
                  fontFamily="var(--font-mono)"
                  fontSize="9.5"
                  fontWeight="700"
                >
                  {n.label}
                </text>
              </g>
            );
          }
          if (n.type === 'dev') {
            return (
              <g key={n.id}>
                <rect x={n.x - 10} y={n.y - 10} width="20" height="20" rx="3" fill="#55EFC4" stroke="#000000" strokeWidth="2" />
                <text
                  x={n.x}
                  y={n.y + 20}
                  textAnchor="middle"
                  fill="#000000"
                  fontFamily="var(--font-mono)"
                  fontSize="9.5"
                  fontWeight="700"
                >
                  {n.label}
                </text>
              </g>
            );
          }
          return (
            <g key={n.id}>
              <circle cx={n.x} cy={n.y} r={n.r} fill="#A29BFE" stroke="#000000" strokeWidth="1.8" />
              <text
                x={n.x}
                y={n.y + n.r + 11}
                textAnchor="middle"
                fill="#1a1a1a"
                fontFamily="var(--font-mono)"
                fontSize="9"
                fontWeight="600"
              >
                {n.label}
              </text>
            </g>
          );
        })}

        <g fontSize="9.5" fontFamily="var(--font-mono)" fontWeight="700">
          <circle cx="20" cy={H - 14} r="4" fill="#FFE600" stroke="#000000" strokeWidth="1.5" />
          <text fill="#000000" x="30" y={H - 11}>
            CARD
          </text>
          <circle cx="85" cy={H - 14} r="4" fill="#FF7675" stroke="#000000" strokeWidth="1.5" />
          <text fill="#000000" x="96" y={H - 11}>
            FLAGGED TXN
          </text>
          <rect x="200" y={H - 18} width="8" height="8" rx="2" fill="#55EFC4" stroke="#000000" strokeWidth="1.5" />
          <text fill="#000000" x="214" y={H - 11}>
            DEVICE
          </text>
          <circle cx="280" cy={H - 14} r="4" fill="#A29BFE" stroke="#000000" strokeWidth="1.5" />
          <text fill="#000000" x="291" y={H - 11}>
            PRECEDENT / SHARED
          </text>
        </g>
      </svg>
    </div>
  );
}
