import { Database, Zap } from 'lucide-react';

const DataSourceBadge = ({ source }) => {
  const isLive = source === 'NTES' || source === 'RAILWAYAPI';

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      height: '28px',
      padding: '0 8px',
      borderRadius: '6px',
      border: `1px solid ${isLive ? 'rgba(34,197,94,0.3)' : 'rgba(245,158,11,0.3)'}`,
      background: isLive ? 'rgba(34,197,94,0.08)' : 'rgba(245,158,11,0.08)',
      color: isLive ? '#22c55e' : 'var(--accent)',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '10px',
      fontWeight: 700,
      letterSpacing: '0.8px',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      flexShrink: 0,
    }}>
      {isLive
        ? <Zap style={{ width: '10px', height: '10px' }} />
        : <Database style={{ width: '10px', height: '10px' }} />}
      {isLive ? 'LIVE' : 'SCN'}
    </div>
  );
};

export default DataSourceBadge;
