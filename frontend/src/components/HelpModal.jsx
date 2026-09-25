import React from 'react';

export default function HelpModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-row">
            <div className="modal-icon">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            </div>
            <div>
              <h3>How FraudGraph Agent Works</h3>
              <p className="modal-subtitle">Beginner's guide to autonomous graph intelligence</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} title="Close Guide">
            &times;
          </button>
        </div>

        <div className="modal-body">
          {/* Core concept in 2 sentences */}
          <div className="guide-card primary">
            <h4>The Core Concept</h4>
            <p>
              Traditional fraud tools look at transactions one by one in isolation. <b>FraudGraph Agent</b> uses <b>TigerGraph</b> to connect <b>860,000+ real transactions, cards, devices, and merchants</b> into a live knowledge graph to expose hidden criminal fraud rings in milliseconds.
            </p>
          </div>

          {/* 3 Step Workflow */}
          <h4 className="guide-section-title">3 Simple Steps to Use This Dashboard</h4>
          <div className="guide-steps-grid">
            <div className="guide-step">
              <span className="step-num-pill">STEP 1</span>
              <h5>Pick an Alert</h5>
              <p>Browse suspicious transactions in the left queue. Cards are color-coded: <b>Red</b> for high risk, <b>Amber</b> for human review, and <b>Green</b> for safe.</p>
            </div>

            <div className="guide-step">
              <span className="step-num-pill">STEP 2</span>
              <h5>Execute Investigation</h5>
              <p>Click the <b>"Execute Investigation"</b> button. The agent instantly traces connected devices, recent transaction spikes, and matches 5,500+ past cases.</p>
            </div>

            <div className="guide-step">
              <span className="step-num-pill">STEP 3</span>
              <h5>Review &amp; Act</h5>
              <p>See the explainable decision gauge, recommended actions (e.g., auto-freeze stolen card), and read the generated <b>FinCEN SAR regulatory report</b> ready for law enforcement.</p>
            </div>
          </div>

          {/* Key Terms Glossary */}
          <h4 className="guide-section-title">What The Terms Mean (Plain English)</h4>
          <div className="glossary-grid">
            <div className="glossary-item">
              <b>Calibrated Probability</b>
              <span>How likely the transaction is fraudulent (0% is completely safe, 100% is definite fraud).</span>
            </div>
            <div className="glossary-item">
              <b>Deterministic Policy</b>
              <span>Banking safety rules that guarantee 100% explainable, legal decisions without AI hallucinations.</span>
            </div>
            <div className="glossary-item">
              <b>FinCEN SAR</b>
              <span>Suspicious Activity Report: The mandatory government document banks file when fraud is discovered.</span>
            </div>
            <div className="glossary-item">
              <b>GRIP GraphRAG</b>
              <span>The research studio tab comparing traditional search vs graph-powered AI ground truth.</span>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose}>
            GOT IT &mdash; LET'S INVESTIGATE &rarr;
          </button>
        </div>
      </div>
    </div>
  );
}
