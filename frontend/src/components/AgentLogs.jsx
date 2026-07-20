import { useState, useEffect, useRef } from 'react';

export default function AgentLogs({ logs }) {
  const [activeFilter, setActiveFilter] = useState('ALL');
  const terminalEndRef = useRef(null);

  // Automatically scroll to bottom of logs on update
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, activeFilter]);

  const agentsList = [
    { label: 'ALL', value: 'ALL' },
    { label: 'Monitor', value: 'MonitorAgent' },
    { label: 'Conflict', value: 'ConflictDetector' },
    { label: 'Cascade', value: 'CascadePredictor' },
    { label: 'Dispatch', value: 'DispatchAgent' },
    { label: 'Notify', value: 'NotificationAgent' },
    { label: 'Audit', value: 'AuditAgent' }
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
        return { color: 'var(--accent)', prefix: `[${a.label}]` };
      }
    }
    return { color: 'var(--ink-soft)', prefix: '[System]' };
  };

  return (
    <div style={{
      gridColumn: 'span 12',
      minHeight: '340px',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px',
      background: 'var(--surface-panel)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--rounded-md)'
    }}>
      <div style={{ marginBottom: '15px' }}>
        <h3 style={{ fontFamily: "'Inter', sans-serif", fontSize: '16px', fontWeight: 600, color: 'var(--ink)', margin: 0 }}>
          Operations Decision Logs
        </h3>
        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', color: 'var(--ink-soft)', margin: '4px 0 0 0' }}>
          System Diagnostics & Logs
        </p>
      </div>

      {/* Filter Badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '15px' }}>
        {agentsList.map(a => (
          <button
            key={a.value}
            onClick={() => setActiveFilter(a.value)}
            style={{
              background: activeFilter === a.value ? 'var(--accent)' : 'transparent',
              border: 'none',
              borderRadius: 'var(--rounded-xs)',
              padding: '0 14px',
              height: '32px',
              fontSize: '12px',
              fontWeight: 700,
              fontFamily: "'Inter', sans-serif",
              letterSpacing: '2px',
              textTransform: 'uppercase',
              cursor: 'pointer',
              color: activeFilter === a.value ? 'var(--ink-on-red)' : 'var(--ink-soft)',
              outline: 'none'
            }}
          >
            {a.label}
          </button>
        ))}
      </div>

      {/* Terminal logs body */}
      <div style={{
        background: 'var(--surface-input)',
        borderRadius: 'var(--rounded-sm)',
        padding: '16px',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '13px',
        lineHeight: '1.7',
        flexGrow: 1,
        overflowY: 'auto',
        maxHeight: '190px',
        border: '1px solid var(--border)'
      }}>
        {filteredLogs.length === 0 ? (
          <div style={{ color: 'var(--ink-muted)', fontStyle: 'italic', textAlign: 'center', marginTop: '20px' }}>
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
                <span style={{ color: 'var(--ink)' }}>{cleanText}</span>
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
