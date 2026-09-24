import React from 'react';

function pretty(s) {
  return String(s || '').replaceAll('_', ' ');
}

function money(n) {
  if (n == null) return '';
  return '$' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function CaseItem({ item, isSelected, onSelect }) {
  const isFraud = item.verdict === 'fraud';
  const isLegit = item.verdict === 'legitimate';
  const verdictLabel = isFraud ? 'FRAUD' : isLegit ? 'LEGIT' : 'REVIEW';

  return (
    <div
      className={`case-card ${isSelected ? 'active' : ''}`}
      onClick={() => onSelect(item.case_id)}
      role="option"
      aria-selected={isSelected}
      tabIndex={0}
      data-id={item.case_id}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(item.case_id);
        }
      }}
    >
      <div className="case-card-header">
        <div className="case-card-id-wrap">
          <span className={`case-status-indicator ${item.verdict || 'uncertain'}`} />
          <span className="case-card-id">{item.case_id}</span>
        </div>
        <div className="case-card-badges">
          {item.exposure != null && item.exposure > 0 && (
            <span className="case-exposure-badge">{money(item.exposure)}</span>
          )}
          <span className={`case-prob-pill ${item.verdict || 'uncertain'}`}>
            {item.probability != null ? `${(item.probability * 100).toFixed(0)}%` : 'N/A'} {verdictLabel}
          </span>
        </div>
      </div>

      <div className="case-card-meta">
        <span className="case-trigger-label">{pretty(item.trigger_type)}</span>
        <span className="case-card-num">{item.card_id}</span>
      </div>

      {item.pattern && item.pattern !== 'none' && (
        <div className="case-card-footer">
          <span className="case-pattern-tag">{pretty(item.pattern)}</span>
        </div>
      )}
    </div>
  );
}
