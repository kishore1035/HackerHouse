import React from 'react';

export default function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-header-row">
        <svg viewBox="0 0 24 24">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
        <h2>Select an Alert to Investigate</h2>
      </div>
      <p>
        Autonomous graph traversal across 590k+ transactions. Calibrated on historical closed cases with deterministic policy rule enforcement.
      </p>
    </div>
  );
}
