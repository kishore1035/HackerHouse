import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import EmptyState from './components/EmptyState';
import CaseDetail from './components/CaseDetail';
import Toast from './components/Toast';
import SplashScreen from './components/SplashScreen';
import GripGraphRAG from './components/GripGraphRAG';
import HelpModal from './components/HelpModal';

export default function App() {
  const [activeView, setActiveView] = useState('investigation');
  const [showSplash, setShowSplash] = useState(true);
  const [showGuide, setShowGuide] = useState(false);
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState({
    transactions: 590742,
    cards: 14893,
    closed_cases: 5565,
    agent_cases: 20,
    avg_latency: 12.7,
  });
  const [selectedId, setSelectedId] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [currentFilter, setCurrentFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigationStatus, setInvestigationStatus] = useState('');
  const [toastMsg, setToastMsg] = useState('');
  const [toastVisible, setToastVisible] = useState(false);

  const showToast = useCallback((msg) => {
    setToastMsg(msg);
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 2200);
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) setStats(await res.json());
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  }, []);

  const loadCases = useCallback(async () => {
    try {
      const res = await fetch('/api/cases');
      if (res.ok) {
        const data = await res.json();
        setCases(data);
        return data;
      }
    } catch (e) {
      console.error('Failed to load cases:', e);
    }
    return [];
  }, []);

  const loadCaseDetail = useCallback(async (id) => {
    try {
      const res = await fetch(`/api/cases/${id}`);
      if (res.ok) {
        const detail = await res.json();
        setSelectedDetail(detail);
      } else {
        setSelectedDetail(null);
      }
    } catch (e) {
      console.error('Failed to load case detail:', e);
      setSelectedDetail(null);
    }
  }, []);

  const handleSelectCase = useCallback((id) => {
    setSelectedId(id);
    window.location.hash = id;
    loadCaseDetail(id);
  }, [loadCaseDetail]);

  // Initial load
  useEffect(() => {
    loadStats();
    loadCases().then((loaded) => {
      const hash = window.location.hash.slice(1);
      if (hash && loaded.some((c) => c.case_id === hash)) {
        handleSelectCase(hash);
      } else if (loaded && loaded.length > 0) {
        handleSelectCase(loaded[0].case_id);
      }
    });
  }, [loadStats, loadCases, handleSelectCase]);

  // Hash change listener
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.slice(1);
      if (hash && hash !== selectedId) {
        handleSelectCase(hash);
      }
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, [selectedId, handleSelectCase]);

  // Filter calculation
  const filterCounts = useMemo(() => {
    return {
      all: cases.length,
      fraud: cases.filter((c) => c.verdict === 'fraud').length,
      uncertain: cases.filter((c) => c.verdict === 'uncertain' || !c.verdict).length,
      legitimate: cases.filter((c) => c.verdict === 'legitimate').length,
    };
  }, [cases]);

  const filteredCases = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return cases.filter((c) => {
      const verdict = c.verdict || 'uncertain';
      if (currentFilter !== 'all' && verdict !== currentFilter) return false;
      if (q) {
        const matchId = (c.case_id || '').toLowerCase().includes(q);
        const matchCard = (c.card_id || '').toLowerCase().includes(q);
        const matchPattern = (c.pattern || '').toLowerCase().includes(q);
        const matchTrigger = (c.trigger_type || '').toLowerCase().includes(q);
        if (!matchId && !matchCard && !matchPattern && !matchTrigger) return false;
      }
      return true;
    });
  }, [cases, currentFilter, searchQuery]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') e.target.blur();
        return;
      }
      if (e.key === '/' || ((e.metaKey || e.ctrlKey) && e.key === 'k')) {
        e.preventDefault();
        const input = document.getElementById('search');
        input?.focus();
        input?.select();
        return;
      }
      if (!filteredCases.length) return;
      const curIdx = filteredCases.findIndex((c) => c.case_id === selectedId);

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIdx = curIdx < filteredCases.length - 1 ? curIdx + 1 : 0;
        const nextId = filteredCases[nextIdx].case_id;
        handleSelectCase(nextId);
        document.querySelector(`[data-id="${nextId}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIdx = curIdx > 0 ? curIdx - 1 : filteredCases.length - 1;
        const prevId = filteredCases[prevIdx].case_id;
        handleSelectCase(prevId);
        document.querySelector(`[data-id="${prevId}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      } else if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        if (!isInvestigating && selectedId) {
          runInvestigation();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filteredCases, selectedId, isInvestigating, handleSelectCase]);

  // Live Investigation Execution via SSE
  const runInvestigation = async () => {
    if (!selectedId || isInvestigating) return;
    setIsInvestigating(true);
    setInvestigationStatus('EXECUTING QUERY STREAM FROM TIGERGRAPH...');

    // Clear prior detail while streaming trace
    setSelectedDetail((prev) => ({
      case: prev?.case || {},
      trace: [],
      next_best_actions: { final: [] },
      sar: { file: false },
      reasoning: [],
    }));

    try {
      const res = await fetch(`/api/investigate/${selectedId}`, { method: 'POST' });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf('\n\n')) >= 0) {
          const blk = buf.slice(0, i);
          buf = buf.slice(i + 2);
          const ev = /event: (\w+)/.exec(blk)?.[1];
          const dataMatch = /data: (.*)/s.exec(blk);
          if (!dataMatch) continue;
          const data = JSON.parse(dataMatch[1]);

          if (ev === 'step') {
            setSelectedDetail((prev) => ({
              ...prev,
              trace: [...(prev?.trace || []), data],
            }));
          }
          if (ev === 'done') {
            setSelectedDetail(data);
            setIsInvestigating(false);
            setInvestigationStatus('');
            await loadCases();
            await loadStats();
            showToast('Investigation complete');
          }
          if (ev === 'error') {
            setSelectedDetail((prev) => ({
              ...prev,
              trace: [
                ...(prev?.trace || []),
                { action: 'Investigation Error', output: data.error },
              ],
            }));
            setIsInvestigating(false);
            setInvestigationStatus('FAILED');
            showToast(`Error: ${data.error}`);
          }
        }
      }
    } catch (err) {
      console.error('Investigation error:', err);
      setIsInvestigating(false);
      setInvestigationStatus('NETWORK ERROR');
      showToast(`Network error: ${err.message}`);
    }
  };

  const handleCopyJson = (data) => {
    navigator.clipboard?.writeText(JSON.stringify(data, null, 2));
    showToast('Case JSON payload copied to clipboard');
  };

  const handleCopySar = (text) => {
    navigator.clipboard?.writeText(text);
    showToast('FinCEN SAR narrative copied to clipboard');
  };

  const selectedMeta = useMemo(() => {
    return cases.find((c) => c.case_id === selectedId);
  }, [cases, selectedId]);

  return (
    <div className={`app ${activeView === 'grip' ? 'view-grip' : ''}`}>
      <Header
        stats={stats}
        onShowSplash={() => setShowSplash(true)}
        activeView={activeView}
        onSelectView={setActiveView}
        onOpenGuide={() => setShowGuide(true)}
      />

      {activeView === 'investigation' && (
        <Sidebar
          cases={filteredCases}
          selectedId={selectedId}
          onSelectCase={handleSelectCase}
          currentFilter={currentFilter}
          onSetFilter={setCurrentFilter}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onClearSearch={() => setSearchQuery('')}
          filterCounts={filterCounts}
        />
      )}

      <main id="main" className={activeView === 'grip' ? 'main-full' : ''}>
        {activeView === 'grip' ? (
          <GripGraphRAG onCopy={handleCopyJson} />
        ) : !selectedMeta ? (
          <EmptyState />
        ) : (
          <CaseDetail
            caseMeta={selectedMeta}
            caseDetail={selectedDetail}
            isInvestigating={isInvestigating}
            investigationStatus={investigationStatus}
            onRunInvestigation={runInvestigation}
            onCopyJson={handleCopyJson}
            onCopySar={handleCopySar}
          />
        )}
      </main>

      <Toast message={toastMsg} isVisible={toastVisible} />

      <HelpModal isOpen={showGuide} onClose={() => setShowGuide(false)} />

      {showSplash && <SplashScreen onEnter={() => setShowSplash(false)} />}
    </div>
  );
}
