import React, { useState } from 'react';

export default function Recommendations({ recommendations, onApprove, onOverride }) {
  const [overrideText, setOverrideText] = useState('');
  const [showOverrideInput, setShowOverrideInput] = useState(false);

  const handleOverrideSubmit = (e, recId) => {
    e.preventDefault();
    if (overrideText.trim()) {
      onOverride(recId, overrideText);
      setOverrideText('');
      setShowOverrideInput(false);
    }
  };

  return (
    <div style={{
      gridColumn: 'span 4', minHeight: '320px',
      display: 'flex', flexDirection: 'column', padding: '24px',
      background: 'var(--surface-panel)', border: '1px solid var(--border)',
      borderRadius: 'var(--rounded-md)'
    }}>
      <div className="card-header" style={{ marginBottom: '15px' }}>
        <h3 style={{ fontFamily: "'Inter', sans-serif", fontSize: '16px', fontWeight: 600, color: 'var(--ink)', margin: 0 }}>Automated Dispatch Solutions</h3>
        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', color: 'var(--ink-soft)', margin: '4px 0 0 0' }}>Confidence-gated hold/proceed resolutions</p>
      </div>

      <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        {recommendations.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--color-text-dark)', fontStyle: 'italic', padding: '30px' }}>
            -- No recommendations pending resolution --
          </div>
        ) : (
          recommendations.map((rec) => {
            // Circle calculations for the gauge
            const radius = 30;
            const strokeWidth = 5;
            const circumference = 2 * Math.PI * radius;
            const strokeDashoffset = circumference - (rec.confidence * circumference);

            return (
              <div key={rec.id} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                  {/* Circular SVG Gauge */}
                  <div style={{ position: 'relative', width: '70px', height: '70px', flexShrink: 0 }}>
                    <svg width="70" height="70" viewBox="0 0 70 70">
                      {/* Background circle */}
                      <circle
                        cx="35"
                        cy="35"
                        r={radius}
                        fill="transparent"
                        stroke="rgba(255, 255, 255, 0.04)"
                        strokeWidth={strokeWidth}
                      />
                      {/* Animated foreground circle */}
                      <circle
                        cx="35"
                        cy="35"
                        r={radius}
                        fill="transparent"
                        stroke={rec.confidence < 0.85 ? 'var(--ink-soft)' : 'var(--accent)'}
                        strokeWidth={strokeWidth}
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="round"
                        transform="rotate(-90 35 35)"
                        style={{ transition: 'stroke-dashoffset 0.8s ease-in-out' }}
                      />
                    </svg>
                    {/* Inner Text percentage */}
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '70px',
                      height: '70px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.85rem',
                      fontWeight: '700',
                      color: 'var(--ink)'
                    }}>
                      {Math.round(rec.confidence * 100)}%
                    </div>
                  </div>

                  {/* Recommendation description */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent)' }}>
                        {rec.type} {rec.target_train}
                      </span>
                      <span className={`badge-status ${rec.tier === 2 ? 'failed' : 'pending'}`}>
                        {rec.tier === 2 ? 'Escalated' : 'System Auto'}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', lineHeight: '1.4' }}>
                      {rec.reasoning}
                    </p>
                  </div>
                </div>

                {/* Approve/Override actions */}
                {!rec.is_approved && !rec.override_reason ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {!showOverrideInput ? (
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                          className="btn-primary"
                          onClick={() => onApprove(rec.id)}
                          style={{ flexGrow: 1, height: '36px', padding: '0 20px', fontSize: '12px' }}
                        >
                          Approve Hold Resolution
                        </button>
                        <button
                          className="btn-secondary"
                          onClick={() => setShowOverrideInput(true)}
                          style={{ height: '36px', padding: '0 20px', fontSize: '12px' }}
                        >
                          Override
                        </button>
                      </div>
                    ) : (
                      <form onSubmit={(e) => handleOverrideSubmit(e, rec.id)} style={{ display: 'flex', gap: '10px' }}>
                        <input
                          type="text"
                          placeholder="Provide controller override rationale..."
                          value={overrideText}
                          onChange={(e) => setOverrideText(e.target.value)}
                          required
                          style={{
                            flexGrow: 1,
                            background: 'var(--surface-input)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--rounded-sm)',
                            padding: '8px 12px',
                            height: '36px',
                            color: 'var(--ink)',
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: '13px',
                            outline: 'none'
                          }}
                        />
                        <button
                          type="submit"
                          className="btn-primary"
                          style={{ height: '36px', padding: '0 16px', fontSize: '12px' }}
                        >
                          Confirm
                        </button>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => setShowOverrideInput(false)}
                          style={{ height: '36px', padding: '0 16px', fontSize: '12px' }}
                        >
                          Cancel
                        </button>
                      </form>
                    )}
                  </div>
                ) : (
                  <div style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--rounded-sm)',
                    background: rec.is_approved ? 'rgba(76, 175, 80, 0.15)' : 'var(--accent-subtle)',
                    border: `1px solid ${rec.is_approved ? 'rgba(76, 175, 80, 0.3)' : 'var(--border-accent)'}`,
                    fontSize: '13px',
                    fontFamily: "'Inter', sans-serif",
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <span style={{ color: rec.is_approved ? 'var(--status-ok)' : 'var(--accent)', fontWeight: 'bold' }}>
                      {rec.is_approved ? 'APPROVED' : 'OVERRIDDEN'}
                    </span>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                      {rec.is_approved 
                        ? 'Resolution successfully dispatched to track control.'
                        : `Reason: ${rec.override_reason}`
                      }
                    </span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
