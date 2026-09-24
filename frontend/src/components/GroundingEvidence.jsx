import React from 'react';

export default function GroundingEvidence({ evidence }) {
  const items = evidence || [];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg viewBox="0 0 24 24">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          Grounding Evidence
        </span>
        <span className="card-subtitle">{items.length} FACTS</span>
      </div>
      {items.map((e, idx) => (
        <div key={idx} className="evidence-row">
          <span className="source-badge">{e.source}</span>
          <div>
            <div className="evidence-claim">{e.claim}</div>
            <div className="evidence-ref">{e.ref}</div>
            {e.entity_ids && e.entity_ids.length > 0 && (
              <div className="evidence-tags">
                {e.entity_ids.slice(0, 10).map((id, i) => (
                  <span key={i} className="evidence-tag">
                    {id}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
