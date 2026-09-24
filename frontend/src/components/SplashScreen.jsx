import React, { useState, useEffect } from 'react';

export default function SplashScreen({ onEnter }) {
  const [progress, setProgress] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [isExiting, setIsExiting] = useState(false);

  const steps = [
    'CONNECTING TIGERGRAPH CLUSTER · GOA NODE',
    'TRAVERSING 590,742 GRAPH TRANSACTIONS',
    'INDEXING 14,893 PAYMENT CARD ENTITIES',
    'CALIBRATING 5,565 HISTORICAL PRECEDENTS',
    'DETERMINISTIC POLICIES ARMED · READY',
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          return 100;
        }
        const next = prev + 2;
        const currentStep = Math.min(Math.floor((next / 100) * steps.length), steps.length - 1);
        setStepIndex(currentStep);
        return next;
      });
    }, 35);

    return () => clearInterval(timer);
  }, [steps.length]);

  const handleComplete = () => {
    setIsExiting(true);
    setTimeout(() => {
      onEnter();
    }, 400);
  };

  // Automatically transition into the console directly after reaching 100%
  useEffect(() => {
    if (progress >= 100 && !isExiting) {
      const autoTimer = setTimeout(() => {
        handleComplete();
      }, 250);
      return () => clearTimeout(autoTimer);
    }
  }, [progress, isExiting]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Escape') {
        e.preventDefault();
        handleComplete();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className={`splash-overlay ${isExiting ? 'splash-exit' : ''}`}>
      {/* Subtle Background Geometric Matrix */}
      <div className="splash-grid-bg" />

      {/* Top Header Row */}
      <div className="splash-topbar">
        <div />
        <button className="splash-skip-btn" onClick={handleComplete}>
          SKIP INTRO [ESC] &rarr;
        </button>
      </div>

      {/* Center Cinematic Content */}
      <div className="splash-center">
        {/* Animated Vector Topology Wave */}
        <div className="splash-wave-container">
          <svg className="splash-wave-svg" viewBox="0 0 800 120" preserveAspectRatio="none">
            <path
              className="splash-wave-path-1"
              d="M0,60 Q200,10 400,60 T800,60"
              fill="none"
              stroke="#000000"
              strokeWidth="2"
            />
            <path
              className="splash-wave-path-2"
              d="M0,60 Q200,110 400,60 T800,60"
              fill="none"
              stroke="#a1a1aa"
              strokeWidth="1.5"
              strokeDasharray="4 4"
            />
            <circle cx="200" cy="35" r="4" fill="#000000" />
            <circle cx="400" cy="60" r="5" fill="#000000" />
            <circle cx="600" cy="85" r="4" fill="#000000" />
          </svg>
        </div>

        <div className="splash-brand-mark">
          <svg viewBox="0 0 24 24">
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
        </div>

        <h1 className="splash-headline">FRAUDGRAPH</h1>
        <p className="splash-subheadline">
          Autonomous Graph Traversal &middot; Deterministic Fraud Intelligence
        </p>

        {/* Live Loading Telemetry */}
        <div className="splash-progress-card">
          <div className="splash-progress-bar-wrap">
            <div className="splash-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="splash-status-row">
            <span className="splash-status-text">{steps[stepIndex]}</span>
            <span className="splash-pct">{progress}%</span>
          </div>
        </div>
      </div>

      {/* Bottom Footer Info */}
      <div className="splash-footer">
        <span>POWERED BY TIGERGRAPH &middot; DEEP SUBGRAPH REASONING</span>
        <span>AUTO-LAUNCHING AT 100% &middot; PRESS [ESC] TO SKIP</span>
      </div>
    </div>
  );
}
