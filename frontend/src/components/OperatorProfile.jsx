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
    name: 'Controller North — Gaurav Kumar Nayak',
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

  return (
    <div className="bento-grid" style={{ padding: '20px' }}>
      
      {/* Feature 1: Operator Badge and QR Code */}
      <div className="glass-card" style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px' }}>
        <div style={{
          width: '70px',
          height: '70px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.6rem',
          fontWeight: 800,
          color: 'white',
          boxShadow: 'var(--shadow-neon-cyan)',
          marginBottom: '15px'
        }}>
          GN
        </div>

        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '4px' }}>{operatorInfo.name}</h3>
        <p style={{ fontSize: '0.75rem', color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 600, marginBottom: '15px' }}>
          {operatorInfo.role}
        </p>

        {/* SVG QR Code Simulation */}
        <div style={{ background: 'white', padding: '8px', borderRadius: '6px', marginBottom: '15px', display: 'inline-block' }}>
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
            style={{ width: '100%', padding: '8px', fontSize: '0.75rem' }}
          >
            Generate Handover Report
          </button>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn-secondary" style={{ flex: 1, padding: '6px', fontSize: '0.7rem' }} onClick={() => alert("Terminal session locked.")}>
              Lock Terminal
            </button>
            <button className="btn-secondary" style={{ flex: 1, padding: '6px', fontSize: '0.7rem' }} onClick={() => alert("Shift duration extended by 2 hours.")}>
              Extend Session
            </button>
          </div>
        </div>
      </div>

      {/* Feature 2: Cryptographic Identity & Key Display + Authority Badges */}
      <div className="glass-card" style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
          Cryptographic Identity Credentials
        </h4>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>ECDSA Public Signature Key (secp256k1)</span>
            <button 
              onClick={copyPublicKey}
              style={{ background: 'transparent', border: 'none', color: 'var(--color-primary)', fontSize: '0.65rem', cursor: 'pointer', outline: 'none' }}
            >
              {copied ? 'Copied' : 'Copy Key'}
            </button>
          </div>
          <div style={{
            background: 'var(--bg-terminal)',
            borderRadius: '6px',
            padding: '10px 14px',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.62rem',
            color: 'var(--color-text-muted)',
            wordBreak: 'break-all',
            border: '1px solid var(--border-color)',
            lineHeight: '1.4'
          }}>
            {operatorInfo.credentials.ecdsaPublicKey}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '15px', fontSize: '0.75rem' }}>
          <div>
            <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '0.65rem' }}>User Authority Level</span>
            <span style={{ fontWeight: 700, display: 'block', marginTop: '2px', color: 'white' }}>{operatorInfo.credentials.clearanceLevel}</span>
          </div>
          <div>
            <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '0.65rem' }}>Hardware Token Status</span>
            <span style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px', color: 'var(--color-accent)' }}>
              <span className="led-indicator active" style={{ width: '6px', height: '6px' }}></span> {tokenStatus}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '0.65rem' }}>Token Diagnostic</span>
            <button 
              onClick={handleTestToken}
              style={{ background: 'transparent', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'white', padding: '2px 8px', fontSize: '0.6rem', cursor: 'pointer', marginTop: '2px' }}
            >
              {tokenStatus === 'TESTING' ? 'Testing...' : 'Test Sync'}
            </button>
          </div>
        </div>

        {/* Feature: Authority Level Badge indicators */}
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
          <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
            Active Controller Safety Authorizations
          </span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {['EXECUTE_DIVERSION', 'SPEED_LOCK_OVERRIDE', 'EMERGENCY_BRAKE_BROADCAST', 'KAVACH_PARAM_LOCK'].map(auth => (
              <span key={auth} style={{
                fontSize: '0.6rem',
                padding: '3px 8px',
                borderRadius: '4px',
                background: 'rgba(0, 240, 255, 0.05)',
                color: 'var(--color-primary)',
                border: '1px solid rgba(0, 240, 255, 0.15)',
                fontWeight: 'bold'
              }}>
                {auth}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Feature 3: Shift Tasks/Checklist (Interactive TODO list) */}
      <div className="glass-card" style={{ gridColumn: 'span 5', minHeight: '280px', display: 'flex', flexDirection: 'column' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '12px' }}>
          Shift Operations Tasks
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1, justifyContent: 'center' }}>
          {tasks.map(t => (
            <label 
              key={t.id} 
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                fontSize: '0.75rem',
                background: 'rgba(255,255,255,0.01)',
                border: '1px solid var(--border-color)',
                padding: '8px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                textDecoration: t.checked ? 'line-through' : 'none',
                color: t.checked ? 'var(--color-text-dark)' : 'var(--color-text-main)'
              }}
            >
              <input 
                type="checkbox" 
                checked={t.checked} 
                onChange={() => handleTaskToggle(t.id)}
                style={{ accentColor: 'var(--color-primary)' }}
              />
              {t.text}
            </label>
          ))}
        </div>
      </div>

      {/* Feature 4: Operator Performance Dials */}
      <div className="glass-card" style={{ gridColumn: 'span 7', minHeight: '280px', display: 'flex', flexDirection: 'column' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '15px' }}>
          Performance Metrics Dashboard
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', flexGrow: 1, alignItems: 'center' }}>
          {/* Handled Alerts count */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'rgba(0, 240, 255, 0.05)', border: '1px solid var(--color-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--color-primary)', fontSize: '1rem' }}>
              {perfStats.handled_alerts_count}
            </div>
            <div>
              <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block' }}>ALERTERS SOLVED</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'white' }}>Variance Within Limit</span>
            </div>
          </div>

          {/* Reaction time */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'rgba(168, 85, 247, 0.05)', border: '1px solid var(--color-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--color-secondary)', fontSize: '1rem' }}>
              {perfStats.average_reaction_time_seconds}s
            </div>
            <div>
              <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block' }}>REACTION LATENCY</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'white' }}>Optimal Threshold</span>
            </div>
          </div>

          {/* Compliance rate */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'rgba(34, 197, 94, 0.05)', border: '1px solid var(--color-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--color-accent)', fontSize: '1rem' }}>
              {Math.round(perfStats.safety_compliance_rate)}%
            </div>
            <div>
              <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block' }}>SAFETY COMPLIANCE</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'white' }}>Perfect Rating</span>
            </div>
          </div>

          {/* Handled overrides */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: 'rgba(234, 179, 8, 0.05)', border: '1px solid var(--color-warning)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: 'var(--color-warning)', fontSize: '1.1rem' }}>
              {perfStats.handled_overrides_count || 8}
            </div>
            <div>
              <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block' }}>DISPATCH OVERRIDES</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'white' }}>Audited Decisional Logs</span>
            </div>
          </div>
        </div>
      </div>

      {/* Feature 5: Assigned Sector list and Shift handover logs */}
      <div className="glass-card" style={{ gridColumn: 'span 12' }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '15px' }}>
          Assigned Railway Sectors & Active Blocks
        </h4>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
          {operatorInfo.corridors.map((c, i) => (
            <div key={i} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'rgba(255, 255, 255, 0.01)',
              padding: '12px 18px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)'
            }}>
              <div>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, display: 'block', color: 'white' }}>{c.name}</span>
                <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>Code: {c.code} · Blocks: {c.blocks}</span>
              </div>
              <span style={{
                fontSize: '0.65rem',
                padding: '3px 8px',
                borderRadius: '4px',
                background: c.system.includes('ACTIVE') ? 'rgba(34, 197, 94, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                color: c.system.includes('ACTIVE') ? 'var(--color-accent)' : 'var(--color-text-muted)',
                border: `1px solid ${c.system.includes('ACTIVE') ? 'rgba(34, 197, 94, 0.2)' : 'var(--border-color)'}`,
                fontWeight: 'bold'
              }}>
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
          background: 'rgba(0,0,0,0.85)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(8px)'
        }}>
          <div className="glass-card" style={{ maxWidth: '500px', width: '90%', padding: '24px', border: '1px solid var(--color-primary)' }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--color-primary)', marginBottom: '15px' }}>Shift Handover Summary Report</h3>
            
            <div style={{ background: 'var(--bg-terminal)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '15px', fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--color-text-muted)', display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '250px', overflowY: 'auto' }}>
              <div><strong>OPERATOR ID:</strong> {operatorInfo.credentials.userId}</div>
              <div><strong>DUTY SECTOR:</strong> Sector North Control Desk</div>
              <div><strong>SHIFT LENGTH:</strong> {perfStats.active_duty_hours} Hours</div>
              <div><strong>SOLVED ALERTERS:</strong> {perfStats.handled_alerts_count}</div>
              <div><strong>DISPATCH OVERRIDES:</strong> {perfStats.handled_overrides_count}</div>
              <div><strong>COMPLIANCE SCORE:</strong> {perfStats.safety_compliance_rate}%</div>
              
              <div style={{ borderTop: '1px dashed var(--border-color)', paddingTop: '8px', color: 'var(--color-accent)', fontSize: '0.62rem', wordBreak: 'break-all' }}>
                <strong>ECDSA SHA-256 SIGNATURE:</strong>
                <br />
                0x04a89d3c5f21ea1893ef2d31c4fbe567a18f9e2b10a9c8
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
              <button 
                className="btn-primary" 
                onClick={() => {
                  alert("Handover report cryptographically sealed and dispatched to Chief Operations Manager.");
                  setShowHandover(false);
                }}
                style={{ flexGrow: 1 }}
              >
                Sign & Send Handover
              </button>
              <button 
                className="btn-secondary" 
                onClick={() => setShowHandover(false)}
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
