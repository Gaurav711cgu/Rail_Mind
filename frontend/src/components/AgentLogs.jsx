import React, { useState, useEffect, useRef } from 'react';

export default function AgentLogs({ logs }) {
  const [activeFilter, setActiveFilter] = useState('ALL');
  const terminalEndRef = useRef(null);

  // Automatically scroll to bottom of logs on update
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, activeFilter]);

  const agentsList = [
    { label: 'ALL', value: 'ALL', color: 'var(--color-text-main)' },
    { label: 'Monitor', value: 'MonitorAgent', color: 'var(--color-accent)' },
    { label: 'Conflict', value: 'ConflictDetector', color: 'var(--color-warning)' },
    { label: 'Cascade', value: 'CascadePredictor', color: 'var(--color-primary)' },
    { label: 'Dispatch', value: 'DispatchAgent', color: 'var(--color-secondary)' },
    { label: 'Notify', value: 'NotificationAgent', color: '#60A5FA' },
    { label: 'Audit', value: 'AuditAgent', color: '#F472B6' }
  ];

  // Filter logs based on selection
  const filteredLogs = logs.filter(log => {
    if (activeFilter === 'ALL') return true;
    return log.includes(`[${activeFilter}]`);
  });

  // Extract agent color for row prefix styling
  const getLogStyle = (logText) => {
    for (const a of agentsList) {
      if (a.value !== 'ALL' && logText.includes(`[${a.value}]`)) {
        return { color: a.color, prefix: `[${a.label}]` };
      }
    }
    return { color: 'var(--color-text-muted)', prefix: '[System]' };
  };

  return (
    <div className="glass-card" style={{ gridColumn: 'span 5', minHeight: '340px', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ marginBottom: '15px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Autonomous Decision Log Console</h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Explainable AI Agent Execution Telemetries</p>
      </div>

      {/* Filter Badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '15px' }}>
        {agentsList.map(a => (
          <button
            key={a.value}
            onClick={() => setActiveFilter(a.value)}
            style={{
              background: activeFilter === a.value ? 'rgba(255,255,255,0.08)' : 'transparent',
              border: `1px solid ${activeFilter === a.value ? 'var(--color-primary)' : 'var(--border-color)'}`,
              borderRadius: '20px',
              padding: '4px 10px',
              fontSize: '0.7rem',
              fontWeight: 600,
              cursor: 'pointer',
              color: activeFilter === a.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
              transition: 'all 0.2s',
              boxShadow: activeFilter === a.value ? '0 0 8px rgba(0, 240, 255, 0.2)' : 'none'
            }}
          >
            {a.label}
          </button>
        ))}
      </div>

      {/* Terminal logs body */}
      <div style={{
        background: 'var(--bg-terminal)',
        borderRadius: '8px',
        padding: '15px',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '0.75rem',
        flexGrow: 1,
        overflowY: 'auto',
        maxHeight: '190px',
        border: '1px solid var(--border-color)'
      }}>
        {filteredLogs.length === 0 ? (
          <div style={{ color: 'var(--color-text-dark)', fontStyle: 'italic', textAlign: 'center', marginTop: '20px' }}>
            -- No logs matching filter query --
          </div>
        ) : (
          filteredLogs.map((log, index) => {
            const style = getLogStyle(log);
            // Clean prefix from main display text
            const cleanText = log.replace(/\[\w+\]\s*/, '');
            return (
              <div key={index} style={{ marginBottom: '8px', display: 'flex', gap: '8px' }}>
                <span style={{ color: style.color, fontWeight: 'bold' }}>{style.prefix}</span>
                <span style={{ color: '#E2E8F0' }}>{cleanText}</span>
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
