import React from 'react';

export default function CaseMemory({ similarPriorCases }) {
  const cases = similarPriorCases || [];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg viewBox="0 0 24 24">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
            <line x1="6" y1="6" x2="6.01" y2="6" />
            <line x1="6" y1="18" x2="6.01" y2="18" />
          </svg>
          Case Memory Retrieval
        </span>
        <span className="card-subtitle">VECTOR MATCH</span>
      </div>
      {cases.length > 0 ? (
        cases.map((id, idx) => (
          <div key={idx} className="memory-row">
            <span className="memory-cid">{id}</span>
            <span style={{ color: 'var(--text-tertiary)' }}>
              Closed historical case &middot; cosine vector similarity
            </span>
          </div>
        ))
      ) : (
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
          No prior precedent cases matched.
        </p>
      )}
    </div>
  );
}
