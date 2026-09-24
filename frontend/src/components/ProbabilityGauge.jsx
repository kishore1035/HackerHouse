import React from 'react';

export default function ProbabilityGauge({ probability }) {
  const p = probability != null ? probability : 0;
  const leftPct = Math.max(1, Math.min(99, p * 100));

  const ticks = [
    { left: 15, text: '0.15' },
    { left: 30, text: '0.30' },
    { left: 70, text: '0.70' },
    { left: 85, text: '0.85' },
  ];

  return (
    <div className="gauge-container">
      <div className="gauge-track">
        <div className="gauge-pointer" style={{ left: `${leftPct}%` }}>
          <span className="gauge-badge">{p.toFixed(2)}</span>
        </div>
      </div>
      <div className="gauge-markers">
        {ticks.map((t) => (
          <span key={t.text} className="gauge-marker" style={{ left: `${t.left}%` }}>
            {t.text}
          </span>
        ))}
      </div>
      <div className="gauge-regions">
        <span>[&le; 0.15 CLEAR]</span>
        <span>[0.15 &ndash; 0.85 INVESTIGATE]</span>
        <span>[&ge; 0.85 FRAUD]</span>
      </div>
    </div>
  );
}
