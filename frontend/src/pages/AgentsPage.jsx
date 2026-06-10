import React from 'react';
import useAgentStream from '../hooks/useAgentStream';

// Agent display metadata
const AGENT_META = {
  MonitorAgent:     { icon: '🔍', label: 'Monitor',      desc: 'Z-score anomaly detection on live NTES telemetry' },
  ConflictDetector: { icon: '⚠️',  label: 'Conflict',     desc: 'NetworkX DiGraph route conflict analysis' },
  CascadePredictor: { icon: '📡', label: 'Cascade',      desc: 'BFS delay propagation across timetable graph' },
  DispatchAgent:    { icon: '🚦', label: 'Dispatch',     desc: 'Automated dispatch resolution with heuristic fallback' },
  NotificationAgent:{ icon: '📢', label: 'Notification', desc: 'Passenger advisory & alternate train ranking' },
  AuditAgent:       { icon: '🔐', label: 'Audit',        desc: 'Append-only ECDSA cryptographic audit chain' },
};

function StatusBadge({ status }) {
  const map = {
    healthy:  { bg: 'rgba(255,255,255,0.08)', border: 'rgba(255,255,255,0.2)', color: '#ffffff', dot: 'active',  text: 'HEALTHY' },
    running:  { bg: 'rgba(255,255,255,0.08)', border: 'rgba(255,255,255,0.2)', color: '#ffffff', dot: 'warning', text: 'RUNNING' },
    degraded: { bg: 'rgba(227,26,34,0.08)',   border: 'rgba(227,26,34,0.3)',   color: 'var(--color-primary)', dot: 'danger',  text: 'DEGRADED' },
  };
  const s = map[status] || map.healthy;
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:5,
      background: s.bg, border:`1px solid ${s.border}`,
      borderRadius:12, padding:'2px 8px', fontSize:'0.6rem',
      fontWeight:700, color: s.color, fontFamily:"'JetBrains Mono', monospace",
      letterSpacing:'1px'
    }}>
      <span className={`led-indicator ${s.dot}`} style={{ width:5, height:5 }} />
      {s.text}
    </span>
  );
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 1.0) * 100);
  const color = 'var(--color-primary)'; // Fixed color: Crimson Red
  return (
    <div style={{ marginTop:6 }}>
      <div style={{ display:'flex', justifyContent:'space-between', fontSize:'0.6rem',
        color:'var(--color-text-muted)', marginBottom:3 }}>
        <span>CONFIDENCE</span>
        <span style={{ color: 'white', fontWeight:700 }}>{pct}%</span>
      </div>
      <div style={{ height:3, background:'rgba(255,255,255,0.05)', borderRadius:2 }}>
        <div style={{ width:`${pct}%`, height:'100%', background:color,
          borderRadius:2, transition:'width 0.5s ease' }} />
      </div>
    </div>
  );
}

