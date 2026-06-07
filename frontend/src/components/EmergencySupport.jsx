import React, { useState } from 'react';

export default function EmergencySupport() {
  const [report, setReport] = useState({
    section: 'DLI-GZB',
    anomalyType: 'SIGNAL_INTERLOCK_FAULT',
    severity: 'MEDIUM',
    details: '',
  });
  
  const [overrideActive, setOverrideActive] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  const emergencyContacts = [
    { name: 'NDLS Section Controller', role: 'Delhi division main office', phone: '+91 11 2334 5678' },
    { name: 'Kanpur Main Operations', role: 'CNB Central Desk', phone: '+91 512 232 4455' },
    { name: 'Ghaziabad Junction Master', role: 'Station Control Room', phone: '+91 120 282 8900' },
    { name: 'Kavach Telemetry Support', role: 'RDSO Signal Lab', phone: '+91 522 245 1200' }
  ];

  const handleReportSubmit = (e) => {
    e.preventDefault();
    setFeedbackMsg({
      type: 'success',
      text: `Anomaly successfully registered under code RM-REP-${Math.floor(Math.random()*100000)}. Cryptographically sealed and queued for Inspector review.`
    });
    setReport({ section: 'DLI-GZB', anomalyType: 'SIGNAL_INTERLOCK_FAULT', severity: 'MEDIUM', details: '' });
  };

  const handleEmergencyOverride = () => {
    setOverrideActive(!overrideActive);
    setFeedbackMsg({
      type: 'warning',
      text: !overrideActive 
        ? 'ALERT: Kavach Emergency Brake Signal (EBS) broadcasted to all locomotives in Sector North! Grid speed locked to 15km/h.' 
        : 'Emergency Override cancelled. Normal signaling parameters restored.'
    });
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '30px', maxWidth: '1200px', margin: '20px auto', padding: '0 20px' }}>
      {/* Emergency Hotline Panel */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div className="glass-card" style={{ borderLeft: '4px solid var(--color-danger)' }}>
          <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '15px', color: 'var(--color-danger)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="led-indicator danger" style={{ width: '8px', height: '8px' }}></span> EMERGENCY RAILWAY CALLS
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {emergencyContacts.map((c, i) => (
              <div key={i} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block' }}>{c.name}</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>{c.role}</span>
                <span style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--color-primary)' }}>{c.phone}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Safety override action */}
        <div className="glass-card" style={{ background: 'rgba(255, 49, 49, 0.02)', borderColor: 'rgba(255, 49, 49, 0.2)' }}>
          <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '10px', color: 'var(--color-danger)' }}>Kavach Emergency Signal Override</h4>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '15px', lineHeight: '1.4' }}>
            Broadcasting this signal overrides loop-holding states and issues absolute speed restrictions to all locomotives operating in the corridor segment.
          </p>
          <button 
            onClick={handleEmergencyOverride} 
            className="btn-primary" 
            style={{ 
              width: '100%', 
              background: overrideActive ? 'var(--color-accent)' : 'var(--color-danger)', 
              color: overrideActive ? '#000000' : '#FFFFFF',
              boxShadow: overrideActive ? 'var(--shadow-neon-green)' : 'var(--shadow-neon-red)'
            }}
          >
            {overrideActive ? 'CANCEL EMERGENCY SIGNAL' : 'BROADCAST EMERGENCY SIGNAL (EBS)'}
          </button>
        </div>
      </div>

      {/* Safety anomaly reporting form */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {feedbackMsg && (
          <div style={{
            padding: '12px 18px',
            borderRadius: '8px',
            background: feedbackMsg.type === 'success' ? 'rgba(57, 255, 20, 0.05)' : 'rgba(255, 49, 49, 0.05)',
            border: `1px solid ${feedbackMsg.type === 'success' ? 'var(--color-accent)' : 'var(--color-danger)'}`,
            fontSize: '0.8rem',
            color: feedbackMsg.type === 'success' ? 'var(--color-accent)' : 'var(--color-danger)',
            lineHeight: '1.4'
          }}>
            <strong>{feedbackMsg.type === 'success' ? 'SUCCESS: ' : 'CRITICAL WARNING: '}</strong>
            {feedbackMsg.text}
          </div>
        )}

        <div className="glass-card">
          <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px', color: 'var(--color-primary)' }}>Report Safety Anomaly / Blockage</h4>
          <form onSubmit={handleReportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
              <div>
                <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Corridor Section</label>
                <select 
                  value={report.section} 
                  onChange={e => setReport({...report, section: e.target.value})}
                  style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
                >
                  <option value="DLI-GZB">Delhi - Ghaziabad (DLI-GZB)</option>
                  <option value="GZB-ALJN">Ghaziabad - Aligarh (GZB-ALJN)</option>
                  <option value="ALJN-CNB">Aligarh - Kanpur (ALJN-CNB)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Anomaly Type</label>
                <select 
                  value={report.anomalyType} 
                  onChange={e => setReport({...report, anomalyType: e.target.value})}
                  style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
                >
                  <option value="SIGNAL_INTERLOCK_FAULT">Interlocking Interlocking Fault</option>
                  <option value="KAVACH_OBU_FAILURE">Kavach OBU Hardware Failure</option>
                  <option value="TRACK_FRACTURE">Track Fracture / Blockage</option>
                  <option value="WEATHER_DISRUPTION">Heavy Fog / Severe Weather</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Severity Level</label>
              <select 
                value={report.severity} 
                onChange={e => setReport({...report, severity: e.target.value})}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
              >
                <option value="LOW">Low (Variance within limits)</option>
                <option value="MEDIUM">Medium (Rescheduling required)</option>
                <option value="CRITICAL">Critical (Line block / Safety hazard)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Incident details & Operator Rationale</label>
              <textarea 
                rows="4" 
                value={report.details} 
                onChange={e => setReport({...report, details: e.target.value})}
                placeholder="Describe details of interlocking warning codes, active locomotives affected, and required line clear times..."
                required
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', outline: 'none', resize: 'vertical', fontFamily: 'inherit' }}
              />
            </div>

            <button type="submit" className="btn-primary" style={{ padding: '10px' }}>
              Submit Incident Report
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
