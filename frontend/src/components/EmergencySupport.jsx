import React, { useState, useEffect } from 'react';

export default function EmergencySupport() {
  const [report, setReport] = useState({
    section: 'DLI-GZB',
    anomalyType: 'SIGNAL_INTERLOCK_FAULT',
    severity: 'MEDIUM',
    details: '',
  });
  
  const [overrideActive, setOverrideActive] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [activeSpeedLimit, setActiveSpeedLimit] = useState(130);
  const [selectedSection, setSelectedSection] = useState('GZB-ALJN');
  const [diagnosticsChecklist, setDiagnosticsChecklist] = useState({
    gps: true,
    power: true,
    radio: false
  });
  const [pingStates, setPingStates] = useState({
    db: '9ms',
    api: '14ms',
    mlModel: '42ms',
    wsLink: '11ms'
  });
  const [activeAccordion, setActiveAccordion] = useState(null);
  const [reportedIncidents, setReportedIncidents] = useState([
    { id: 'RM-REP-8941', section: 'DLI-GZB', type: 'SIGNAL_FAULT', severity: 'MEDIUM', status: 'IN_REVIEW' },
    { id: 'RM-REP-3921', section: 'GZB-ALJN', type: 'WEATHER_FOG', severity: 'LOW', status: 'RESOLVED' }
  ]);

  const emergencyContacts = [
    { name: 'NDLS Section Controller', role: 'Delhi division main office', phone: '+91 11 2334 5678' },
    { name: 'Kanpur Main Operations', role: 'CNB Central Desk', phone: '+91 512 232 4455' },
    { name: 'Ghaziabad Junction Master', role: 'Station Control Room', phone: '+91 120 282 8900' },
    { name: 'Kavach Telemetry Support', role: 'RDSO Signal Lab', phone: '+91 522 245 1200' }
  ];

  // Fetch current speed lock values on section change
  useEffect(() => {
    const fetchSpeed = async () => {
      try {
        const res = await fetch('/api/v1/trains/speed-lock');
        if (res.ok) {
          const data = await res.json();
          if (data[selectedSection]) {
            setActiveSpeedLimit(data[selectedSection]);
          }
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchSpeed();
  }, [selectedSection]);

  // Submit Safety Anomaly
  const handleReportSubmit = (e) => {
    e.preventDefault();
    const newId = `RM-REP-${Math.floor(Math.random()*10000) + 1000}`;
    
    setReportedIncidents(prev => [
      {
        id: newId,
        section: report.section,
        type: report.anomalyType,
        severity: report.severity,
        status: 'PENDING'
      },
      ...prev
    ]);

    setFeedbackMsg({
      type: 'success',
      text: `Incident ${newId} registered successfully. Sealed block queued in Audit Ledger.`
    });
    setReport({ section: 'DLI-GZB', anomalyType: 'SIGNAL_INTERLOCK_FAULT', severity: 'MEDIUM', details: '' });
  };

  // Broadcast Kavach Emergency Brake Signal (EBS)
  const handleEmergencyOverride = async () => {
    const nextVal = !overrideActive;
    setOverrideActive(nextVal);
    
    try {
      const targetSpeed = nextVal ? 15 : 130;
      await fetch(`/api/v1/trains/speed-lock?section_code=GZB-ALJN&speed_limit=${targetSpeed}`, { method: 'POST' });
      await fetch(`/api/v1/trains/speed-lock?section_code=DLI-GZB&speed_limit=${targetSpeed}`, { method: 'POST' });
      
      setFeedbackMsg({
        type: nextVal ? 'warning' : 'success',
        text: nextVal 
          ? 'CRITICAL: Kavach Emergency Brake Signal (EBS) broadcasted! Speed locked to 15km/h across Sector North.' 
          : 'Emergency override resolved. Nominal signaling parameters restored.'
      });
    } catch (err) {
      console.error(err);
    }
  };

  // Set Manual Speed Limit Overrides
  const handleSetSpeedLimit = async (e) => {
    e.preventDefault();
    try {
      await fetch(`/api/v1/trains/speed-lock?section_code=${selectedSection}&speed_limit=${activeSpeedLimit}`, { method: 'POST' });
      setFeedbackMsg({
        type: 'success',
        text: `Speed limit for ${selectedSection} updated to ${activeSpeedLimit} km/h successfully.`
      });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="bento-grid" style={{ padding: '20px' }}>
      
      {/* Feature 1: Emergency Contacts & EBS Broadcast Action */}
      <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div className="glass-card" style={{ borderLeft: '4px solid var(--color-danger)', padding: '20px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px', color: 'var(--color-danger)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="led-indicator danger" style={{ width: '8px', height: '8px' }}></span> EMERGENCY HOTLINE DESK
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {emergencyContacts.map((c, i) => (
              <div key={i} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', fontSize: '0.75rem' }}>
                <span style={{ fontWeight: 700, display: 'block', color: 'white' }}>{c.name}</span>
                <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block' }}>{c.role}</span>
                <span style={{ fontFamily: 'monospace', color: 'var(--color-primary)', display: 'block', marginTop: '2px' }}>{c.phone}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Safety override action */}
        <div className="glass-card" style={{ background: 'rgba(239, 68, 68, 0.02)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '8px', color: 'var(--color-danger)' }}>Kavach Emergency Override</h4>
          <p style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginBottom: '12px', lineHeight: '1.4' }}>
            Broadcasting this signal overrides loop-holding states and issues absolute speed restrictions (15km/h) to all locomotives.
          </p>
          <button 
            onClick={handleEmergencyOverride} 
            className="btn-primary" 
            style={{ 
              width: '100%', 
              background: overrideActive ? 'var(--color-accent)' : 'var(--color-danger)', 
              color: overrideActive ? '#000000' : '#FFFFFF',
              boxShadow: overrideActive ? 'var(--shadow-neon-green)' : 'var(--shadow-neon-red)',
              fontSize: '0.75rem',
              fontWeight: 'bold'
            }}
          >
            {overrideActive ? 'CANCEL EBS BROADCAST' : 'BROADCAST EMERGENCY SIGNAL (EBS)'}
          </button>
        </div>
      </div>

      {/* Feature 2: Report Safety Anomaly Form & Live Incidents log */}
      <div style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {feedbackMsg && (
          <div style={{
            padding: '10px 14px',
            borderRadius: '6px',
            background: feedbackMsg.type === 'success' ? 'rgba(34, 197, 94, 0.05)' : 'rgba(239, 68, 68, 0.05)',
            border: `1px solid ${feedbackMsg.type === 'success' ? 'var(--color-accent)' : 'var(--color-danger)'}`,
            fontSize: '0.75rem',
            color: feedbackMsg.type === 'success' ? 'var(--color-accent)' : 'var(--color-danger)',
            lineHeight: '1.4'
          }}>
            <strong>{feedbackMsg.type === 'success' ? 'SUCCESS: ' : 'CRITICAL WARNING: '}</strong>
            {feedbackMsg.text}
          </div>
        )}

        <div className="glass-card" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Anomaly reporting form */}
          <div>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px', color: 'var(--color-primary)' }}>Report Blockage / Anomaly</h4>
            <form onSubmit={handleReportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Corridor Section</label>
                <select 
                  value={report.section} 
                  onChange={e => setReport({...report, section: e.target.value})}
                  style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', fontSize: '0.72rem', outline: 'none' }}
                >
                  <option value="DLI-GZB">Delhi - Ghaziabad (DLI-GZB)</option>
                  <option value="GZB-ALJN">Ghaziabad - Aligarh (GZB-ALJN)</option>
                  <option value="ALJN-CNB">Aligarh - Kanpur (ALJN-CNB)</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Type</label>
                  <select 
                    value={report.anomalyType} 
                    onChange={e => setReport({...report, anomalyType: e.target.value})}
                    style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', fontSize: '0.72rem', outline: 'none' }}
                  >
                    <option value="SIGNAL_FAULT">Interlocking Interlocking Fault</option>
                    <option value="KAVACH_OBU_FAILURE">Kavach OBU failure</option>
                    <option value="TRACK_FRACTURE">Track Fracture</option>
                    <option value="WEATHER_FOG">Heavy Fog Warning</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Severity</label>
                  <select 
                    value={report.severity} 
                    onChange={e => setReport({...report, severity: e.target.value})}
                    style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', fontSize: '0.72rem', outline: 'none' }}
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Details</label>
                <textarea 
                  rows="2" 
                  value={report.details} 
                  onChange={e => setReport({...report, details: e.target.value})}
                  placeholder="relays warnings..."
                  required
                  style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', fontSize: '0.72rem', outline: 'none', resize: 'none' }}
                />
              </div>

              <button type="submit" className="btn-primary" style={{ padding: '8px', fontSize: '0.75rem', marginTop: '4px' }}>
                Submit Incident Report
              </button>
            </form>
          </div>

          {/* Incident board */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px', color: 'var(--color-primary)' }}>Live Incident Board</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', maxHeight: '180px', flexGrow: 1 }}>
              {reportedIncidents.map(inc => (
                <div key={inc.id} style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.68rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: 700, color: 'white', display: 'block' }}>{inc.id} · {inc.section}</span>
                    <span style={{ color: 'var(--color-text-muted)' }}>Type: {inc.type} · Sev: <strong style={{ color: inc.severity === 'CRITICAL' ? 'var(--color-danger)' : 'var(--color-warning)' }}>{inc.severity}</strong></span>
                  </div>
                  <span style={{
                    fontSize: '0.55rem',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: inc.status === 'RESOLVED' ? 'rgba(34,197,94,0.1)' : 'rgba(0, 240, 255, 0.1)',
                    color: inc.status === 'RESOLVED' ? 'var(--color-accent)' : 'var(--color-primary)',
                    fontWeight: 'bold'
                  }}>
                    {inc.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Feature 3: Speed limit locking & Live Diagnostics Monitor */}
      <div className="glass-card" style={{ gridColumn: 'span 6', minHeight: '320px', display: 'flex', flexDirection: 'column' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '12px' }}>
          Speed Limit Locks & Diagnostic Ping
        </h4>

        {/* Speed Lock Form */}
        <form onSubmit={handleSetSpeedLimit} style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem', marginBottom: '15px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Segment Section</label>
              <select 
                value={selectedSection} 
                onChange={e => setSelectedSection(e.target.value)}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', fontSize: '0.72rem', outline: 'none' }}
              >
                <option value="DLI-GZB">Delhi - Ghaziabad (DLI-GZB)</option>
                <option value="GZB-ALJN">Ghaziabad - Aligarh (GZB-ALJN)</option>
                <option value="ALJN-CNB">Aligarh - Kanpur (ALJN-CNB)</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Speed Limit (km/h)</label>
              <input 
                type="number" 
                value={activeSpeedLimit}
                onChange={e => setActiveSpeedLimit(parseInt(e.target.value) || 0)}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', fontSize: '0.72rem', outline: 'none' }}
              />
            </div>
          </div>
          <button type="submit" className="btn-secondary" style={{ width: '100%', padding: '6px', fontSize: '0.72rem' }}>
            Override Speed Lock Parameters
          </button>
        </form>

        {/* Ping diagnostics */}
        <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
          Connection Latency Diagnostics
        </span>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px' }}>
          {[
            { label: "SQLITE DB", value: pingStates.db, color: 'var(--color-accent)' },
            { label: "API SRV", value: pingStates.api, color: 'var(--color-accent)' },
            { label: "XGB MODEL", value: pingStates.mlModel, color: 'var(--color-accent)' },
            { label: "TELE WS", value: pingStates.wsLink, color: 'var(--color-accent)' }
          ].map(ping => (
            <div key={ping.label} style={{ background: 'rgba(0,0,0,0.15)', padding: '8px', borderRadius: '4px', textAlign: 'center', border: '1px solid var(--border-color)' }}>
              <span style={{ fontSize: '0.5rem', color: 'var(--color-text-muted)', display: 'block' }}>{ping.label}</span>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: ping.color, display: 'block', marginTop: '2px' }}>{ping.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Feature 4: Kavach OBU Troubleshooter Wizard */}
      <div className="glass-card" style={{ gridColumn: 'span 6', minHeight: '320px', display: 'flex', flexDirection: 'column' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '12px' }}>
          Kavach OBU Troubleshooter
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flexGrow: 1, justifyContent: 'center' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Locomotive Hardware Self-Test Checklist:</span>
          {[
            { key: 'gps', label: "GPS Receiver lock synchrony" },
            { key: 'power', label: "Power Relay board validation" },
            { key: 'radio', label: "RF VHF Radio link channel sync" }
          ].map(chk => (
            <label key={chk.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', background: 'rgba(0,0,0,0.15)', padding: '8px 12px', borderRadius: '4px', cursor: 'pointer' }}>
              <span style={{ color: 'white' }}>{chk.label}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontWeight: 'bold', color: diagnosticsChecklist[chk.key] ? 'var(--color-accent)' : 'var(--color-danger)' }}>
                  {diagnosticsChecklist[chk.key] ? 'ONLINE' : 'FAILED'}
                </span>
                <input 
                  type="checkbox" 
                  checked={diagnosticsChecklist[chk.key]} 
                  onChange={() => setDiagnosticsChecklist({...diagnosticsChecklist, [chk.key]: !diagnosticsChecklist[chk.key]})}
                  style={{ accentColor: 'var(--color-primary)' }}
                />
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Feature 5: Disaster Management Accordion Reference */}
      <div className="glass-card" style={{ gridColumn: 'span 12' }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '15px' }}>
          Disaster Management & Standard Procedures Index
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {[
            { id: 1, title: "Procedure A: Emergency Track Fracture / Obstruction", desc: "1. Broadcast EBS immediate halt. 2. Dispatch relief van from closest station. 3. Notify downstream interlocking blocks to hold signals. 4. Initiate safety checklist." },
            { id: 2, title: "Procedure B: Electronic Interlocking Code Relays Failure", desc: "1. Switch section to manual block authority. 2. Max speeds locked to 30km/h on visual check. 3. Issue written Line Clear commands to locos." },
            { id: 3, title: "Procedure C: Kavach OBU Signal Telemetry Loss", desc: "1. Log telemetry fault details in Ledger. 2. Verify signal overlap via NTES cache. 3. Alert driver to proceed under manual signaling separation." }
          ].map(proc => (
            <div key={proc.id} style={{ border: '1px solid var(--border-color)', borderRadius: '6px', overflow: 'hidden' }}>
              <button 
                onClick={() => setActiveAccordion(activeAccordion === proc.id ? null : proc.id)}
                style={{
                  width: '100%', 
                  background: 'rgba(255,255,255,0.01)', 
                  border: 'none', 
                  color: 'white', 
                  textAlign: 'left', 
                  padding: '10px 15px', 
                  fontSize: '0.78rem', 
                  fontWeight: 700, 
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between'
                }}
              >
                <span>{proc.title}</span>
                <span>{activeAccordion === proc.id ? '▼' : '►'}</span>
              </button>
              {activeAccordion === proc.id && (
                <div style={{ background: 'var(--bg-terminal)', padding: '12px 15px', fontSize: '0.72rem', color: 'var(--color-text-muted)', borderTop: '1px solid var(--border-color)', lineHeight: '1.4' }}>
                  {proc.desc}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