export default function AgentsPage() {
  const { agents, connected, lastUpdate, error, reconnect } = useAgentStream();

  const agentEntries = Object.entries(agents);
  const hasData = agentEntries.length > 0;

  // Pipeline summary stats
  const healthyCnt = agentEntries.filter(([,v]) => v.status === 'healthy').length;
  const runningCnt = agentEntries.filter(([,v]) => v.status === 'running').length;
  const avgConf = hasData
    ? (agentEntries.reduce((s,[,v]) => s + (v.last_confidence || 1), 0) / agentEntries.length * 100).toFixed(1)
    : '—';

  return (
    <div style={{ padding:'0 12px' }}>

      {/* ── Top bar ── */}
      <div className="glass-card" style={{ marginBottom:12, padding:'12px 16px',
        display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <div>
          <h3 style={{ fontSize:'1rem', fontWeight:700, marginBottom:2 }}>
            System Decision Flow Monitor
          </h3>
          <p style={{ fontSize:'0.72rem', color:'var(--color-text-muted)' }}>
            Real-time SSE stream · Automated multi-step dispatch verification
          </p>
        </div>

        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          {/* Connection indicator */}
          <div style={{ display:'flex', alignItems:'center', gap:6,
            background:'rgba(255,255,255,0.03)', border:`1px solid ${connected ? 'rgba(255,255,255,0.3)' : 'rgba(227,26,34,0.3)'}`,
            borderRadius:16, padding:'4px 12px' }}>
            <span className={`led-indicator ${connected ? 'active' : 'danger'}`} style={{ width:6, height:6 }} />
            <span style={{ fontSize:'0.6rem', fontWeight:700,
              color: connected ? '#ffffff' : 'var(--color-primary)',
              fontFamily:"'JetBrains Mono', monospace", letterSpacing:'1px' }}>
              {connected ? 'LIVE CONNECTION' : 'DISCONNECTED'}
            </span>
          </div>

          {!connected && (
            <button className="btn-secondary" onClick={reconnect}
              style={{ padding:'4px 10px', fontSize:'0.65rem' }}>
              Reconnect
            </button>
          )}
        </div>
      </div>

      {/* ── Summary pills ── */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8, marginBottom:12 }}>
        {[
          { label:'TOTAL AGENTS', value: agentEntries.length || 6, color:'var(--color-primary)' },
          { label:'HEALTHY',      value: healthyCnt || '—',         color:'#22c55e' },
          { label:'RUNNING',      value: runningCnt || 0,           color:'#3b82f6' },
          { label:'AVG CONFIDENCE',value: avgConf + '%',            color:'var(--color-warning)' },
        ].map(p => (
          <div key={p.label} className="glass-card" style={{ padding:'10px 14px', textAlign:'center' }}>
            <span style={{ fontSize:'0.55rem', color:'var(--color-text-muted)', display:'block',
              textTransform:'uppercase', letterSpacing:'1px' }}>{p.label}</span>
            <span style={{ fontSize:'1.1rem', fontWeight:800, color:p.color }}>{p.value}</span>
          </div>
        ))}
      </div>

      {/* ── Agent cards ── */}
      {error && !hasData && (
        <div className="glass-card" style={{ padding:20, textAlign:'center',
          border:'1px solid rgba(239,68,68,0.3)', color:'var(--color-danger)',
          fontSize:'0.8rem', marginBottom:12 }}>
          {error}
        </div>
      )}

      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:10 }}>
        {(hasData ? agentEntries : Object.keys(AGENT_META).map(k => [k, { status:'healthy', last_run:null, last_confidence:1.0, last_error:null }])).map(([name, info]) => {
          const meta = AGENT_META[name] || { icon:'🤖', label:name, desc:'' };
          return (
            <div key={name} className="glass-card" style={{ padding:'14px 16px', display:'flex', flexDirection:'column', gap:8 }}>
              {/* Header */}
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                  <span style={{ fontSize:'1.1rem' }}>{meta.icon}</span>
                  <div>
                    <div style={{ fontSize:'0.8rem', fontWeight:700 }}>{meta.label}</div>
                    <div style={{ fontSize:'0.6rem', color:'var(--color-text-muted)',
                      fontFamily:"'JetBrains Mono', monospace" }}>{name}</div>
                  </div>
                </div>
                <StatusBadge status={info.status} />
              </div>

              {/* Description */}
              <p style={{ fontSize:'0.65rem', color:'var(--color-text-muted)', lineHeight:1.4 }}>
                {meta.desc}
              </p>

              {/* Confidence bar */}
              <ConfidenceBar value={info.last_confidence} />

              {/* Last run */}
              <div style={{ fontSize:'0.6rem', color:'var(--color-text-dark)',
                fontFamily:"'JetBrains Mono', monospace",
                borderTop:'1px solid var(--border-color)', paddingTop:6, marginTop:2 }}>
                LAST RUN: {info.last_run
                  ? new Date(info.last_run).toLocaleTimeString()
                  : <span style={{ color:'rgba(255,255,255,0.2)' }}>awaiting first cycle</span>
                }
              </div>

              {/* Error */}
              {info.last_error && (
                <div style={{ fontSize:'0.6rem', color:'var(--color-danger)',
                  background:'rgba(239,68,68,0.05)', borderRadius:4, padding:'4px 8px' }}>
                  ⚠ {info.last_error}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Last updated ── */}
      {lastUpdate && (
        <div style={{ textAlign:'center', marginTop:12, fontSize:'0.6rem',
          color:'var(--color-text-dark)', fontFamily:"'JetBrains Mono', monospace" }}>
          Last event: {new Date(lastUpdate).toLocaleTimeString()} · Polling every 5s
        </div>
      )}
    </div>
  );
}
