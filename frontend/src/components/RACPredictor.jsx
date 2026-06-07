import React, { useState } from 'react';

export default function RACPredictor() {
  const [query, setQuery] = useState({
    train_no: '22415',
    from_station: 'NDLS',
    to_station: 'ALJN',
    date: '2026-06-15',
    current_waitlist_position: 12,
    current_rac_count: 8,
    days_to_journey: 5,
    quota: 'GN'
  });

  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch('/api/v1/rac/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(query)
      });
      if (res.ok) {
        const data = await res.json();
        setPrediction(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card" style={{ gridColumn: 'span 12', minHeight: '340px' }}>
      <div className="card-header" style={{ marginBottom: '15px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>ML RAC / Waitlist Confirmation Predictor</h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>XGBoost Classifier trained on ticketing dynamics</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Form Inputs */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Train Number</label>
              <select
                value={query.train_no}
                onChange={e => setQuery({ ...query, train_no: e.target.value })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '6px', fontSize: '0.75rem', outline: 'none' }}
              >
                <option value="22415">22415 (Vande Bharat)</option>
                <option value="12002">12002 (Shatabdi)</option>
                <option value="12301">12301 (Rajdhani)</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Booking Quota</label>
              <select
                value={query.quota}
                onChange={e => setQuery({ ...query, quota: e.target.value })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '6px', fontSize: '0.75rem', outline: 'none' }}
              >
                <option value="GN">General (GN)</option>
                <option value="TQ">Tatkal (TQ)</option>
                <option value="LD">Ladies (LD)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Waitlist Pos</label>
              <input
                type="number"
                value={query.current_waitlist_position}
                onChange={e => setQuery({ ...query, current_waitlist_position: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '6px', fontSize: '0.75rem', outline: 'none' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>RAC Size</label>
              <input
                type="number"
                value={query.current_rac_count}
                onChange={e => setQuery({ ...query, current_rac_count: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '6px', fontSize: '0.75rem', outline: 'none' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '2px' }}>Days to Go</label>
              <input
                type="number"
                value={query.days_to_journey}
                onChange={e => setQuery({ ...query, days_to_journey: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '6px', fontSize: '0.75rem', outline: 'none' }}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '5px', padding: '8px' }}>
            {loading ? 'Analyzing Trends...' : 'Calculate Confirmation Rate'}
          </button>
        </form>

        {/* Prediction Results Display */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {!prediction ? (
            <div style={{ textStyle: 'italic', color: 'var(--color-text-dark)', fontSize: '0.8rem', textAlign: 'center', padding: '20px', border: '1px dashed var(--border-color)', borderRadius: '6px' }}>
              Submit waitlist query parameters to run XGBoost confirmation likelihood inference
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Conf Rate Progress Bar */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600 }}>Confirmation Probability</span>
                  <span style={{ fontWeight: 800, color: 'var(--color-accent)' }}>
                    {Math.round(prediction.confirmation_probability * 100)}%
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${prediction.confirmation_probability * 100}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, var(--color-primary), var(--color-accent))',
                    boxShadow: '0 0 8px var(--color-accent)',
                    transition: 'width 0.5s ease-out'
                  }}></div>
                </div>
                <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>
                  Interval: [{Math.round(prediction.confidence_interval[0]*100)}% - {Math.round(prediction.confidence_interval[1]*100)}%]
                </span>
              </div>

              {/* Factors list */}
              <div>
                <h4 style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '1px' }}>Feature Importance</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                  {prediction.key_factors.map(f => (
                    <div key={f.factor} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                      <span style={{ color: 'var(--color-text-main)' }}>{f.factor}</span>
                      <span style={{ color: f.impact >= 0 ? 'var(--color-accent)' : 'var(--color-danger)', fontWeight: 'bold' }}>
                        {f.impact >= 0 ? '+' : ''}{Math.round(f.impact * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
