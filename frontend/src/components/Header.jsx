import React from 'react';

export default function Header({ stats, onShowSplash }) {
  return (
    <header>
      <div className="header-left">
        <div className="brand-icon">
          <svg viewBox="0 0 24 24">
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
        </div>
        <div className="brand-title">
          <h1>FraudGraph Agent</h1>
          <span>TigerGraph Knowledge Graph &middot; Deterministic Policy</span>
        </div>
      </div>
      <div className="stats" id="stats">
        <div className="telemetry-item" title="Transactions in Knowledge Graph">
          <svg viewBox="0 0 24 24">
            <rect x="2" y="5" width="20" height="14" rx="2" />
            <line x1="2" y1="10" x2="22" y2="10" />
          </svg>
          <span>Txns</span>
          <b>{(stats?.transactions || 0).toLocaleString()}</b>
        </div>
        <div className="telemetry-item" title="Card Entities">
          <svg viewBox="0 0 24 24">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
            <line x1="2" y1="10" x2="22" y2="10" />
          </svg>
          <span>Cards</span>
          <b>{(stats?.cards || 0).toLocaleString()}</b>
        </div>
        <div className="telemetry-item" title="Historical Closed Cases">
          <svg viewBox="0 0 24 24">
            <polyline points="9 11 12 14 22 4" />
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
          </svg>
          <span>Closed</span>
          <b>{(stats?.closed_cases || 0).toLocaleString()}</b>
        </div>
        <div className="telemetry-item" title="Agent Memory Precedents">
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span>Memory</span>
          <b>{stats?.agent_cases || 0}</b>
        </div>
        <div className="telemetry-item" title="Average Latency">
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <span>Latency</span>
          <b>{stats?.avg_latency || 0}s</b>
        </div>
        {onShowSplash && (
          <button className="telemetry-item splash-trigger-btn" onClick={onShowSplash} title="Replay Hacker House Goa Intro">
            <svg viewBox="0 0 24 24">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span>GOA INTRO</span>
          </button>
        )}
      </div>
    </header>
  );
}
