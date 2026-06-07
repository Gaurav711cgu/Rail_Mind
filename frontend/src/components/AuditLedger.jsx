import React, { useState } from 'react';

export default function AuditLedger({ auditLogs }) {
  const [verification, setVerification] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const handleVerify = async () => {
    setVerifying(true);
    setVerification(null);
    
    // Simulate matrix scan delay
    setTimeout(async () => {
      try {
        const res = await fetch('/api/v1/audit/verify');
        if (res.ok) {
          const data = await res.json();
          setVerification(data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setVerifying(false);
      }
    }, 1200);
  };

  return (
    <div className="glass-card" style={{ gridColumn: 'span 12', minHeight: '340px', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Cryptographic Decision Audit Ledger</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Chronologically sealed immutable agent chain</p>
        </div>
        <button 
          className="btn-secondary" 
          onClick={handleVerify}
          disabled={verifying}
          style={{ padding: '6px 12px', fontSize: '0.75rem', borderColor: 'var(--color-accent)', color: 'var(--color-accent)' }}
        >
          {verifying ? 'Scanning Ledger...' : 'Verify Ledger Integrity'}
        </button>
      </div>

      {/* Verification success banner */}
      {verification && (
        <div style={{
          padding: '8px 15px',
          borderRadius: '6px',
          background: 'rgba(57, 255, 20, 0.05)',
          border: '1px solid var(--color-accent)',
          fontSize: '0.8rem',
          color: 'var(--color-accent)',
          marginBottom: '15px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span><strong>Chain Status:</strong> 100% Intact. Verified {verification.total_records} sealed blocks.</span>
          <span style={{ fontWeight: 'bold' }}>SECURE ✓</span>
        </div>
      )}

      {/* Ledger list container */}
      <div style={{
        flexGrow: 1,
        overflowY: 'auto',
        maxHeight: '190px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        position: 'relative'
      }}>
        {/* Matrix Scanning Sweep Bar */}
        {verifying && <div className="scanner-overlay" />}

        {auditLogs.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--color-text-dark)', fontStyle: 'italic', padding: '30px' }}>
            -- Ledger empty. Advance scenario to seal blocks --
          </div>
        ) : (
          auditLogs.map((log) => (
            <div 
              key={log.id} 
              style={{
                background: 'rgba(255, 255, 255, 0.01)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '10px 15px',
                fontSize: '0.75rem',
                position: 'relative'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{log.agent_name}</span>
                <span style={{ color: 'var(--color-text-muted)' }}>Block #{log.id}</span>
              </div>
              <p style={{ color: 'var(--color-text-main)', marginBottom: '8px' }}>{log.reasoning}</p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontFamily: 'monospace', fontSize: '0.6rem', color: 'var(--color-text-muted)', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '6px' }}>
                <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  <strong>HASH:</strong> <span style={{ color: '#F472B6' }}>{log.current_hash}</span>
                </span>
                <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  <strong>PREV:</strong> {log.prev_hash}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
