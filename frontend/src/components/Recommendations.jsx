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
    <div className="glass-card" style={{ gridColumn: 'span 4', minHeight: '320px', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ marginBottom: '15px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Automated Dispatch Solutions</h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Confidence-gated hold/proceed resolutions</p>
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
                        stroke={rec.confidence < 0.85 ? 'var(--color-secondary)' : 'var(--color-primary)'}
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
                      color: 'var(--color-text-main)'
                    }}>
                      {Math.round(rec.confidence * 100)}%
                    </div>
                  </div>

                  {/* Recommendation description */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                        {rec.type} {rec.target_train}
                      </span>
                      <span style={{
                        fontSize: '0.65rem',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: rec.tier === 2 ? 'rgba(227, 26, 34, 0.12)' : 'rgba(255, 255, 255, 0.12)',
                        color: rec.tier === 2 ? 'var(--color-primary)' : 'var(--color-secondary)',
                        border: `1px solid ${rec.tier === 2 ? 'rgba(227, 26, 34, 0.2)' : 'rgba(255, 255, 255, 0.2)'}`
                      }}>
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
                          style={{ flexGrow: 1, padding: '8px 15px', fontSize: '0.8rem' }}
                        >
                          Approve Hold Resolution
                        </button>
                        <button
                          className="btn-secondary"
                          onClick={() => setShowOverrideInput(true)}
                          style={{ padding: '8px 15px', fontSize: '0.8rem' }}
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
                            background: 'var(--bg-terminal)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            color: 'white',
                            fontSize: '0.75rem',
                            outline: 'none'
                          }}
                        />
                        <button
                          type="submit"
                          className="btn-primary"
                          style={{ background: 'var(--color-danger)', boxShadow: 'none', padding: '6px 12px', fontSize: '0.75rem' }}
                        >
                          Confirm
                        </button>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => setShowOverrideInput(false)}
                          style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                        >
                          Cancel
                        </button>
                      </form>
                    )}
                  </div>
                ) : (
                  <div style={{
                    padding: '10px',
                    borderRadius: '6px',
                    background: rec.is_approved ? 'rgba(57, 255, 20, 0.05)' : 'rgba(255, 49, 49, 0.05)',
                    border: `1px dashed ${rec.is_approved ? 'var(--color-accent)' : 'var(--color-danger)'}`,
                    fontSize: '0.8rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <span style={{ color: rec.is_approved ? 'var(--color-accent)' : 'var(--color-danger)', fontWeight: 'bold' }}>
                      {rec.is_approved ? '✓ APPROVED' : '✗ OVERRIDDEN'}
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
