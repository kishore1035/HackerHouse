import React from 'react';

function ActionColumn({ title, items }) {
  return (
    <div className="action-column">
      <h4>{title}</h4>
      {!items || items.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)', padding: '4px 0' }}>
          NONE SPECIFIED
        </div>
      ) : (
        items.map((x, i) => (
          <div key={i} className="action-item">
            <div className="action-item-header">
              <b>{x.action}</b>
              <span className={`chip route-${x.route}`}>
                {x.route === 'auto' ? 'AUTONOMOUS' : x.route === 'L1' ? 'L1 LEAD' : 'L2 MANAGER'}
              </span>
            </div>
            <p>{x.reason}</p>
          </div>
        ))
      )}
    </div>
  );
}

export default function ActionRecommendations({ actions, policyDecision }) {
  const autoList = (actions || []).filter((x) => x.route === 'auto');
  const manualList = (actions || []).filter((x) => x.route !== 'auto');

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg viewBox="0 0 24 24">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          Policy-Governed Next Best Actions
        </span>
        <span className="card-subtitle">
          {autoList.length} AUTONOMOUS &middot; {manualList.length} ESCALATED
        </span>
      </div>
      <div className="action-grid">
        <ActionColumn title="Immediate Autonomous Actions" items={autoList} />
        <ActionColumn title="Escalation &amp; Review (L1 / L2)" items={manualList} />
      </div>
      {policyDecision && (
        <div className="callout">
          <b>Governance Routing:</b> {policyDecision}
        </div>
      )}
    </div>
  );
}
