import React, { useState, useEffect } from 'react';
import TelemetryMap from './components/TelemetryMap';
import AgentLogs from './components/AgentLogs';
import Recommendations from './components/Recommendations';
import RACPredictor from './components/RACPredictor';
import AuditLedger from './components/AuditLedger';

export default function App() {
  const [scenarioState, setScenarioState] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch current scenario state and audit logs
  const fetchData = async () => {
    try {
      const resScenario = await fetch('/api/v1/cascade/scenario');
      if (resScenario.ok) {
        const data = await resScenario.json();
        setScenarioState(data);
      }
      
      const resAudit = await fetch('/api/v1/audit/');
      if (resAudit.ok) {
        const data = await resAudit.json();
        setAuditLogs(data);
      }
    } catch (err) {
      setError("Failed to establish websocket telemetry link with backend server.");
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
        const resAudit = await fetch('/api/v1/audit/');
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

  // Jump directly to a step by resetting and stepping forward
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
      
      const resAudit = await fetch('/api/v1/audit/');
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
        // Reload scenario and audit states
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
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: '#080C14', color: 'var(--color-danger)' }}>
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
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Panel */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">RM</div>
          <div>
            <h1 className="brand-title">RailMind Dispatcher Console</h1>
            <div className="brand-tagline">Autonomous Intelligence for Indian Railways</div>
          </div>
        </div>

        {/* Step-Timeline Node Selector */}
        {scenarioState && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '6px 15px', borderRadius: '30px', border: '1px solid var(--border-color)', gap: '15px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Simulation Timeline:</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {stepDetails.map((step, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleJumpToStep(idx)}
                    title={step.desc}
                    disabled={loading}
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: scenarioState.step === idx 
                        ? 'var(--color-primary)' 
                        : idx < scenarioState.step 
                          ? 'rgba(0, 240, 255, 0.15)' 
                          : 'transparent',
                      border: `2.5px solid ${scenarioState.step === idx ? 'white' : idx < scenarioState.step ? 'var(--color-primary)' : 'var(--border-color)'}`,
                      color: scenarioState.step === idx ? '#04060A' : 'var(--color-text-muted)',
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.3s'
                    }}
                  >
                    {idx}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Step triggers */}
            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                className="btn-primary" 
                onClick={handleNextStep} 
                disabled={loading || scenarioState.step >= scenarioState.max_steps}
                style={{ opacity: scenarioState.step >= scenarioState.max_steps ? 0.5 : 1 }}
              >
                {loading ? 'Advancing...' : 'Next Step'}
              </button>
              <button className="btn-secondary" onClick={handleReset} disabled={loading}>
                Reset
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Main Grid Body */}
      {scenarioState && (
        <main className="bento-grid" style={{ opacity: loading ? 0.75 : 1, transition: 'opacity 0.2s' }}>
          {/* Active Step Status Card */}
          <div className="glass-card" style={{ gridColumn: 'span 12', borderLeft: `4px solid ${scenarioState.step === 0 ? 'var(--color-accent)' : scenarioState.step === 6 ? 'var(--color-accent)' : 'var(--color-danger)'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-primary)', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1.5px' }}>
                  STEP {scenarioState.step} OF {scenarioState.max_steps} : {scenarioState.title}
                </span>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '2px' }}>{stepDetails[scenarioState.step].title}</h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                  {scenarioState.description}
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`led-indicator ${scenarioState.step === 0 ? 'active' : scenarioState.step === 6 ? 'active' : 'danger'}`}></span>
                <span style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>
                  {scenarioState.step === 0 ? 'Corridor Normal' : scenarioState.step === 6 ? 'Cascade Resolved' : 'Outage Active'}
                </span>
              </div>
            </div>
          </div>

          {/* Telemetry Route Map */}
          <TelemetryMap trains={scenarioState.trains} disruptions={scenarioState.disruptions} />

          {/* Terminal Console */}
          <AgentLogs logs={scenarioState.logs} />

          {/* Recommendations Card */}
          <Recommendations 
            recommendations={scenarioState.recommendations} 
            onApprove={handleApproveRec} 
            onOverride={handleOverrideRec} 
          />

          {/* RAC prediction Tool */}
          <RACPredictor />

          {/* Cryptographic chain verification */}
          <AuditLedger auditLogs={auditLogs} />
        </main>
      )}
    </div>
  );
}
