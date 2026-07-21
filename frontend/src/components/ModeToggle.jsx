import { Activity } from 'lucide-react';

const ModeToggle = ({ isLive, setIsLive, onTriggerLive }) => {
  const handleToggle = () => {
    const nextState = !isLive;
    setIsLive(nextState);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      height: '28px',
      padding: '0 10px',
      borderRadius: '6px',
      border: '1px solid var(--border)',
      background: 'var(--surface-elevated)',
      flexShrink: 0,
    }}>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '1px',
        textTransform: 'uppercase',
        color: !isLive ? 'var(--accent)' : 'var(--ink-muted)',
        whiteSpace: 'nowrap',
      }}>
        SCN
      </span>

      <button
        onClick={handleToggle}
        style={{
          position: 'relative',
          width: '32px',
          height: '16px',
          borderRadius: '8px',
          border: 'none',
          background: isLive ? '#22c55e' : 'var(--border)',
          cursor: 'pointer',
          padding: 0,
          flexShrink: 0,
          transition: 'background 0.2s',
        }}
      >
        <span style={{
          position: 'absolute',
          top: '2px',
          left: isLive ? '16px' : '2px',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          background: '#fff',
          transition: 'left 0.2s',
        }} />
      </button>

      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '1px',
        textTransform: 'uppercase',
        color: isLive ? '#22c55e' : 'var(--ink-muted)',
        display: 'flex',
        alignItems: 'center',
        gap: '3px',
        whiteSpace: 'nowrap',
      }}>
        <Activity style={{ width: '10px', height: '10px' }} /> LIVE
      </span>

      {isLive && (
        <button
          onClick={onTriggerLive}
          style={{
            marginLeft: '4px',
            background: 'rgba(34,197,94,0.15)',
            border: '1px solid rgba(34,197,94,0.3)',
            color: '#22c55e',
            padding: '2px 7px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 700,
            fontFamily: "'JetBrains Mono', monospace",
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          ▶ RUN
        </button>
      )}
    </div>
  );
};

export default ModeToggle;
