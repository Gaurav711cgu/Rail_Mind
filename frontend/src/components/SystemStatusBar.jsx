import { useState, useEffect, useCallback } from 'react';

const POLL_INTERVAL = 10000; // 10 seconds

function formatUptime(seconds) {
  if (!seconds && seconds !== 0) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatNumber(num) {
  if (num == null) return '—';
  return num.toLocaleString();
}

export default function SystemStatusBar() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/health/system');
      if (res.ok) {
        setHealth(await res.json());
        setError(false);
      } else {
        setError(true);
      }
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchHealth();
    const interval = setInterval(fetchHealth, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // Derive health status
  const allHealthy = health
    ? (health.agents_healthy === health.agents_total) && health.ml_status === 'operational'
    : false;

  const statusColor = error
    ? 'var(--status-fail)'
    : allHealthy
      ? 'var(--status-ok)'
      : 'var(--status-fail)';

  const statusText = error
    ? 'OFFLINE'
    : allHealthy
      ? 'SYSTEM OK'
      : 'DEGRADED';

  const barStyle = {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    height: '32px',
    zIndex: 200,
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '0 24px',
    fontFamily: "'JetBrains Mono', 'Courier New', monospace",
    fontSize: '11px',
    fontWeight: 400,
    letterSpacing: '0.5px',
    color: 'var(--ink-muted)',
    background: 'var(--surface-base)',
    borderTop: '1px solid var(--border)',
    userSelect: 'none',
  };

  const dotStyle = {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: statusColor,
    flexShrink: 0,
  };

  const labelStyle = {
    color: 'var(--ink-soft)',
    marginRight: '6px',
    fontWeight: 500,
  };

  const valueStyle = {
    color: 'var(--ink)',
  };

  const pipeStyle = {
    color: 'var(--border)',
    padding: '0 4px',
  };

  return (
    <div style={barStyle}>
      {/* Status dot + label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        <span style={dotStyle} />
        <span style={{
          fontWeight: 700,
          letterSpacing: '1px',
          color: statusColor,
          textTransform: 'uppercase',
          fontSize: '11px',
        }}>
          {statusText}
        </span>
      </div>

      {/* Metrics */}
      {health && !error ? (
        <>
          <span style={pipeStyle}>|</span>
          <span>
            <span style={labelStyle}>UPTIME:</span>
            <span style={valueStyle}>{formatUptime(health.uptime_seconds)}</span>
          </span>

          <span style={pipeStyle}>|</span>
          <span>
            <span style={labelStyle}>REQUESTS:</span>
            <span style={valueStyle}>{formatNumber(health.total_requests)}</span>
          </span>

          <span style={pipeStyle}>|</span>
          <span>
            <span style={labelStyle}>LATENCY:</span>
            <span style={valueStyle}>{health.avg_latency_ms != null ? `${health.avg_latency_ms}ms` : '—'}</span>
          </span>

          <span style={pipeStyle}>|</span>
          <span>
            <span style={labelStyle}>AGENTS:</span>
            <span style={{
              ...valueStyle,
              color: health.agents_healthy === health.agents_total
                ? 'var(--ink)'
                : 'var(--accent)',
            }}>
              {health.agents_healthy ?? '?'}/{health.agents_total ?? '?'}
            </span>
          </span>

          <span style={pipeStyle}>|</span>
          <span>
            <span style={labelStyle}>ML:</span>
            <span style={{
              ...valueStyle,
              color: health.ml_status === 'operational' ? 'var(--ink)' : 'var(--accent)',
            }}>
              {health.ml_model || 'Unknown'}
            </span>
          </span>
        </>
      ) : (
        error && (
          <>
            <span style={pipeStyle}>|</span>
            <span style={{ color: 'var(--accent)' }}>
              UNABLE TO ESTABLISH TELEMETRY LINK
            </span>
          </>
        )
      )}

      {/* Right-aligned timestamp */}
      <span style={{
        marginLeft: 'auto',
        color: 'var(--ink-muted)',
        fontSize: '11px',
        flexShrink: 0,
      }}>
        RAILMIND v2.1
      </span>
    </div>
  );
}
