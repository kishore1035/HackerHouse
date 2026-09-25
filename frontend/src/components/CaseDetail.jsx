import React from 'react';
import ProbabilityGauge from './ProbabilityGauge';
import ActionRecommendations from './ActionRecommendations';
import FinCEN_SAR from './FinCEN_SAR';
import InvestigationTrace from './InvestigationTrace';
import SubgraphTopology from './SubgraphTopology';
import GroundingEvidence from './GroundingEvidence';
import CaseMemory from './CaseMemory';

function pretty(s) {
  return String(s || '').replaceAll('_', ' ');
}

function money(n) {
  return '$' + Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function CaseDetail({
  caseMeta,
  caseDetail,
  isInvestigating,
  investigationStatus,
  onRunInvestigation,
  onCopyJson,
  onCopySar,
}) {
  const c = caseDetail?.case;
  const a = caseDetail;

  return (
    <div>
      {/* Case Detail Top Bar */}
      <div className="case-top-bar">
        <div className="case-info">
          <div className="case-title-row">
            <span className="case-cid">{caseMeta.case_id}</span>
            {c && (
              <div className="case-chips">
                <span className={`chip ${c.verdict}`}>{c.verdict}</span>
                <span className="chip">{pretty(c.status)}</span>
                {c.pattern && c.pattern !== 'none' && <span className="chip">{pretty(c.pattern)}</span>}
              </div>
            )}
          </div>
          <div className="trigger-text">{caseMeta.trigger_text}</div>
          <div className="case-meta-line">
            <span>
              TRIGGER: <b>{pretty(caseMeta.trigger_type).toUpperCase()}</b>
            </span>
            <span className="sep">&middot;</span>
            <span>
              OPENED: <b>{caseMeta.opened_at}</b>
            </span>
            <span className="sep">&middot;</span>
            <span>
              FLAGGED TXN: <b>{caseMeta.flagged_txn_id}</b>
            </span>
            <span className="sep">&middot;</span>
            <span>
              CARD: <b>{caseMeta.card_id}</b>
            </span>
            {caseMeta.risk_score != null && (
              <>
                <span className="sep">&middot;</span>
                <span>
                  BANK RISK: <b>{caseMeta.risk_score}</b>
                </span>
              </>
            )}
          </div>
        </div>
        <div className="case-actions">
          {a && (
            <button className="btn ghost" onClick={() => onCopyJson(a)} title="Copy Case Payload">
              <svg viewBox="0 0 24 24">
                <rect x="9" y="9" width="13" height="13" rx="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy JSON
            </button>
          )}
          <button className="btn" disabled={isInvestigating} onClick={onRunInvestigation}>
            {isInvestigating ? (
              <>
                <svg viewBox="0 0 24 24" style={{ animation: 'spin 0.8s linear infinite' }}>
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="3"
                    fill="none"
                    strokeDasharray="16 16"
                  />
                </svg>
                Investigating...
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                {a ? 'Re-run Investigation' : 'Execute Investigation'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* User-friendly guidance banner */}
      {c ? (
        <div className="callout guide-callout">
          <b>Live Investigation Summary:</b>
          <span> This card was evaluated across 860,000+ TigerGraph transactions. The agent verified {(c.evidence || []).length} graph facts and matched {(c.similar_prior_cases || []).length} closed historical fraud rings to reach a calibrated <b>{c.verdict?.toUpperCase()}</b> verdict.</span>
        </div>
      ) : (
        <div className="callout guide-callout pending">
          <b>Ready to Investigate:</b>
          <span> Click the <b>"Execute Investigation"</b> button above. The agent will traverse connected cards, shared stolen devices, and historical precedents to calculate risk in real-time.</span>
        </div>
      )}

      {/* If investigated, show KPI summary row */}
      {c && (
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-label">Calibrated Probability</span>
              <span className="kpi-icon">
                <svg viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
              </span>
            </div>
            <div className="kpi-val">
              {c.fraud_probability != null ? `${(c.fraud_probability * 100).toFixed(1)}%` : 'N/A'}
            </div>
            <span className="kpi-hint">0% = Safe · 100% = Definite Fraud</span>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-label">Financial Exposure</span>
              <span className="kpi-icon">
                <svg viewBox="0 0 24 24">
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
              </span>
            </div>
            <div className="kpi-val">{money(c.exposure_usd)}</div>
            <span className="kpi-hint">Total USD at risk on card</span>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-label">Pattern Signature</span>
              <span className="kpi-icon">
                <svg viewBox="0 0 24 24">
                  <polygon points="12 2 2 7 12 12 22 7 12 2" />
                  <polyline points="2 17 12 22 22 17" />
                  <polyline points="2 12 12 17 22 12" />
                </svg>
              </span>
            </div>
            <div className="kpi-val" style={{ fontSize: '13px', textTransform: 'uppercase' }}>
              {pretty(c.pattern || 'None')}
            </div>
            <span className="kpi-hint">Detected fraud ring structure</span>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-label">Graph Evidence</span>
              <span className="kpi-icon">
                <svg viewBox="0 0 24 24">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
              </span>
            </div>
            <div className="kpi-val">{(c.evidence || []).length} Facts</div>
            <span className="kpi-hint">Zero-hallucination graph facts</span>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-label">Precedents Matched</span>
              <span className="kpi-icon">
                <svg viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </span>
            </div>
            <div className="kpi-val">{(c.similar_prior_cases || []).length} Cases</div>
            <span className="kpi-hint">Historical cases with same traits</span>
          </div>
        </div>
      )}

      {/* If not investigated yet or streaming, show trace box */}
      {!a && (
        <InvestigationTrace
          trace={a?.trace || []}
          statusText={investigationStatus || 'INITIALIZED'}
        />
      )}

      {/* Full Detail Grid if investigated */}
      {a && (
        <div className="detail-grid">
          <div>
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <svg viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  Calibrated Decision Engine
                </span>
                <span className="card-subtitle">{c?.verdict?.toUpperCase()}</span>
              </div>
              <ProbabilityGauge probability={c?.fraud_probability} />
              <div className="callout">
                <b>Deterministic Rule Assessment:</b> {c?.policy_decision}
              </div>
            </div>

            <ActionRecommendations
              actions={a.next_best_actions?.final}
              policyDecision={c?.policy_decision}
            />

            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <svg viewBox="0 0 24 24">
                    <polyline points="4 17 10 11 4 5" />
                    <line x1="12" y1="19" x2="20" y2="19" />
                  </svg>
                  Agent Reasoning Trace
                </span>
              </div>
              <ul className="reasoning-list">
                {(a.reasoning || []).map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
              <div style={{ color: 'var(--text-tertiary)', margin: '10px 0 0', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                STOP CONDITION: {a.stop_reason}
              </div>
            </div>

            <FinCEN_SAR sar={a.sar} onCopySar={onCopySar} />
          </div>

          <div>
            <InvestigationTrace
              trace={a.trace || []}
              statusText={investigationStatus || `${(a.trace || []).length} STEPS`}
            />

            <SubgraphTopology caseDetail={a} />

            <GroundingEvidence evidence={c?.evidence} />

            <CaseMemory similarPriorCases={c?.similar_prior_cases} />
          </div>
        </div>
      )}
    </div>
  );
}
