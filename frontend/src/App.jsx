import React, { useState, useEffect } from 'react';
import TelemetryMap from './components/TelemetryMap';
import AgentLogs from './components/AgentLogs';
import Recommendations from './components/Recommendations';
import RACPredictor from './components/RACPredictor';
import AuditLedger from './components/AuditLedger';
import OperatorProfile from './components/OperatorProfile';
import EmergencySupport from './components/EmergencySupport';

export default function App() {
  const [scenarioState, setScenarioState] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard'); // Tabs: dashboard, rac, audit, profile, support

  // Fetch current scenario state and audit logs
  const fetchData = async () => {
    try {
      const resScenario = await fetch('/api/v1/cascade/scenario');
      if (resScenario.ok) {
        const data = await resScenario.json();
        setScenarioState(data);
      }
      
      const resAudit = await fetch('/api/v1/audit');
      if (resAudit.ok) {
        const data = await resAudit.json();
        setAuditLogs(data);
      }
    } catch (err) {
      setError("Failed to establish telemetry link with backend server.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Advance scenario step forward
  const handleNextStep = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/cascade/scenario/next', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setScenarioState(data);
        
        // Refresh audit logs
        const resAudit = await fetch('/api/v1/audit');
        if (resAudit.ok) {
          const auditData = await resAudit.json();
          setAuditLogs(auditData);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Reset scenario to nominal
  const handleReset = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/cascade/scenario/reset', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setScenarioState(data);
        setAuditLogs([]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Jump directly to a step
  const handleJumpToStep = async (targetStep) => {
    if (targetStep === scenarioState?.step) return;
    setLoading(true);
    try {
      let res = await fetch('/api/v1/cascade/scenario/reset', { method: 'POST' });
      let data = await res.json();
      
      for (let i = 0; i < targetStep; i++) {
        const nextRes = await fetch('/api/v1/cascade/scenario/next', { method: 'POST' });
        data = await nextRes.json();
      }
      setScenarioState(data);
      
      const resAudit = await fetch('/api/v1/audit');
      if (resAudit.ok) {
        const auditData = await resAudit.json();
        setAuditLogs(auditData);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Recommendation approvals
  const handleApproveRec = async (recId) => {
    try {
      const res = await fetch(`/api/v1/cascade/recommendations/${recId}/approve`, { method: 'POST' });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Recommendation manual overrides
  const handleOverrideRec = async (recId, reason) => {
    try {
      const res = await fetch(`/api/v1/cascade/recommendations/${recId}/override?override_reason=${encodeURIComponent(reason)}`, { method: 'POST' });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (error) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: '#060810', color: 'var(--color-danger)' }}>
        <div className="glass-card" style={{ padding: '40px', textAlign: 'center', border: '1px solid var(--color-danger)' }}>
          <h2 style={{ marginBottom: '15px' }}>Operational Outage</h2>
          <p>{error}</p>
          <button className="btn-secondary" onClick={fetchData} style={{ marginTop: '20px' }}>Retry Connection</button>
        </div>
      </div>
    );
  }

  const stepDetails = [
    { title: "Nominal", desc: "Corridor runs at standard operational threshold" },
    { title: "Signal Fault", desc: "Interlocking code 0x4F failure at New Delhi exit" },
    { title: "Route Conflict", desc: "Shatabdi rescheduled path conflicts with Freight BOXN-902" },
    { title: "Cascade Predict", desc: "BFS projections identify 180 total minutes delay addition" },
    { title: "Dispatch Action", desc: "Dynamic hold recommendation formulated for loop line hold" },
    { title: "Passenger Advisories", desc: "Alternative routes push with 88% RAC probability" },
    { title: "Resolution", desc: "Controller approves recommend, traffic normalized" }
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#060810' }}>
      {/* Header Panel */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">RM</div>
          <div>
            <h1 className="brand-title">RailMind Dispatcher Console</h1>
            <div className="brand-tagline">Autonomous Intelligence for Indian Railways</div>
          </div>
        </div>

        {/* Tab Routing Links */}
        <nav style={{ display: 'flex', gap: '25px', height: '100%' }}>
          <button className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            Telemetry Radar
          </button>
          <button className={`nav-tab ${activeTab === 'rac' ? 'active' : ''}`} onClick={() => setActiveTab('rac')}>
            ML RAC Solver
          </button>
          <button className={`nav-tab ${activeTab === 'audit' ? 'active' : ''}`} onClick={() => setActiveTab('audit')}>
            Audit Ledger
          </button>
          <button className={`nav-tab ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => setActiveTab('profile')}>
            Operator Profile
          </button>
          <button className={`nav-tab ${activeTab === 'support' ? 'active' : ''}`} onClick={() => setActiveTab('support')}>
            System Helpline
          </button>
        </nav>
      </header>

      {/* Control Toolbar */}
      {scenarioState && (
        <div className="control-toolbar">
          {/* Active Step Indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className={`led-indicator ${scenarioState.step === 0 ? 'active' : scenarioState.step === 6 ? 'active' : 'danger'}`}></span>
            <span style={{ fontSize: '0.8rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--color-text-main)', letterSpacing: '0.5px' }}>
              Step {scenarioState.step} : {scenarioState.title}
            </span>
            <span className="toolbar-desc" style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              — {scenarioState.description}
            </span>
          </div>

          {/* Stepper Timeline & Action buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.01)', padding: '5px 12px', borderRadius: '30px', border: '1px solid var(--border-color)', gap: '10px' }}>
              <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Timeline:</span>
              <div style={{ display: 'flex', gap: '5px' }}>
                {stepDetails.map((step, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleJumpToStep(idx)}
                    title={step.title + ": " + step.desc}
                    disabled={loading}
                    className={`timeline-step-btn ${scenarioState.step === idx ? 'active' : idx < scenarioState.step ? 'passed' : ''}`}
                  >
                    {idx}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                className="btn-primary" 
                onClick={handleNextStep} 
                disabled={loading || scenarioState.step >= scenarioState.max_steps}
                style={{ padding: '6px 14px', fontSize: '0.75rem', opacity: scenarioState.step >= scenarioState.max_steps ? 0.5 : 1 }}
              >
                {loading ? 'Advancing...' : 'Next Step'}
              </button>
              <button className="btn-secondary" onClick={handleReset} disabled={loading} style={{ padding: '6px 14px', fontSize: '0.75rem' }}>
                Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Render based on active tab */}
      <div style={{ flexGrow: 1, padding: '20px 0' }}>
        {scenarioState && (
          <>
            {activeTab === 'dashboard' && (
              <main className="bento-grid" style={{ opacity: loading ? 0.75 : 1, transition: 'opacity 0.2s' }}>
                <TelemetryMap trains={scenarioState.trains} disruptions={scenarioState.disruptions} />
                <Recommendations 
                  recommendations={scenarioState.recommendations} 
                  onApprove={handleApproveRec} 
                  onOverride={handleOverrideRec} 
                />
                <AgentLogs logs={scenarioState.logs} />
              </main>
            )}

            {activeTab === 'rac' && (
              <main className="bento-grid" style={{ opacity: loading ? 0.75 : 1, transition: 'opacity 0.2s' }}>
                <div style={{ gridColumn: 'span 12' }}>
                  <RACPredictor />
                </div>
              </main>
            )}

            {activeTab === 'audit' && (
              <main className="bento-grid" style={{ opacity: loading ? 0.75 : 1, transition: 'opacity 0.2s' }}>
                <div style={{ gridColumn: 'span 12' }}>
                  <AuditLedger auditLogs={auditLogs} />
                </div>
              </main>
            )}

            {activeTab === 'profile' && (
              <main style={{ opacity: loading ? 0.75 : 1, transition: 'opacity 0.2s' }}>
                <OperatorProfile />
              </main>
            )}

            {activeTab === 'support' && (
              <main style={{ opacity: loading ? 0.75 : 1, transition: 'opacity 0.2s' }}>
                <EmergencySupport />
              </main>
            )}
          </>
        )}
      </div>
    </div>
  );
}
