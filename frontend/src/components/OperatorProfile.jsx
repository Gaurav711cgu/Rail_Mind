import React, { useState, useEffect } from 'react';

export default function OperatorProfile() {
  const [copied, setCopied] = useState(false);
  const [showHandover, setShowHandover] = useState(false);
  const [tokenStatus, setTokenStatus] = useState('SYNCED');
  
  // Shift Checklist state synced to localStorage
  const [tasks, setTasks] = useState(() => {
    const saved = localStorage.getItem('railmind_shift_tasks');
    return saved ? JSON.parse(saved) : [
      { id: 1, text: "Verify exit interlocking status codes", checked: true },
      { id: 2, text: "Authorize pending dispatch recommendations", checked: false },
      { id: 3, text: "Check meteorological fog restrictions", checked: false },
      { id: 4, text: "Perform SHA-256 ledger integrity validation", checked: true },
      { id: 5, text: "Seal chronological shift transaction log", checked: false }
    ];
  });

  const [perfStats, setPerfStats] = useState({
    handled_alerts_count: 42,
    variance_score: 98.4,
    average_reaction_time_seconds: 12.8,
    safety_compliance_rate: 100.0,
    authority_status: "L3_SUPERVISOR_ACTIVE",
    handled_overrides_count: 8,
    active_duty_hours: 3.5,
    system_cohesion_index: 95.8,
    kavach_override_count: 1
  });

  const operatorInfo = {
    name: 'Controller Gaurav Kumar Nayak',
    role: 'Interlocking Section Dispatcher',
    status: 'ACTIVE_DUTY',
    dutyStation: 'New Delhi (NDLS) Sector North Control Grid',
    credentials: {
      userId: 'RM-OP-71109',
      clearanceLevel: 'LEVEL_3 (CORRIDOR_SUPERVISOR)',
      ecdsaPublicKey: '04a89d3c5f21ea1893ef2d31c4fbe567a18f9e2b10a9c80d52b14589d32aef78cc9d2af0e5138a0f2142e887d1bc712f67ac128b7e289d1a38f32a2c5a2c',
      authMethod: 'ECDSA SECP256K1 HW_TOKEN',
      sessionStarted: '15:30:12'
    },
    corridors: [
      { name: 'Delhi - Ghaziabad Segment', code: 'DLI-GZB', blocks: 14, system: 'KAVACH_ACTIVE' },
      { name: 'Ghaziabad - Aligarh Segment', code: 'GZB-ALJN', blocks: 32, system: 'ABS_BLOCK_SIGNAL' },
      { name: 'Aligarh - Kanpur Central Corridor', code: 'ALJN-CNB', blocks: 64, system: 'KAVACH_PENDING' }
    ]
  };

  // Fetch operator performance metrics from backend
  useEffect(() => {
    const fetchPerf = async () => {
      try {
        const res = await fetch('/api/v1/auth/operator-performance');
        if (res.ok) {
          const data = await res.json();
          setPerfStats(data);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchPerf();
  }, []);

  // Save checklist to localStorage
  useEffect(() => {
    localStorage.setItem('railmind_shift_tasks', JSON.stringify(tasks));
  }, [tasks]);

  const handleTaskToggle = (id) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, checked: !t.checked } : t));
  };

  const copyPublicKey = () => {
    navigator.clipboard.writeText(operatorInfo.credentials.ecdsaPublicKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTestToken = () => {
    setTokenStatus('TESTING');
    setTimeout(() => {
      setTokenStatus('SYNCED');
    }, 1000);
  };

  const getSystemBadgeClass = (sys) => {
    if (sys === 'KAVACH_ACTIVE') return 'healthy';
    if (sys === 'ABS_BLOCK_SIGNAL') return 'pending';
    return 'in-review';
  };

  return (
    <div className="bento-grid" style={{ padding: '0 24px' }}>
      
      {/* Feature 1: Operator Badge and QR Code */}
      <div style={{
        gridColumn: 'span 4',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)'
      }}>
        <div style={{
          width: '70px',
          height: '70px',
          borderRadius: 'var(--rounded-md)',
          background: 'var(--surface-elevated)',
          border: '1px solid var(--border-accent)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
          fontWeight: 700,
          color: 'var(--accent)',
          marginBottom: '15px'
        }}>
          GN
        </div>

        <h3 style={{ fontFamily: "'Inter', sans-serif", fontSize: '16px', fontWeight: 600, color: 'var(--ink)', margin: '0 0 4px 0' }}>
          {operatorInfo.name}
        </h3>
        <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 700, margin: '0 0 15px 0' }}>
          {operatorInfo.role}
        </p>

        {/* SVG QR Code Simulation */}
        <div style={{ background: 'white', padding: '8px', borderRadius: 'var(--rounded-xs)', marginBottom: '15px', display: 'inline-block' }}>
          <svg width="80" height="80" viewBox="0 0 100 100">
            <rect x="0" y="0" width="100" height="100" fill="white" />
            <rect x="10" y="10" width="25" height="25" fill="black" />
            <rect x="15" y="15" width="15" height="15" fill="white" />
            <rect x="65" y="10" width="25" height="25" fill="black" />
            <rect x="70" y="15" width="15" height="15" fill="white" />
            <rect x="10" y="65" width="25" height="25" fill="black" />
            <rect x="15" y="70" width="15" height="15" fill="white" />
            <rect x="45" y="45" width="15" height="15" fill="black" />
            <rect x="70" y="70" width="20" height="20" fill="black" />
            <rect x="45" y="75" width="10" height="10" fill="black" />
          </svg>
        </div>

        {/* Session Controls */}
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px', marginTop: 'auto' }}>
          <button 
            className="btn-primary" 
            onClick={() => setShowHandover(true)}
            style={{ width: '100%', height: '36px', fontSize: '12px' }}
          >
            Generate Handover Report
          </button>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn-secondary" style={{ flex: 1, height: '36px', fontSize: '12px' }} onClick={() => alert("Terminal session locked.")}>
              Lock
            </button>
            <button className="btn-secondary" style={{ flex: 1, height: '36px', fontSize: '12px' }} onClick={() => alert("Shift duration extended by 2 hours.")}>
              Extend
            </button>
          </div>
        </div>
      </div>

      {/* Feature 2: Cryptographic Identity & Key Display + Authority Badges */}
      <div style={{
        gridColumn: 'span 8',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)'
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
          margin: 0
        }}>
          Identity Credentials
        </h4>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '11px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-soft)' }}>
              ECDSA Public Signature Key (secp256k1)
            </span>
            <button 
              onClick={copyPublicKey}
              style={{ background: 'transparent', border: 'none', color: 'var(--accent)', fontSize: '11px', fontWeight: 600, cursor: 'pointer', outline: 'none' }}
            >
              {copied ? 'Copied' : 'Copy Key'}
            </button>
          </div>
          <div style={{
            background: 'var(--surface-input)',
            borderRadius: 'var(--rounded-sm)',
            padding: '12px',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            color: 'var(--ink-soft)',
            wordBreak: 'break-all',
            border: '1px solid var(--border)',
            lineHeight: '1.5'
          }}>
            {operatorInfo.credentials.ecdsaPublicKey}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '16px' }}>
          <div>
            <span style={{ color: 'var(--ink-muted)', display: 'block', fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Clearance Level
            </span>
            <span style={{ fontWeight: 600, fontSize: '13px', display: 'block', marginTop: '4px', color: 'var(--ink)' }}>
              {operatorInfo.credentials.clearanceLevel}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--ink-muted)', display: 'block', fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Token Status
            </span>
            <span style={{ fontWeight: 600, fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px', color: 'var(--accent)' }}>
              <span className="led-indicator active" style={{ width: '6px', height: '6px' }}></span> {tokenStatus}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--ink-muted)', display: 'block', fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '4px' }}>
              Diagnostics
            </span>
            <button 
              onClick={handleTestToken}
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: 'var(--rounded-sm)',
                color: 'var(--ink)',
                padding: '4px 10px',
                fontSize: '11px',
                fontFamily: "'Inter', sans-serif",
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              {tokenStatus === 'TESTING' ? 'Testing...' : 'Test Sync'}
            </button>
          </div>
        </div>

        {/* Feature: Authority Level Badge indicators */}
        <div style={{ borderTop: '1px solid var(--border-soft)', paddingTop: '16px' }}>
          <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>
            Active controller safety authorizations
          </span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {['EXECUTE_DIVERSION', 'SPEED_LOCK_OVERRIDE', 'EMERGENCY_BRAKE_BROADCAST', 'KAVACH_PARAM_LOCK'].map(auth => (
              <span key={auth} className="badge-status pending">
                {auth}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Feature 3: Shift Tasks/Checklist (Interactive TODO list) */}
      <div style={{
        gridColumn: 'span 5',
        minHeight: '280px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)'
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
          Shift Tasks Checklist
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1, justifyContent: 'center' }}>
          {tasks.map(t => (
            <label 
              key={t.id} 
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                fontSize: '13px',
                fontFamily: "'Inter', sans-serif",
                background: 'var(--surface-elevated)',
                border: '1px solid var(--border)',
                padding: '8px 12px',
                borderRadius: 'var(--rounded-xs)',
                cursor: 'pointer',
                textDecoration: t.checked ? 'line-through' : 'none',
                color: t.checked ? 'var(--ink-muted)' : 'var(--ink)'
              }}
            >
              <input 
                type="checkbox" 
                checked={t.checked} 
                onChange={() => handleTaskToggle(t.id)}
                style={{ accentColor: 'var(--accent)', cursor: 'pointer' }}
              />
              {t.text}
            </label>
          ))}
        </div>
      </div>

      {/* Feature 4: Operator Performance Dials */}
      <div style={{
        gridColumn: 'span 7',
        minHeight: '280px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)'
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
          Performance Metrics
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', flexGrow: 1, alignItems: 'center' }}>
          {/* Handled Alerts count */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', background: 'var(--surface-elevated)', border: '1px solid var(--border)', padding: '12px', borderRadius: 'var(--rounded-xs)' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: 'var(--rounded-xs)', background: 'var(--surface-input)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--accent)', fontSize: '16px', fontFamily: "'JetBrains Mono', monospace" }}>
              {perfStats.handled_alerts_count}
            </div>
            <div>
              <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', display: 'block', textTransform: 'uppercase' }}>ALERTS SOLVED</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)', fontFamily: "'Inter', sans-serif" }}>Variance Nominal</span>
            </div>
          </div>

          {/* Reaction time */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', background: 'var(--surface-elevated)', border: '1px solid var(--border)', padding: '12px', borderRadius: 'var(--rounded-xs)' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: 'var(--rounded-xs)', background: 'var(--surface-input)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--ink)', fontSize: '16px', fontFamily: "'JetBrains Mono', monospace" }}>
              {perfStats.average_reaction_time_seconds}s
            </div>
            <div>
              <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', display: 'block', textTransform: 'uppercase' }}>REACTION LATENCY</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)', fontFamily: "'Inter', sans-serif" }}>Optimal Threshold</span>
            </div>
          </div>

          {/* Compliance rate */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', background: 'var(--surface-elevated)', border: '1px solid var(--border)', padding: '12px', borderRadius: 'var(--rounded-xs)' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: 'var(--rounded-xs)', background: 'var(--surface-input)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--accent)', fontSize: '16px', fontFamily: "'JetBrains Mono', monospace" }}>
              {Math.round(perfStats.safety_compliance_rate)}%
            </div>
            <div>
              <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', display: 'block', textTransform: 'uppercase' }}>SAFETY COMPLIANCE</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)', fontFamily: "'Inter', sans-serif" }}>Perfect Rating</span>
            </div>
          </div>

          {/* Handled overrides */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', background: 'var(--surface-elevated)', border: '1px solid var(--border)', padding: '12px', borderRadius: 'var(--rounded-xs)' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: 'var(--rounded-xs)', background: 'var(--surface-input)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--ink)', fontSize: '16px', fontFamily: "'JetBrains Mono', monospace" }}>
              {perfStats.handled_overrides_count || 8}
            </div>
            <div>
              <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', display: 'block', textTransform: 'uppercase' }}>DISPATCH OVERRIDES</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)', fontFamily: "'Inter', sans-serif" }}>Audited Decisional Logs</span>
            </div>
          </div>
        </div>
      </div>

      {/* Feature 5: Assigned Sector list and Shift handover logs */}
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
          Assigned Railway Sectors & Active Blocks
        </h4>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
          {operatorInfo.corridors.map((c, i) => (
            <div key={i} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'var(--surface-elevated)',
              padding: '12px 18px',
              borderRadius: 'var(--rounded-xs)',
              border: '1px solid var(--border)'
            }}>
              <div>
                <span style={{ fontSize: '13px', fontFamily: "'Inter', sans-serif", fontWeight: 600, display: 'block', color: 'var(--ink)' }}>
                  {c.name}
                </span>
                <span style={{ fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: 'var(--ink-soft)', marginTop: '2px', display: 'block' }}>
                  Code: {c.code} · Blocks: {c.blocks}
                </span>
              </div>
              <span className={`badge-status ${getSystemBadgeClass(c.system)}`}>
                {c.system}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Handover Log Report Overlay Modal */}
      {showHandover && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'rgba(13, 13, 11, 0.95)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            maxWidth: '500px',
            width: '90%',
            padding: '24px',
            background: 'var(--surface-panel)',
            border: '1px solid var(--border-accent)',
            borderRadius: 'var(--rounded-md)',
            boxSizing: 'border-box'
          }}>
            <h3 style={{ fontFamily: "'Inter', sans-serif", fontSize: '16px', fontWeight: 600, color: 'var(--accent)', margin: '0 0 15px 0' }}>
              Shift Handover Summary Report
            </h3>
            
            <div style={{
              background: 'var(--surface-input)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--rounded-sm)',
              padding: '16px',
              fontSize: '11px',
              fontFamily: "'JetBrains Mono', monospace",
              color: 'var(--ink-soft)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              maxHeight: '250px',
              overflowY: 'auto'
            }}>
              <div><strong>OPERATOR ID:</strong> {operatorInfo.credentials.userId}</div>
              <div><strong>DUTY SECTOR:</strong> Sector North Control Desk</div>
              <div><strong>SHIFT LENGTH:</strong> {perfStats.active_duty_hours} Hours</div>
              <div><strong>SOLVED ALERTERS:</strong> {perfStats.handled_alerts_count}</div>
              <div><strong>DISPATCH OVERRIDES:</strong> {perfStats.handled_overrides_count}</div>
              <div><strong>COMPLIANCE SCORE:</strong> {perfStats.safety_compliance_rate}%</div>
              
              <div style={{ borderTop: '1px dashed var(--border)', paddingTop: '8px', color: 'var(--accent)', fontSize: '10px', wordBreak: 'break-all' }}>
                <strong>ECDSA SHA-256 SIGNATURE:</strong>
                <br />
                0x04a89d3c5f21ea1893ef2d31c4fbe567a18f9e2b10a9c8
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
              <button 
                className="btn-primary" 
                onClick={() => {
                  alert("Handover report cryptographically sealed and dispatched to Chief Operations Manager.");
                  setShowHandover(false);
                }}
                style={{ flexGrow: 1, height: '36px', fontSize: '12px' }}
              >
                Sign & Send Handover
              </button>
              <button 
                className="btn-secondary" 
                onClick={() => setShowHandover(false)}
                style={{ height: '36px', fontSize: '12px' }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
