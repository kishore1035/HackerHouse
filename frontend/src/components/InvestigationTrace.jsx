import React from 'react';

export default function InvestigationTrace({ trace, statusText }) {
  const steps = trace || [];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg viewBox="0 0 24 24">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          Investigation Trace
        </span>
        <span className="card-subtitle" id="live">
          {statusText ? statusText : `${steps.length} STEPS`}
        </span>
      </div>
      <div className="timeline" id="tl">
        {steps.map((s, idx) => {
          const detail = typeof s.output === 'object' ? JSON.stringify(s.output) : String(s.output || s.input || '');
          const latency = s.latency_ms ? `${s.latency_ms}ms` : '';
          return (
            <div key={idx} className="timeline-step">
              <span className="step-badge">{idx + 1}</span>
              {latency && <span className="step-time">{latency}</span>}
              <span className="step-title">{s.action || 'Query execution'}</span>
              <p className="step-detail">{detail}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
