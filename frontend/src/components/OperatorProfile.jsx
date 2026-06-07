import React from 'react';

export default function OperatorProfile() {
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
      sessionStarted: new Date(Date.now() - 3.5 * 60 * 60 * 1000).toLocaleTimeString()
    },
    corridors: [
      { name: 'Delhi - Ghaziabad Segment', code: 'DLI-GZB', blocks: 14, system: 'KAVACH_ACTIVE' },
      { name: 'Ghaziabad - Aligarh Segment', code: 'GZB-ALJN', blocks: 32, system: 'ABS_BLOCK_SIGNAL' },
      { name: 'Aligarh - Kanpur Central Corridor', code: 'ALJN-CNB', blocks: 64, system: 'KAVACH_PENDING' }
    ]
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '30px', maxWidth: '1200px', margin: '20px auto', padding: '0 20px' }}>
      {/* Operator Badge Card */}
      <div className="glass-card" style={{ borderLeft: '4px solid var(--color-primary)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '30px 20px' }}>
        <div style={{
          width: '90px',
          height: '90px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '2rem',
          fontWeight: 800,
          color: 'white',
          boxShadow: '0 0 20px rgba(0, 240, 255, 0.4)',
          marginBottom: '20px'
        }}>
          GN
        </div>

        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '5px' }}>{operatorInfo.name}</h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 600, marginBottom: '20px' }}>
          {operatorInfo.role}
        </p>

        <div style={{ width: '100%', borderTop: '1px solid var(--border-color)', paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '12px', textAlign: 'left' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Security Level</span>
            <span style={{ color: 'var(--color-accent)', fontWeight: 'bold' }}>{operatorInfo.credentials.clearanceLevel}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Auth Token</span>
            <span style={{ color: 'var(--color-text-main)', fontFamily: 'monospace' }}>HW_SECP256K1</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Status</span>
            <span style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: 'var(--color-accent)',
              fontWeight: 600
            }}>
              <span className="led-indicator active" style={{ width: '8px', height: '8px' }}></span> ONLINE
            </span>
          </div>
        </div>
      </div>

      {/* Operator Details and assigned zones */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Security Credentials Block */}
        <div className="glass-card">
          <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '15px', color: 'var(--color-primary)' }}>Cryptographic Identity Credentials</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>ECDSA Public Signature Key</span>
              <div style={{
                background: 'var(--bg-terminal)',
                borderRadius: '6px',
                padding: '12px',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '0.65rem',
                color: 'var(--color-text-muted)',
                wordBreak: 'break-all',
                border: '1px solid var(--border-color)',
                lineHeight: '1.4'
              }}>
                {operatorInfo.credentials.ecdsaPublicKey}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>System User ID</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginTop: '2px' }}>{operatorInfo.credentials.userId}</span>
              </div>
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Session Initialized</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginTop: '2px' }}>{operatorInfo.credentials.sessionStarted}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Assigned Corridors */}
        <div className="glass-card">
          <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '15px', color: 'var(--color-primary)' }}>Active Sector Assignations</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
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
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block' }}>{c.name}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Code: {c.code} · Blocks: {c.blocks}</span>
                </div>
                <span style={{
                  fontSize: '0.7rem',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  background: c.system.includes('ACTIVE') ? 'rgba(57, 255, 20, 0.1)' : 'rgba(255, 255, 255, 0.04)',
                  color: c.system.includes('ACTIVE') ? 'var(--color-accent)' : 'var(--color-text-muted)',
                  border: `1px solid ${c.system.includes('ACTIVE') ? 'rgba(57, 255, 20, 0.2)' : 'var(--border-color)'}`
                }}>
                  {c.system}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
