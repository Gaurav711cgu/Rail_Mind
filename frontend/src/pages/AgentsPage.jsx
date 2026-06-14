import React from 'react';
import useAgentStream from '../hooks/useAgentStream';

// Agent display metadata
const AGENT_META = {
  MonitorAgent:     { icon: '', label: 'Monitor',      desc: 'Z-score anomaly detection on live NTES telemetry' },
  ConflictDetector: { icon: '', label: 'Conflict',     desc: 'NetworkX DiGraph route conflict analysis' },
  CascadePredictor: { icon: '', label: 'Cascade',      desc: 'BFS delay propagation across timetable graph' },
  DispatchAgent:    { icon: '', label: 'Dispatch',     desc: 'Automated dispatch resolution with heuristic fallback' },
  NotificationAgent:{ icon: '', label: 'Notification', desc: 'Passenger advisory & alternate train ranking' },
  AuditAgent:       { icon: '', label: 'Audit',        desc: 'Append-only ECDSA cryptographic audit chain' },
};

function StatusBadge({ status }) {
  const variantMap = {
    healthy:  { badge: 'healthy', led: 'active', text: 'HEALTHY' },
    running:  { badge: 'in-review', led: 'warning', text: 'RUNNING' },
    degraded: { badge: 'failed', led: 'danger', text: 'DEGRADED' },
  };
  const s = variantMap[status] || variantMap.healthy;
  return (
    <span className={`badge-status ${s.badge}`}>
      <span className={`led-indicator ${s.led}`} style={{ width: 6, height: 6 }} />
      {s.text}
    </span>
  );
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 1.0) * 100);
  return (
    <div style={{ marginTop: '8px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '4px'
      }}>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: '10px',
          fontWeight: 500,
          letterSpacing: '1.5px',
          textTransform: 'uppercase',
          color: 'var(--ink-soft)'
        }}>
          Confidence
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '11px',
          fontWeight: 700,
          color: 'var(--ink)'
        }}>
          {pct}%
        </span>
      </div>
      <div style={{ height: '3px', background: 'var(--border)', borderRadius: 0 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', borderRadius: 0 }} />
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

  const summaryStats = [
    { label: 'TOTAL AGENTS', value: agentEntries.length || 6, color: 'var(--ink)' },
    { label: 'HEALTHY',      value: healthyCnt || '—',         color: 'var(--status-ok)' },
    { label: 'RUNNING',      value: runningCnt || 0,           color: 'var(--status-warn)' },
    { label: 'AVG CONFIDENCE',value: avgConf + (hasData ? '%' : ''), color: 'var(--ink)' },
  ];

  return (
    <div style={{ padding: '0 24px' }}>

      {/* ── Top bar ── */}
      <div style={{
        marginBottom: '16px',
        padding: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)'
      }}>
        <div>
          <h3 style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: '16px',
            fontWeight: 600,
            color: 'var(--ink)',
            margin: 0
          }}>
            System Decision Flow Monitor
          </h3>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: '13px',
            color: 'var(--ink-soft)',
            margin: '4px 0 0 0'
          }}>
            Real-time SSE stream · Automated multi-step dispatch verification
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* Connection indicator */}
          <div className={`badge-status ${connected ? 'healthy' : 'failed'}`}>
            <span className={`led-indicator ${connected ? 'active' : 'danger'}`} style={{ width: 6, height: 6 }} />
            <span>
              {connected ? 'LIVE CONNECTION' : 'DISCONNECTED'}
            </span>
          </div>

          {!connected && (
            <button
              className="btn-secondary"
              onClick={reconnect}
              style={{
                height: '32px',
                padding: '0 16px',
                fontSize: '11px'
              }}
            >
              Reconnect
            </button>
          )}
        </div>
      </div>

      {/* ── Summary pills ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '16px' }}>
        {summaryStats.map(p => (
          <div key={p.label} style={{
            background: 'var(--surface-panel)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--rounded-md)',
            padding: '16px',
            textAlign: 'center'
          }}>
            <span style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '10px',
              fontWeight: 500,
              letterSpacing: '1.5px',
              textTransform: 'uppercase',
              color: 'var(--ink-muted)',
              display: 'block',
              marginBottom: '4px'
            }}>
              {p.label}
            </span>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '22px',
              fontWeight: 700,
              color: p.color
            }}>
              {p.value}
            </span>
          </div>
        ))}
      </div>

      {/* ── Agent cards ── */}
      {error && !hasData && (
        <div style={{
          padding: '16px',
          textAlign: 'center',
          background: 'var(--accent-subtle)',
          border: '1px solid var(--border-accent)',
          borderRadius: 'var(--rounded-md)',
          color: 'var(--accent)',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          marginBottom: '16px'
        }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {(hasData ? agentEntries : Object.keys(AGENT_META).map(k => [k, { status: 'healthy', last_run: null, last_confidence: 1.0, last_error: null }])).map(([name, info]) => {
          const meta = AGENT_META[name] || { icon: '', label: name, desc: '' };
          return (
            <div key={name} style={{
              background: 'var(--surface-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--rounded-md)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div>
                    <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '16px', fontWeight: 600, color: 'var(--ink)' }}>
                      {meta.label}
                    </div>
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '11px',
                      color: 'var(--ink-muted)',
                      marginTop: '2px'
                    }}>
                      {name}
                    </div>
                  </div>
                </div>
                <StatusBadge status={info.status} />
              </div>

              {/* Description */}
              <p style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: '13px',
                color: 'var(--ink-soft)',
                lineHeight: '1.4',
                margin: 0
              }}>
                {meta.desc}
              </p>

              {/* Confidence bar */}
              <ConfidenceBar value={info.last_confidence} />

              {/* Last run */}
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '11px',
                color: 'var(--ink-muted)',
                borderTop: '1px solid var(--border-soft)',
                paddingTop: '8px',
                marginTop: '4px'
              }}>
                LAST RUN: {info.last_run
                  ? new Date(info.last_run).toLocaleTimeString()
                  : <span style={{ color: 'var(--ink-muted)', opacity: 0.4 }}>awaiting first cycle</span>
                }
              </div>

              {/* Error */}
              {info.last_error && (
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '11px',
                  color: 'var(--accent)',
                  background: 'var(--accent-subtle)',
                  border: '1px solid var(--border-accent)',
                  borderRadius: 'var(--rounded-xs)',
                  padding: '6px 10px',
                  marginTop: '4px'
                }}>
                  Warning: {info.last_error}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Last updated ── */}
      {lastUpdate && (
        <div style={{
          textAlign: 'center',
          marginTop: '16px',
          fontSize: '11px',
          color: 'var(--ink-muted)',
          fontFamily: "'JetBrains Mono', monospace"
        }}>
          Last event: {new Date(lastUpdate).toLocaleTimeString()} · Polling every 5s
        </div>
      )}
    </div>
  );
}
