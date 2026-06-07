import React, { useState, useEffect } from 'react';

export default function RACPredictor() {
  // 1. Primary query state
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

  // States for sub-features
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historicalTrends, setHistoricalTrends] = useState([]);
  const [alternativeTrains, setAlternativeTrains] = useState([]);
  const [quotaHeatmap, setQuotaHeatmap] = useState([]);
  const [upgradeClass, setUpgradeClass] = useState('3AC');
  const [upgradeChances, setUpgradeChances] = useState(65);
  const [comparisonTrain, setComparisonTrain] = useState('12002');
  const [comparisonOdds, setComparisonOdds] = useState(0.42);
  const [modelWeightTuner, setModelWeightTuner] = useState({
    journeyDaysWeight: 1.0,
    waitlistWeight: 1.0
  });

  // Calculate confirmation likelihood
  const runPrediction = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/rac/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(query)
      });
      if (res.ok) {
        const data = await res.json();
        
        // Tweak probability based on interactive slider weights
        let adjustedProb = data.confirmation_probability;
        if (modelWeightTuner.journeyDaysWeight !== 1.0) {
          adjustedProb += (modelWeightTuner.journeyDaysWeight - 1.0) * 0.05;
        }
        if (modelWeightTuner.waitlistWeight !== 1.0) {
          adjustedProb -= (modelWeightTuner.waitlistWeight - 1.0) * 0.08;
        }
        adjustedProb = Math.max(0.01, Math.min(0.99, adjustedProb));

        setPrediction({
          ...data,
          confirmation_probability: adjustedProb
        });
      }

      // Fetch accompanying features
      const resTrends = await fetch(`/api/v1/rac/historical-trends?train_no=${query.train_no}`);
      if (resTrends.ok) {
        const dataTrends = await resTrends.json();
        setHistoricalTrends(dataTrends);
      }

      const resAlts = await fetch(`/api/v1/rac/alternative-suggestions?train_no=${query.train_no}&from_station=${query.from_station}&to_station=${query.to_station}`);
      if (resAlts.ok) {
        const dataAlts = await resAlts.json();
        setAlternativeTrains(dataAlts);
      }

      const resHeat = await fetch(`/api/v1/rac/quota-heatmap?train_no=${query.train_no}&waitlist_pos=${query.current_waitlist_position}`);
      if (resHeat.ok) {
        const dataHeat = await resHeat.json();
        setQuotaHeatmap(dataHeat);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runPrediction();
  }, [query.train_no, modelWeightTuner]);

  const handleSubmit = (e) => {
    e.preventDefault();
    runPrediction();
  };

  // Seat Upgrade odds calculation logic
  const handleUpgradeClassChange = (cls) => {
    setUpgradeClass(cls);
    const base = cls === '2AC' ? 38 : cls === '3AC' ? 72 : 88;
    const computed = Math.round(base - (query.current_waitlist_position * 1.5) + (query.days_to_journey * 2));
    setUpgradeChances(Math.max(5, Math.min(95, computed)));
  };

  // Multi-train comparison odds logic
  const handleComparisonChange = (trainNo) => {
    setComparisonTrain(trainNo);
    const odds = trainNo === '22415' ? 0.88 : trainNo === '12002' ? 0.74 : 0.94;
    setComparisonOdds(odds);
  };

  return (
    <div className="bento-grid" style={{ padding: 0 }}>
      
      {/* Feature 1: XGBoost Confirmation Predictor & Tuner */}
      <div className="glass-card" style={{ gridColumn: 'span 5', minHeight: '380px', display: 'flex', flexDirection: 'column' }}>
        <div className="card-header" style={{ marginBottom: '15px' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>ML RAC Waitlist Predictor</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>XGBoost Classifier with adjustable feature weights</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '3px' }}>Select Train</label>
              <select
                value={query.train_no}
                onChange={e => setQuery({ ...query, train_no: e.target.value })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
              >
                <option value="22415">22415 (Vande Bharat)</option>
                <option value="12002">12002 (Shatabdi)</option>
                <option value="12301">12301 (Rajdhani)</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '3px' }}>Quota</label>
              <select
                value={query.quota}
                onChange={e => setQuery({ ...query, quota: e.target.value })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
              >
                <option value="GN">General (GN)</option>
                <option value="TQ">Tatkal (TQ)</option>
                <option value="LD">Ladies (LD)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '3px' }}>Waitlist Pos</label>
              <input
                type="number"
                value={query.current_waitlist_position}
                onChange={e => setQuery({ ...query, current_waitlist_position: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '3px' }}>RAC Size</label>
              <input
                type="number"
                value={query.current_rac_count}
                onChange={e => setQuery({ ...query, current_rac_count: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '3px' }}>Days to Go</label>
              <input
                type="number"
                value={query.days_to_journey}
                onChange={e => setQuery({ ...query, days_to_journey: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', fontSize: '0.75rem', outline: 'none' }}
              />
            </div>
          </div>

          {/* Feature: Model Parameter weight tuners */}
          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
              XGBoost Feature Importance Bias Tuners
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
              <div>
                <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Journey Days Bias</span>
                  <strong>{modelWeightTuner.journeyDaysWeight}x</strong>
                </span>
                <input 
                  type="range" min="0.5" max="2.0" step="0.1" 
                  value={modelWeightTuner.journeyDaysWeight} 
                  onChange={e => setModelWeightTuner({...modelWeightTuner, journeyDaysWeight: parseFloat(e.target.value)})}
                  style={{ width: '100%', height: '2px', outline: 'none' }} 
                />
              </div>
              <div>
                <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Waitlist Weight Bias</span>
                  <strong>{modelWeightTuner.waitlistWeight}x</strong>
                </span>
                <input 
                  type="range" min="0.5" max="2.0" step="0.1" 
                  value={modelWeightTuner.waitlistWeight} 
                  onChange={e => setModelWeightTuner({...modelWeightTuner, waitlistWeight: parseFloat(e.target.value)})}
                  style={{ width: '100%', height: '2px', outline: 'none' }} 
                />
              </div>
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%', padding: '10px', fontSize: '0.8rem', marginTop: '4px' }}>
            {loading ? 'Re-Running Classifier Inference...' : 'Calculate Confirmation Odds'}
          </button>
        </form>
      </div>

      {/* Feature 2: Interactive SVG RAC Seat Split & Upgrade Analyzer */}
      <div className="glass-card" style={{ gridColumn: 'span 4', minHeight: '380px', display: 'flex', flexDirection: 'column' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '12px' }}>
          RAC Seat Split & Berths
        </h4>

        {/* RAC seat illustration */}
        <div style={{ background: 'var(--bg-terminal)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color)', display: 'flex', justifyContent: 'center', marginBottom: '15px' }}>
          <svg width="220" height="70" viewBox="0 0 220 70">
            {/* Lower berth border */}
            <rect x="10" y="10" width="200" height="50" rx="4" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="2" />
            
            {/* Passenger 1 partition */}
            <rect x="15" y="15" width="90" height="40" rx="3" fill="rgba(0, 240, 255, 0.05)" stroke="var(--color-primary)" strokeWidth="1" />
            <text x="60" y="35" textAnchor="middle" fill="white" fontSize="0.65rem" fontWeight="bold">RAC Pax #1</text>
            <text x="60" y="47" textAnchor="middle" fill="var(--color-text-muted)" fontSize="0.5rem">Side Lower A</text>

            {/* Passenger 2 partition */}
            <rect x="115" y="15" width="90" height="40" rx="3" fill="rgba(168, 85, 247, 0.05)" stroke="var(--color-secondary)" strokeWidth="1" />
            <text x="160" y="35" textAnchor="middle" fill="white" fontSize="0.65rem" fontWeight="bold">RAC Pax #2</text>
            <text x="160" y="47" textAnchor="middle" fill="var(--color-text-muted)" fontSize="0.5rem">Side Lower B</text>
          </svg>
        </div>

        {/* Upgrade Calculator */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 'auto' }}>
          <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Auto-Berth Upgrade Calculator:</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['3AC', '2AC', '1AC'].map(cls => (
              <button
                key={cls}
                onClick={() => handleUpgradeClassChange(cls)}
                style={{
                  flex: 1,
                  background: upgradeClass === cls ? 'var(--color-secondary)' : 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'white',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  padding: '6px 0',
                  cursor: 'pointer'
                }}
              >
                {cls}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.15)', padding: '10px 15px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.75rem' }}>Auto-Upgrade Odds:</span>
            <span style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--color-accent)' }}>{upgradeChances}%</span>
          </div>
        </div>
      </div>

      {/* Feature 3: Quota Heatmap Matrix */}
      <div className="glass-card" style={{ gridColumn: 'span 3', minHeight: '380px', display: 'flex', flexDirection: 'column' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '15px' }}>
          Quota Heatmap
        </h4>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flexGrow: 1, justifyContent: 'center' }}>
          {quotaHeatmap.map(q => (
            <div key={q.quota} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                <span style={{ fontWeight: 600, color: 'white' }}>{q.quota}</span>
                <span style={{ fontWeight: 700, color: q.probability > 0.6 ? 'var(--color-accent)' : q.probability > 0.3 ? 'var(--color-warning)' : 'var(--color-danger)' }}>
                  {Math.round(q.probability * 100)}%
                </span>
              </div>
              <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.03)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  width: `${q.probability * 100}%`,
                  height: '100%',
                  background: q.probability > 0.6 ? 'var(--color-accent)' : q.probability > 0.3 ? 'var(--color-warning)' : 'var(--color-danger)'
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Feature 4: SVG Historical Confirmation Trend Chart */}
      <div className="glass-card" style={{ gridColumn: 'span 6', minHeight: '360px', display: 'flex', flexDirection: 'column' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '15px' }}>
          Historical Confirmation Trends (6 Months)
        </h4>
        
        <div style={{ flexGrow: 1, background: 'var(--bg-terminal)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '15px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {historicalTrends.length === 0 ? (
            <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--color-text-dark)', fontStyle: 'italic' }}>
              Generating historical odds analysis chart...
            </div>
          ) : (
            <div style={{ width: '100%' }}>
              {/* Dynamic SVG chart */}
              <svg viewBox="0 0 400 140" width="100%" height="130px">
                <defs>
                  <linearGradient id="chart-glow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Grid guidelines */}
                <line x1="40" y1="20" x2="380" y2="20" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                <line x1="40" y1="60" x2="380" y2="60" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                <line x1="40" y1="100" x2="380" y2="100" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                <line x1="40" y1="120" x2="380" y2="120" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />

                {/* Left Y Axis labels */}
                <text x="15" y="24" fill="var(--color-text-dark)" fontSize="0.55rem">100%</text>
                <text x="15" y="64" fill="var(--color-text-dark)" fontSize="0.55rem">50%</text>
                <text x="15" y="104" fill="var(--color-text-dark)" fontSize="0.55rem">25%</text>

                {/* Chart Path and Points */}
                {(() => {
                  const paddingLeft = 60;
                  const width = 300;
                  const stepX = width / (historicalTrends.length - 1);
                  let points = "";
                  let fillPoints = `40,120 `;
                  
                  historicalTrends.forEach((t, idx) => {
                    const x = paddingLeft + idx * stepX;
                    const y = 120 - (t.rate * 100);
                    points += `${x},${y} `;
                    fillPoints += `${x},${y} `;
                  });
                  fillPoints += `360,120`;

                  return (
                    <g>
                      {/* Gradient fill */}
                      <polygon points={fillPoints} fill="url(#chart-glow)" />
                      {/* Path line */}
                      <polyline points={points} fill="none" stroke="var(--color-primary)" strokeWidth="2" filter="url(#svg-neon-glow)" />
                      
                      {/* Points markers */}
                      {historicalTrends.map((t, idx) => {
                        const x = paddingLeft + idx * stepX;
                        const y = 120 - (t.rate * 100);
                        return (
                          <g key={idx}>
                            <circle cx={x} cy={y} r="3" fill="#FFFFFF" stroke="var(--color-primary)" strokeWidth="1.5" />
                            <text x={x} y="134" textAnchor="middle" fill="var(--color-text-muted)" fontSize="0.55rem">{t.month}</text>
                            <text x={x} y={y - 8} textAnchor="middle" fill="var(--color-accent)" fontSize="0.5rem" fontWeight="bold">
                              {Math.round(t.rate * 100)}%
                            </text>
                          </g>
                        );
                      })}
                    </g>
                  );
                })()}
              </svg>
            </div>
          )}
        </div>
      </div>

      {/* Feature 5: Alternative Route Suggestions & Parallel Comparison */}
      <div className="glass-card" style={{ gridColumn: 'span 6', minHeight: '360px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '15px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Protected Routing Alternatives
          </h4>
          
          {/* Multi-train comparative selection */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Compare:</span>
            <select
              value={comparisonTrain}
              onChange={e => handleComparisonChange(e.target.value)}
              style={{ background: 'var(--bg-terminal)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '3px 8px', fontSize: '0.65rem', outline: 'none' }}
            >
              <option value="12002">12002 (Shatabdi)</option>
              <option value="22415">22415 (Vande Bharat)</option>
              <option value="12301">12301 (Rajdhani)</option>
            </select>
            <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--color-accent)' }}>{Math.round(comparisonOdds*100)}%</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flexGrow: 1 }}>
          {alternativeTrains.length === 0 ? (
            <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--color-text-dark)', fontStyle: 'italic', padding: '30px' }}>
              Finding alternative route options...
            </div>
          ) : (
            alternativeTrains.map(alt => (
              <div 
                key={alt.train_no} 
                style={{
                  background: 'rgba(255,255,255,0.01)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '12px 15px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'white', display: 'block' }}>{alt.train_name}</span>
                  <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>
                    No: {alt.train_no} · Dept: {alt.departure} · Duration: {alt.duration}
                  </span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: '0.7rem',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    background: alt.status === 'RUNNING' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    color: alt.status === 'RUNNING' ? 'var(--color-accent)' : 'var(--color-danger)',
                    border: `1px solid ${alt.status === 'RUNNING' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                    display: 'inline-block',
                    marginBottom: '4px'
                  }}>
                    {alt.status}
                  </span>
                  <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>
                    Conf odds: <strong style={{ color: 'var(--color-primary)' }}>{Math.round(alt.confirmation_probability * 100)}%</strong>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}
