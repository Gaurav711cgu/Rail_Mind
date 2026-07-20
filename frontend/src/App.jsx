import { useState, useEffect } from 'react';
import TelemetryMap from './components/TelemetryMap';
import AgentLogs from './components/AgentLogs';
import Recommendations from './components/Recommendations';
import RACPredictor from './components/RACPredictor';
import AuditLedger from './components/AuditLedger';
import OperatorProfile from './components/OperatorProfile';
import EmergencySupport from './components/EmergencySupport';
import SystemStatusBar from './components/SystemStatusBar';
import AgentsPage from './pages/AgentsPage';
import ModeToggle from './components/ModeToggle';
import DataSourceBadge from './components/DataSourceBadge';
import LLMModeBadge from './components/LLMModeBadge';
import LiveRunPanel from './components/LiveRunPanel';
const stepDetails = [
  { title: "Nominal",            desc: "Corridor runs at standard operational threshold" },
  { title: "Signal Fault",       desc: "Interlocking code 0x4F failure at New Delhi exit" },
  { title: "Route Conflict",     desc: "Shatabdi path conflicts with Freight BOXN-902" },
  { title: "Cascade Predict",    desc: "BFS projections identify 180 min delay addition" },
  { title: "Dispatch Action",    desc: "Dynamic hold recommendation for loop line" },
  { title: "Advisories",         desc: "Alternative routes push — 88% RAC probability" },
  { title: "Resolution",         desc: "Controller approves, traffic normalized" },
];

