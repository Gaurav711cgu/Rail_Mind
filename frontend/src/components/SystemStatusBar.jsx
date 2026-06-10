import React, { useState, useEffect, useCallback } from 'react';

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
    fetchHealth();
    const interval = setInterval(fetchHealth, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // Derive health status
  const allHealthy = health
    ? (health.agents_healthy === health.agents_total) && health.ml_status === 'operational'
    : false;

  const statusColor = error
    ? '#E31A22'
    : allHealthy
      ? '#22c55e'
      : '#E31A22';

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
    height: '24px',
    zIndex: 200,
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '0 20px',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.58rem',
    letterSpacing: '0.5px',
    color: 'var(--color-text-muted)',
    background: 'rgba(2, 4, 10, 0.92)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    borderTop: '1px solid var(--border-subtle)',
    userSelect: 'none',
  };

  const dotStyle = {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: statusColor,
    boxShadow: `0 0 6px ${statusColor}`,
    flexShrink: 0,
  };

  const labelStyle = {
    color: 'var(--color-text-dark)',
    marginRight: '4px',
    textTransform: 'uppercase',
    fontWeight: 700,
    letterSpacing: '1px',
  };

  const valueStyle = {
    color: 'var(--color-text-label)',
  };

  const separatorStyle = {
    width: '1px',
    height: '10px',
    background: 'var(--border-color)',
    flexShrink: 0,
  };

  return (
    <div style={barStyle}>
      {/* Status dot + label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
        <span style={dotStyle} />
        <span style={{
          fontWeight: 700,
          letterSpacing: '1.5px',
          color: statusColor,
          textTransform: 'uppercase',
          fontSize: '0.56rem',
        }}>
          {statusText}
        </span>
      </div>

      <span style={separatorStyle} />

      {/* Metrics */}
      {health && !error && (
        <>
          <span>
            <span style={labelStyle}>Uptime:</span>
            <span style={valueStyle}>{formatUptime(health.uptime_seconds)}</span>
          </span>

          <span style={separatorStyle} />

          <span>
            <span style={labelStyle}>Requests:</span>
            <span style={valueStyle}>{formatNumber(health.total_requests)}</span>
          </span>

          <span style={separatorStyle} />

          <span>
            <span style={labelStyle}>Latency:</span>
            <span style={valueStyle}>{health.avg_latency_ms != null ? `${health.avg_latency_ms}ms` : '—'}</span>
          </span>

          <span style={separatorStyle} />

          <span>
            <span style={labelStyle}>Agents:</span>
            <span style={{
              ...valueStyle,
              color: health.agents_healthy === health.agents_total
                ? 'var(--color-text-label)'
                : '#E31A22',
            }}>
              {health.agents_healthy ?? '?'}/{health.agents_total ?? '?'}
            </span>
          </span>

          <span style={separatorStyle} />

          <span>
            <span style={labelStyle}>ML:</span>
            <span style={{
              ...valueStyle,
              color: health.ml_status === 'operational' ? 'var(--color-text-label)' : '#E31A22',
            }}>
              {health.ml_model || 'Unknown'}
            </span>
          </span>
        </>
      )}

      {error && (
        <span style={{ color: 'var(--color-text-dark)' }}>
          Unable to reach system health endpoint
        </span>
      )}

      {/* Right-aligned timestamp */}
      <span style={{
        marginLeft: 'auto',
        color: 'var(--color-text-dark)',
        fontSize: '0.52rem',
        flexShrink: 0,
      }}>
        RAILMIND v2.1
      </span>
    </div>
  );
}
