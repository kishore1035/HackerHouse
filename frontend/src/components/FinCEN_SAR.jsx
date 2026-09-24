import React from 'react';

function money(n) {
  return '$' + Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function FinCEN_SAR({ sar, onCopySar }) {
  if (!sar) return null;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          Suspicious Activity Report (FinCEN SAR)
        </span>
        <span className="card-subtitle">{sar.file ? 'REQUIRES L2 APPROVAL' : 'EXEMPT'}</span>
      </div>
      {sar.file ? (
        <>
          <div className="sar-box">
            <button className="sar-copy-btn" onClick={() => onCopySar(sar.narrative)}>
              <svg viewBox="0 0 24 24">
                <rect x="9" y="9" width="13" height="13" rx="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy SAR
            </button>
            <pre className="sar-text">{sar.narrative}</pre>
          </div>
          <div style={{ color: 'var(--text-tertiary)', fontSize: '12px', fontFamily: 'var(--font-mono)', marginTop: '6px' }}>
            SUBJECTS: {(sar.subjects || []).join(', ')} &middot; TOTAL: {money(sar.total_amount_usd)} &middot; DATES: {(sar.activity_dates || []).join(' → ')}
          </div>
        </>
      ) : (
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{sar.reason}</p>
      )}
    </div>
  );
}
