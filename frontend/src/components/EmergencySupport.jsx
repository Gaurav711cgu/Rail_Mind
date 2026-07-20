import { useState, useEffect } from 'react';

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
  const [pingStates] = useState({
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

  const getStatusBadgeClass = (status) => {
    if (status === 'RESOLVED') return 'resolved';
    if (status === 'IN_REVIEW') return 'in-review';
    return 'pending';
  };

  return (
    <div className="bento-grid" style={{ padding: '0 24px' }}>
      
      {/* Feature 1: Emergency Contacts & EBS Broadcast Action */}
      <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        
        {/* EMERGENCY HOTLINE DESK */}
        <div style={{
          background: 'var(--accent-subtle)',
          border: '1px solid var(--border-accent)',
          borderRadius: 'var(--rounded-md)',
          padding: '24px',
          boxSizing: 'border-box'
        }}>
          <h4 style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '13px',
            fontWeight: 700,
            letterSpacing: '2px',
            textTransform: 'uppercase',
            color: 'var(--accent)',
            margin: '0 0 16px 0',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span className="led-indicator danger" style={{ width: '6px', height: '6px' }}></span>
            Emergency Hotline Desk
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {emergencyContacts.map((c, i) => (
              <div key={i} style={{ borderBottom: '1px solid var(--border-soft)', paddingBottom: '8px', fontSize: '13px' }}>
                <span style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, display: 'block', color: 'var(--ink)' }}>{c.name}</span>
                <span style={{ fontSize: '11px', color: 'var(--ink-soft)', display: 'block', marginTop: '2px' }}>{c.role}</span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent)', display: 'block', marginTop: '4px', fontWeight: 700 }}>{c.phone}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Safety override action */}
        <div style={{
          background: 'var(--surface-panel)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--rounded-md)',
          padding: '24px',
          boxSizing: 'border-box'
        }}>
          <h4 style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '13px',
            fontWeight: 700,
            letterSpacing: '2px',
            textTransform: 'uppercase',
            color: 'var(--accent)',
            margin: '0 0 8px 0'
          }}>
            Kavach Emergency Override
          </h4>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: '13px',
            color: 'var(--ink-soft)',
            margin: '0 0 16px 0',
            lineHeight: '1.4'
          }}>
            Broadcasting this signal overrides loop-holding states and issues absolute speed restrictions (15km/h) to all locomotives.
          </p>
          <button 
            onClick={handleEmergencyOverride} 
            className="btn-primary" 
            style={{ 
              width: '100%',
              height: '36px',
              fontSize: '12px',
              fontWeight: 700,
              letterSpacing: '2px',
              textTransform: 'uppercase'
            }}
          >
            {overrideActive ? 'CANCEL EBS BROADCAST' : 'BROADCAST EMERGENCY SIGNAL (EBS)'}
          </button>
        </div>
      </div>

      {/* Feature 2: Report Safety Anomaly Form & Live Incidents log */}
      <div style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {feedbackMsg && (
          <div style={{
            padding: '10px 14px',
            borderRadius: 'var(--rounded-sm)',
            background: feedbackMsg.type === 'success' ? 'rgba(76, 175, 80, 0.15)' : 'var(--accent-subtle)',
            border: `1px solid ${feedbackMsg.type === 'success' ? 'rgba(76, 175, 80, 0.3)' : 'var(--border-accent)'}`,
            fontSize: '13px',
            fontFamily: "'Inter', sans-serif",
            color: feedbackMsg.type === 'success' ? 'var(--status-ok)' : 'var(--accent)',
            lineHeight: '1.4'
          }}>
            <strong>{feedbackMsg.type === 'success' ? 'SUCCESS: ' : 'CRITICAL WARNING: '}</strong>
            {feedbackMsg.text}
          </div>
        )}

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '24px',
          padding: '24px',
          background: 'var(--surface-panel)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--rounded-md)',
          boxSizing: 'border-box'
        }}>
          {/* Anomaly reporting form */}
          <div>
            <h4 style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '16px',
              fontWeight: 600,
              color: 'var(--ink)',
              margin: '0 0 15px 0'
            }}>
              Report Blockage / Anomaly
            </h4>
            <form onSubmit={handleReportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
              <div>
                <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Corridor Section</label>
                <select 
                  value={report.section} 
                  onChange={e => setReport({...report, section: e.target.value})}
                  style={{
                    width: '100%',
                    background: 'var(--surface-input)',
                    color: 'var(--ink)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--rounded-sm)',
                    padding: '8px 12px',
                    height: '36px',
                    fontSize: '13px',
                    fontFamily: "'JetBrains Mono', monospace",
                    outline: 'none',
                    boxSizing: 'border-box',
                    cursor: 'pointer'
                  }}
                >
                  <option value="DLI-GZB">Delhi - Ghaziabad (DLI-GZB)</option>
                  <option value="GZB-ALJN">Ghaziabad - Aligarh (GZB-ALJN)</option>
                  <option value="ALJN-CNB">Aligarh - Kanpur (ALJN-CNB)</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Type</label>
                  <select 
                    value={report.anomalyType} 
                    onChange={e => setReport({...report, anomalyType: e.target.value})}
                    style={{
                      width: '100%',
                      background: 'var(--surface-input)',
                      color: 'var(--ink)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--rounded-sm)',
                      padding: '8px 12px',
                      height: '36px',
                      fontSize: '13px',
                      fontFamily: "'JetBrains Mono', monospace",
                      outline: 'none',
                      boxSizing: 'border-box',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="SIGNAL_FAULT">Interlocking Interlocking Fault</option>
                    <option value="KAVACH_OBU_FAILURE">Kavach OBU failure</option>
                    <option value="TRACK_FRACTURE">Track Fracture</option>
                    <option value="WEATHER_FOG">Heavy Fog Warning</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Severity</label>
                  <select 
                    value={report.severity} 
                    onChange={e => setReport({...report, severity: e.target.value})}
                    style={{
                      width: '100%',
                      background: 'var(--surface-input)',
                      color: 'var(--ink)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--rounded-sm)',
                      padding: '8px 12px',
                      height: '36px',
                      fontSize: '13px',
                      fontFamily: "'JetBrains Mono', monospace",
                      outline: 'none',
                      boxSizing: 'border-box',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Details</label>
                <textarea 
                  rows="2" 
                  value={report.details} 
                  onChange={e => setReport({...report, details: e.target.value})}
                  placeholder="relays warnings..."
                  required
                  style={{
                    width: '100%',
                    background: 'var(--surface-input)',
                    color: 'var(--ink)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--rounded-sm)',
                    padding: '8px 12px',
                    fontSize: '13px',
                    fontFamily: "'Inter', sans-serif",
                    outline: 'none',
                    resize: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <button type="submit" className="btn-primary" style={{ width: '100%', height: '36px', fontSize: '12px', marginTop: '4px' }}>
                Submit Incident Report
              </button>
            </form>
          </div>

          {/* Incident board */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <h4 style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '16px',
              fontWeight: 600,
              color: 'var(--ink)',
              margin: '0 0 15px 0'
            }}>
              Live Incident Board
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', maxHeight: '220px', flexGrow: 1 }}>
              {reportedIncidents.map(inc => (
                <div key={inc.id} style={{
                  background: 'var(--surface-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-xs)',
                  padding: '10px 12px',
                  fontSize: '11px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <span style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, color: 'var(--ink)', display: 'block', fontSize: '13px' }}>
                      {inc.id} · {inc.section}
                    </span>
                    <span style={{ color: 'var(--ink-soft)', display: 'block', marginTop: '2px' }}>
                      Type: {inc.type} · Sev: <strong style={{ color: inc.severity === 'CRITICAL' ? 'var(--accent)' : 'var(--status-warn)' }}>{inc.severity}</strong>
                    </span>
                  </div>
                  <span className={`badge-status ${getStatusBadgeClass(inc.status)}`}>
                    {inc.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Feature 3: Speed limit locking & Live Diagnostics Monitor */}
      <div style={{
        gridColumn: 'span 6',
        minHeight: '320px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        boxSizing: 'border-box'
      }}>
        <h4 style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: 'var(--accent)',
          borderBottom: '1px solid var(--border-soft)',
          paddingBottom: '8px',
          margin: '0 0 15px 0'
        }}>
          Speed Limit Locks & Diagnostic Ping
        </h4>

        {/* Speed Lock Form */}
        <form onSubmit={handleSetSpeedLimit} style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px', marginBottom: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Segment Section</label>
              <select 
                value={selectedSection} 
                onChange={e => setSelectedSection(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--surface-input)',
                  color: 'var(--ink)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-sm)',
                  padding: '8px 12px',
                  height: '36px',
                  fontSize: '13px',
                  fontFamily: "'JetBrains Mono', monospace",
                  outline: 'none',
                  boxSizing: 'border-box',
                  cursor: 'pointer'
                }}
              >
                <option value="DLI-GZB">Delhi - Ghaziabad (DLI-GZB)</option>
                <option value="GZB-ALJN">Ghaziabad - Aligarh (GZB-ALJN)</option>
                <option value="ALJN-CNB">Aligarh - Kanpur (ALJN-CNB)</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Speed Limit (km/h)</label>
              <input 
                type="number" 
                value={activeSpeedLimit}
                onChange={e => setActiveSpeedLimit(parseInt(e.target.value) || 0)}
                style={{
                  width: '100%',
                  background: 'var(--surface-input)',
                  color: 'var(--ink)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-sm)',
                  padding: '8px 12px',
                  height: '36px',
                  fontSize: '13px',
                  fontFamily: "'JetBrains Mono', monospace",
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          </div>
          <button type="submit" className="btn-secondary" style={{ width: '100%', height: '36px', fontSize: '12px' }}>
            Override Speed Lock Parameters
          </button>
        </form>

        {/* Ping diagnostics */}
        <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>
          Connection Latency Diagnostics
        </span>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px' }}>
          {[
            { label: "SQLITE DB", value: pingStates.db },
            { label: "API SRV", value: pingStates.api },
            { label: "XGB MODEL", value: pingStates.mlModel },
            { label: "TELE WS", value: pingStates.wsLink }
          ].map(ping => (
            <div key={ping.label} style={{
              background: 'var(--surface-elevated)',
              padding: '8px',
              borderRadius: 'var(--rounded-xs)',
              textAlign: 'center',
              border: '1px solid var(--border)'
            }}>
              <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, color: 'var(--ink-muted)', display: 'block' }}>{ping.label}</span>
              <span style={{ fontSize: '13px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: 'var(--accent)', display: 'block', marginTop: '4px' }}>{ping.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Feature 4: Kavach OBU Troubleshooter Wizard */}
      <div style={{
        gridColumn: 'span 6',
        minHeight: '320px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        boxSizing: 'border-box'
      }}>
        <h4 style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: 'var(--accent)',
          borderBottom: '1px solid var(--border-soft)',
          paddingBottom: '8px',
          margin: '0 0 15px 0'
        }}>
          Kavach OBU Troubleshooter
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1, justifyContent: 'center' }}>
          <span style={{ fontSize: '11px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: '4px' }}>Locomotive Hardware Self-Test Checklist:</span>
          {[
            { key: 'gps', label: "GPS Receiver lock synchrony" },
            { key: 'power', label: "Power Relay board validation" },
            { key: 'radio', label: "RF VHF Radio link channel sync" }
          ].map(chk => (
            <label key={chk.key} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '13px',
              fontFamily: "'Inter', sans-serif",
              background: 'var(--surface-elevated)',
              border: '1px solid var(--border)',
              padding: '8px 12px',
              borderRadius: 'var(--rounded-xs)',
              cursor: 'pointer'
            }}>
              <span style={{ color: 'var(--ink)' }}>{chk.label}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: 'bold', color: diagnosticsChecklist[chk.key] ? 'var(--status-ok)' : 'var(--accent)' }}>
                  {diagnosticsChecklist[chk.key] ? 'ONLINE' : 'FAILED'}
                </span>
                <input 
                  type="checkbox" 
                  checked={diagnosticsChecklist[chk.key]} 
                  onChange={() => setDiagnosticsChecklist({...diagnosticsChecklist, [chk.key]: !diagnosticsChecklist[chk.key]})}
                  style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
                />
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Feature 5: Disaster Management Accordion Reference */}
      <div style={{
        gridColumn: 'span 12',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        marginBottom: '16px'
      }}>
        <h4 style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: 'var(--accent)',
          borderBottom: '1px solid var(--border-soft)',
          paddingBottom: '8px',
          margin: '0 0 15px 0'
        }}>
          Disaster Management & Standard Procedures Index
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[
            { id: 1, title: "Procedure A: Emergency Track Fracture / Obstruction", desc: "1. Broadcast EBS immediate halt. 2. Dispatch relief van from closest station. 3. Notify downstream interlocking blocks to hold signals. 4. Initiate safety checklist." },
            { id: 2, title: "Procedure B: Electronic Interlocking Code Relays Failure", desc: "1. Switch section to manual block authority. 2. Max speeds locked to 30km/h on visual check. 3. Issue written Line Clear commands to locos." },
            { id: 3, title: "Procedure C: Kavach OBU Signal Telemetry Loss", desc: "1. Log telemetry fault details in Ledger. 2. Verify signal overlap via NTES cache. 3. Alert driver to proceed under manual signaling separation." }
          ].map(proc => (
            <div key={proc.id} style={{ border: '1px solid var(--border)', borderRadius: 'var(--rounded-xs)', overflow: 'hidden' }}>
              <button 
                onClick={() => setActiveAccordion(activeAccordion === proc.id ? null : proc.id)}
                style={{
                  width: '100%', 
                  background: 'var(--surface-elevated)', 
                  border: 'none', 
                  color: 'var(--ink)', 
                  textAlign: 'left', 
                  padding: '12px 18px', 
                  fontSize: '13px', 
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 600, 
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  outline: 'none'
                }}
              >
                <span>{proc.title}</span>
                <span style={{ color: 'var(--ink-soft)' }}>{activeAccordion === proc.id ? '▼' : '►'}</span>
              </button>
              {activeAccordion === proc.id && (
                <div style={{
                  background: 'var(--surface-input)',
                  padding: '12px 18px',
                  fontSize: '13px',
                  fontFamily: "'Inter', sans-serif",
                  color: 'var(--ink-soft)',
                  borderTop: '1px solid var(--border-soft)',
                  lineHeight: '1.5'
                }}>
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