export default function App() {
  const [scenarioState, setScenarioState] = useState(null);
  const [auditLogs, setAuditLogs]         = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [activeTab, setActiveTab]         = useState('dashboard');
  const [isLiveMode, setIsLiveMode]       = useState(false);

  const fetchData = async () => {
    try {
      const [resScenario, resAudit] = await Promise.all([
        fetch('/api/v1/cascade/scenario'),
        fetch('/api/v1/audit'),
      ]);
      if (resScenario.ok) setScenarioState(await resScenario.json());
      if (resAudit.ok)    setAuditLogs(await resAudit.json());
    } catch {
      setError('Failed to establish telemetry link with backend server.');
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { fetchData(); }, []);

  const handleNextStep = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/cascade/scenario/next', { method: 'POST' });
      if (res.ok) {
        setScenarioState(await res.json());
        const ra = await fetch('/api/v1/audit');
        if (ra.ok) setAuditLogs(await ra.json());
      }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/cascade/scenario/reset', { method: 'POST' });
      if (res.ok) { setScenarioState(await res.json()); setAuditLogs([]); }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleJumpToStep = async (targetStep) => {
    if (targetStep === scenarioState?.step) return;
    setLoading(true);
    try {
      await fetch('/api/v1/cascade/scenario/reset', { method: 'POST' });
      let data;
      for (let i = 0; i < targetStep; i++) {
        const r = await fetch('/api/v1/cascade/scenario/next', { method: 'POST' });
        data = await r.json();
      }
      if (!data) {
        const r = await fetch('/api/v1/cascade/scenario');
        data = await r.json();
      }
      setScenarioState(data);
      const ra = await fetch('/api/v1/audit');
      if (ra.ok) setAuditLogs(await ra.json());
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleApproveRec = async (recId) => {
    try {
      const res = await fetch(`/api/v1/cascade/recommendations/${recId}/approve`, { method: 'POST' });
      if (res.ok) fetchData();
    } catch (err) { console.error(err); }
  };

  const handleOverrideRec = async (recId, reason) => {
    try {
      const res = await fetch(`/api/v1/cascade/recommendations/${recId}/override?override_reason=${encodeURIComponent(reason)}`, { method: 'POST' });
      if (res.ok) fetchData();
    } catch (err) { console.error(err); }
  };

  const handleTriggerLive = async () => {
    try {
      await fetch('/api/v1/live/trigger', { method: 'POST' });
    } catch (err) { console.error(err); }
  };

  /* ── SYSTEM STATUS LABEL ── */
  const getStatusLabel = (step) => {
    if (step === 0) return { label: 'NOMINAL', color: 'var(--status-ok)', variant: 'healthy' };
    if (step === 6) return { label: 'RESOLVED', color: 'var(--ink-muted)', variant: 'resolved' };
    if (step >= 4)  return { label: 'CRITICAL', color: 'var(--status-fail)', variant: 'failed' };
    return { label: 'ALERT', color: 'var(--status-warn)', variant: 'in-review' };
  };

  /* ── ERROR STATE ── */
  if (error) {
    return (
      <div style={{ display:'flex', height:'100vh', alignItems:'center', justifyContent:'center' }}>
        <div style={{
          padding:'40px',
          textAlign:'center',
          background: 'var(--surface-panel)',
          border:'1px solid var(--border-accent)',
          borderRadius: 'var(--rounded-md)',
          maxWidth: 420
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '2px',
            color: 'var(--accent)',
            textTransform: 'uppercase',
            marginBottom: 12
          }}>
            WARNING: OPERATIONAL OUTAGE
          </div>
          <p style={{ fontFamily: "'Inter', sans-serif", color: 'var(--ink-soft)', fontSize: '13px', marginBottom: 20 }}>
            {error}
          </p>
          <button className="btn-secondary" onClick={fetchData}>Retry Connection</button>
        </div>
      </div>
    );
  }

  const status = scenarioState ? getStatusLabel(scenarioState.step) : null;

  const TABS = [
    { id: 'dashboard', label: 'Telemetry Radar' },
    { id: 'rac',       label: 'ML RAC Solver' },
    { id: 'audit',     label: 'Audit Ledger' },
    { id: 'agents',    label: 'Decision Flow' },
    { id: 'profile',   label: 'Operator Profile' },
    { id: 'support',   label: 'System Helpline' },
  ];

  return (
    <div style={{ minHeight:'100vh', display:'flex', flexDirection:'column', paddingBottom:'24px' }}>

      {/* ── HEADER ── */}
      <header className="app-header">
        <div className="brand-section">
          <img src="/logo.jpg" className="brand-logo-img" alt="RailMind Logo" />
          <div>
            <div className="brand-title">RailMind</div>
            <div className="brand-tagline">Operations Solver · Indian Railways</div>
          </div>
        </div>

        <nav>
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <ModeToggle isLive={isLiveMode} setIsLive={setIsLiveMode} onTriggerLive={handleTriggerLive} />
          <DataSourceBadge source={isLiveMode ? 'NTES' : 'SCENARIO'} />
          <LLMModeBadge isAgentic={true} />
          {/* System status badge — top right */}
          {status && (
            <div className={`badge-status ${status.variant}`}>
              <span className={`led-indicator ${scenarioState.step === 0 || scenarioState.step === 6 ? 'active' : scenarioState.step >= 4 ? 'danger' : 'warning'}`} />
              <span>
                {status.label}
              </span>
            </div>
          )}
        </div>
      </header>

      {/* ── CONTROL TOOLBAR ── */}
      {scenarioState && (
        <div className="control-toolbar">
          <div style={{ display:'flex', alignItems:'center', gap:10, flexShrink:0 }}>
            <span style={{ fontFamily:"'Inter', sans-serif", fontSize:'16px', fontWeight:600, color:'var(--ink)', textTransform:'uppercase', whiteSpace:'nowrap' }}>
              {scenarioState.title} OPERATION — SECTOR NORTH
            </span>
          </div>

          {/* Scrolling status ticker center */}
          <div className="status-ticker-container">
            <marquee scrollamount="3">
              [SYSTEM STATUS: {scenarioState.step === 0 ? 'NOMINAL OPERATIONS — ALL TRACK SEGMENTS REPORTING NORMAL SIGNAL INTEG' : `OUTAGE DETECTED — ${scenarioState.description.toUpperCase()} — CORRIDOR ACTIONS IN PROGRESS`} — LATENCY: 2.1s — INTEGRITY: SECURE]
            </marquee>
          </div>

          <div style={{ display:'flex', alignItems:'center', gap:16, flexShrink:0 }}>
            {/* Timeline stepper */}
            <div style={{ display:'flex', alignItems:'center', gap:6 }}>
              <span style={{ fontSize:'0.58rem', fontWeight:700, color:'var(--ink-muted)', textTransform:'uppercase', letterSpacing:'1px', fontFamily:"'JetBrains Mono', monospace" }}>
                TL
              </span>
              <div style={{ display:'flex', gap:4 }}>
                {stepDetails.map((step, idx) => (
                  <button
                    key={idx}
                    className={`timeline-step-btn ${scenarioState.step === idx ? 'active' : idx < scenarioState.step ? 'passed' : ''}`}
                    onClick={() => handleJumpToStep(idx)}
                    title={`${step.title}: ${step.desc}`}
                    disabled={loading}
                  >
                    {idx}
                  </button>
                ))}
              </div>
            </div>

            {/* Action buttons */}
            <div style={{ display:'flex', gap:6 }}>
              <button
                className="btn-primary"
                onClick={handleNextStep}
                disabled={loading || scenarioState.step >= scenarioState.max_steps}
              >
                {loading ? '···' : 'Next Step'}
              </button>
              <button className="btn-secondary" onClick={handleReset} disabled={loading}>
                Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MAIN CONTENT ── */}
      <div style={{ flexGrow:1, padding:'4px 0' }}>
        {scenarioState && (
          <div style={{ opacity: loading ? 0.7 : 1, transition:'opacity 0.2s' }}>
            {activeTab === 'dashboard' && (
              <main className="bento-grid">
                <TelemetryMap
                  trains={scenarioState.trains}
                  disruptions={scenarioState.disruptions}
                  onNextStep={handleNextStep}
                  scenarioStep={scenarioState.step}
                />
                <Recommendations
                  recommendations={scenarioState.recommendations}
                  onApprove={handleApproveRec}
                  onOverride={handleOverrideRec}
                />
                <AgentLogs logs={scenarioState.logs} />
              </main>
            )}

            {activeTab === 'rac' && (
              <main className="bento-grid">
                <div style={{ gridColumn:'span 12' }}><RACPredictor /></div>
              </main>
            )}

            {activeTab === 'audit' && (
              <main className="bento-grid">
                <div style={{ gridColumn:'span 12' }}><AuditLedger auditLogs={auditLogs} /></div>
              </main>
            )}

            {activeTab === 'agents' && (
              <main style={{ padding:'12px 0' }}>
                <AgentsPage />
              </main>
            )}

            {activeTab === 'profile' && (
              <main className="bento-grid">
                <div style={{ gridColumn:'span 12' }}><OperatorProfile /></div>
              </main>
            )}

            {activeTab === 'support' && (
              <main className="bento-grid">
                <div style={{ gridColumn:'span 12' }}><EmergencySupport /></div>
              </main>
            )}
          </div>
        )}
      </div>

      {/* ── SYSTEM STATUS BAR ── */}
      <SystemStatusBar />
      
      {isLiveMode && <LiveRunPanel />}
    </div>
  );
}
