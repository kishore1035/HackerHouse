import React, { useRef } from 'react';
import CaseItem from './CaseItem';

export default function Sidebar({
  cases,
  selectedId,
  onSelectCase,
  currentFilter,
  onSetFilter,
  searchQuery,
  onSearchChange,
  onClearSearch,
  filterCounts,
}) {
  const searchInputRef = useRef(null);

  return (
    <aside>
      <div className="sidebar-header">
        <div className="sidebar-title-row">
          <h2>Alert Queue</h2>
          <span className="queue-badge" id="queue-count">
            {cases.length}
          </span>
        </div>

        <div className="search-container">
          <svg className="search-icon" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={searchInputRef}
            type="text"
            id="search"
            placeholder="Filter alerts (ID, card, type)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
          <div className="search-actions">
            {searchQuery && (
              <button
                className="search-clear-btn"
                id="search-clear"
                onClick={() => {
                  onClearSearch();
                  searchInputRef.current?.focus();
                }}
                title="Clear"
              >
                <svg viewBox="0 0 24 24">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="18" x2="18" y2="6" />
                </svg>
              </button>
            )}
            <span className="search-shortcut">/</span>
          </div>
        </div>

        <div className="segmented-control" role="tablist">
          <button
            className={`segment-btn ${currentFilter === 'all' ? 'active' : ''}`}
            onClick={() => onSetFilter('all')}
          >
            <svg viewBox="0 0 24 24">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            All <span className="count-badge">{filterCounts.all}</span>
          </button>
          <button
            className={`segment-btn ${currentFilter === 'fraud' ? 'active' : ''}`}
            onClick={() => onSetFilter('fraud')}
          >
            <svg viewBox="0 0 24 24">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            Fraud <span className="count-badge">{filterCounts.fraud}</span>
          </button>
          <button
            className={`segment-btn ${currentFilter === 'uncertain' ? 'active' : ''}`}
            onClick={() => onSetFilter('uncertain')}
          >
            <svg viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 14 14" />
            </svg>
            Review <span className="count-badge">{filterCounts.uncertain}</span>
          </button>
          <button
            className={`segment-btn ${currentFilter === 'legitimate' ? 'active' : ''}`}
            onClick={() => onSetFilter('legitimate')}
          >
            <svg viewBox="0 0 24 24">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            Legit <span className="count-badge">{filterCounts.legitimate}</span>
          </button>
        </div>
      </div>

      <div className="case-list" id="list" role="listbox">
        {cases.length === 0 ? (
          <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            NO ALERTS MATCH CRITERIA
          </div>
        ) : (
          cases.map((c) => (
            <CaseItem
              key={c.case_id}
              item={c}
              isSelected={selectedId === c.case_id}
              onSelect={onSelectCase}
            />
          ))
        )}
      </div>
    </aside>
  );
}
