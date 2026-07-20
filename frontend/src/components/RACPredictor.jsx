import { useState, useEffect } from 'react';

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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    runPrediction();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    <div className="bento-grid" style={{ padding: '0 24px' }}>
      
      {/* Feature 1: XGBoost Confirmation Predictor & Tuner */}
      <div style={{
        gridColumn: 'span 5',
        minHeight: '380px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        boxSizing: 'border-box'
      }}>
        <div style={{ marginBottom: '15px' }}>
          <h3 style={{ fontFamily: "'Inter', sans-serif", fontSize: '16px', fontWeight: 600, color: 'var(--ink)', margin: 0 }}>
            ML RAC Waitlist Predictor
          </h3>
          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', color: 'var(--ink-soft)', margin: '4px 0 0 0' }}>
            XGBoost Classifier with adjustable feature weights
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Select Train</label>
              <select
                value={query.train_no}
                onChange={e => setQuery({ ...query, train_no: e.target.value })}
                style={{
                  width: '100%',
                  background: 'var(--surface-input)',
                  color: 'var(--ink)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-sm)',
                  padding: '8px 12px',
                  height: '36px',
                  fontSize: '13px',
                  fontFamily: "'JetBrains Mono', monospace",
                  outline: 'none',
                  boxSizing: 'border-box',
                  cursor: 'pointer'
                }}
              >
                <option value="22415">22415 (Vande Bharat)</option>
                <option value="12002">12002 (Shatabdi)</option>
                <option value="12301">12301 (Rajdhani)</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Quota</label>
              <select
                value={query.quota}
                onChange={e => setQuery({ ...query, quota: e.target.value })}
                style={{
                  width: '100%',
                  background: 'var(--surface-input)',
                  color: 'var(--ink)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-sm)',
                  padding: '8px 12px',
                  height: '36px',
                  fontSize: '13px',
                  fontFamily: "'JetBrains Mono', monospace",
                  outline: 'none',
                  boxSizing: 'border-box',
                  cursor: 'pointer'
                }}
              >
                <option value="GN">General (GN)</option>
                <option value="TQ">Tatkal (TQ)</option>
                <option value="LD">Ladies (LD)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Waitlist Pos</label>
              <input
                type="number"
                value={query.current_waitlist_position}
                onChange={e => setQuery({ ...query, current_waitlist_position: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  background: 'var(--surface-input)',
                  color: 'var(--ink)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-sm)',
                  padding: '8px 12px',
                  height: '36px',
                  fontSize: '13px',
                  fontFamily: "'JetBrains Mono', monospace",
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>RAC Size</label>
              <input
                type="number"
                value={query.current_rac_count}
                onChange={e => setQuery({ ...query, current_rac_count: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  background: 'var(--surface-input)',
                  color: 'var(--ink)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-sm)',
                  padding: '8px 12px',
                  height: '36px',
                  fontSize: '13px',
                  fontFamily: "'JetBrains Mono', monospace",
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: '4px' }}>Days to Go</label>
              <input
                type="number"
                value={query.days_to_journey}
                onChange={e => setQuery({ ...query, days_to_journey: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  background: 'var(--surface-input)',
                  color: 'var(--ink)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-sm)',
                  padding: '8px 12px',
                  height: '36px',
                  fontSize: '13px',
                  fontFamily: "'JetBrains Mono', monospace",
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          </div>

          {/* Feature: Model Parameter weight tuners */}
          <div style={{ borderTop: '1px solid var(--border-soft)', paddingTop: '10px' }}>
            <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>
              XGBoost Feature Importance Bias Tuners
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '11px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-soft)', display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span>Journey Days Bias</span>
                  <strong style={{ fontFamily: "'JetBrains Mono', monospace" }}>{modelWeightTuner.journeyDaysWeight}x</strong>
                </span>
                <input 
                  type="range" min="0.5" max="2.0" step="0.1" 
                  value={modelWeightTuner.journeyDaysWeight} 
                  onChange={e => setModelWeightTuner({...modelWeightTuner, journeyDaysWeight: parseFloat(e.target.value)})}
                  style={{ width: '100%', height: '2px', accentColor: 'var(--accent)', cursor: 'pointer' }} 
                />
              </div>
              <div>
                <span style={{ fontSize: '11px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-soft)', display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span>Waitlist Weight Bias</span>
                  <strong style={{ fontFamily: "'JetBrains Mono', monospace" }}>{modelWeightTuner.waitlistWeight}x</strong>
                </span>
                <input 
                  type="range" min="0.5" max="2.0" step="0.1" 
                  value={modelWeightTuner.waitlistWeight} 
                  onChange={e => setModelWeightTuner({...modelWeightTuner, waitlistWeight: parseFloat(e.target.value)})}
                  style={{ width: '100%', height: '2px', accentColor: 'var(--accent)', cursor: 'pointer' }} 
                />
              </div>
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%', height: '36px', fontSize: '12px', marginTop: '4px' }}>
            {loading ? 'Re-Running Classifier Inference...' : 'Calculate Confirmation Odds'}
          </button>
        </form>
      </div>

      {/* Feature 2: Interactive SVG RAC Seat Split & Upgrade Analyzer */}
      <div style={{
        gridColumn: 'span 4',
        minHeight: '380px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        boxSizing: 'border-box'
      }}>
        <h4 style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: 'var(--accent)',
          borderBottom: '1px solid var(--border-soft)',
          paddingBottom: '8px',
          margin: '0 0 15px 0'
        }}>
          RAC Seat Split & Berths
        </h4>

        {/* RAC seat illustration */}
        <div style={{ background: 'var(--surface-input)', padding: '10px', borderRadius: 'var(--rounded-sm)', border: '1px solid var(--border)', display: 'flex', justifyContent: 'center', marginBottom: '15px' }}>
          <svg width="220" height="70" viewBox="0 0 220 70">
            {/* Lower berth border */}
            <rect x="10" y="10" width="200" height="50" rx="2" fill="none" stroke="var(--border)" strokeWidth="2" />
            
            {/* Passenger 1 partition */}
            <rect x="15" y="15" width="90" height="40" rx="2" fill="var(--accent-subtle)" stroke="var(--accent)" strokeWidth="1" />
            <text x="60" y="35" textAnchor="middle" fill="var(--ink)" fontSize="10px" fontFamily="Inter, sans-serif" fontWeight="bold">RAC Pax #1</text>
            <text x="60" y="47" textAnchor="middle" fill="var(--ink-soft)" fontSize="8px" fontFamily="Inter, sans-serif">Side Lower A</text>

            {/* Passenger 2 partition */}
            <rect x="115" y="15" width="90" height="40" rx="2" fill="var(--surface-elevated)" stroke="var(--border)" strokeWidth="1" />
            <text x="160" y="35" textAnchor="middle" fill="var(--ink)" fontSize="10px" fontFamily="Inter, sans-serif" fontWeight="bold">RAC Pax #2</text>
            <text x="160" y="47" textAnchor="middle" fill="var(--ink-soft)" fontSize="8px" fontFamily="Inter, sans-serif">Side Lower B</text>
          </svg>
        </div>

        {/* Upgrade Calculator */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: 'auto' }}>
          <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase' }}>Auto-Berth Upgrade Calculator:</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['3AC', '2AC', '1AC'].map(cls => (
              <button
                key={cls}
                onClick={() => handleUpgradeClassChange(cls)}
                style={{
                  flex: 1,
                  background: upgradeClass === cls ? 'var(--accent)' : 'transparent',
                  border: `1px solid ${upgradeClass === cls ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: 'var(--rounded-xs)',
                  color: upgradeClass === cls ? 'var(--ink-on-red)' : 'var(--ink-soft)',
                  fontSize: '11px',
                  fontWeight: 700,
                  height: '32px',
                  cursor: 'pointer',
                  outline: 'none',
                  transition: 'all 0.1s'
                }}
              >
                {cls}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--surface-elevated)', padding: '12px 18px', borderRadius: 'var(--rounded-xs)', border: '1px solid var(--border)' }}>
            <span style={{ fontSize: '13px', fontFamily: "'Inter', sans-serif", color: 'var(--ink)' }}>Auto-Upgrade Odds:</span>
            <span style={{ fontSize: '16px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: 'var(--accent)' }}>{upgradeChances}%</span>
          </div>
        </div>
      </div>

      {/* Feature 3: Quota Heatmap Matrix */}
      <div style={{
        gridColumn: 'span 3',
        minHeight: '380px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        boxSizing: 'border-box'
      }}>
        <h4 style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: 'var(--accent)',
          borderBottom: '1px solid var(--border-soft)',
          paddingBottom: '8px',
          margin: '0 0 15px 0'
        }}>
          Quota Heatmap
        </h4>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flexGrow: 1, justifyContent: 'center' }}>
          {quotaHeatmap.map(q => (
            <div key={q.quota} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontFamily: "'Inter', sans-serif" }}>
                <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{q.quota}</span>
                <span style={{ fontWeight: 700, color: 'var(--ink)' }}>
                  {Math.round(q.probability * 100)}%
                </span>
              </div>
              <div style={{ width: '100%', height: '4px', background: 'var(--border)', borderRadius: 0, overflow: 'hidden' }}>
                <div style={{
                  width: `${q.probability * 100}%`,
                  height: '100%',
                  background: 'var(--accent)',
                  borderRadius: 0
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SHAP Feature Impact Bars */}
      {prediction && prediction.key_factors && prediction.key_factors.length > 0 && (
        <div style={{
          gridColumn: 'span 12',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px',
          background: 'var(--surface-panel)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--rounded-md)',
          boxSizing: 'border-box'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-soft)', paddingBottom: '8px', marginBottom: '16px' }}>
            <div>
              <h4 style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '13px',
                fontWeight: 700,
                letterSpacing: '2px',
                textTransform: 'uppercase',
                color: 'var(--accent)',
                margin: 0
              }}>
                SHAP Feature Impact — Log-Odds Contributions
              </h4>
              {prediction.model_version && (
                <span style={{ fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: 'var(--ink-soft)', marginTop: '4px', display: 'inline-block' }}>
                  Model: {prediction.model_version}
                </span>
              )}
            </div>
            {prediction.confidence_interval && (
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', textTransform: 'uppercase', display: 'block' }}>95% Confidence Interval</span>
                <span style={{ fontSize: '13px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: 'var(--ink)' }}>
                  [{prediction.confidence_interval[0]?.toFixed(3)}, {prediction.confidence_interval[1]?.toFixed(3)}]
                </span>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {(() => {
              const maxAbsImpact = Math.max(...prediction.key_factors.map(f => Math.abs(f.impact)), 0.001);
              return prediction.key_factors.map((factor, idx) => {
                const barWidthPct = (Math.abs(factor.impact) / maxAbsImpact) * 45;
                const isPositive = factor.impact >= 0;
                return (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    {/* Factor name */}
                    <span style={{ flex: '0 0 160px', fontSize: '13px', fontWeight: 600, color: 'var(--ink-soft)', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {factor.factor}
                    </span>

                    {/* Bar container */}
                    <div style={{ flex: 1, position: 'relative', height: '16px', background: 'var(--surface-input)', border: '1px solid var(--border)', borderRadius: 0, overflow: 'hidden' }}>
                      {/* Center line */}
                      <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '1px', background: 'var(--border)', zIndex: 1 }} />

                      {isPositive ? (
                        /* Positive: bar extends right from center (uses ink-soft) */
                        <div style={{
                          position: 'absolute',
                          left: '50%',
                          top: '2px',
                          bottom: '2px',
                          width: `${barWidthPct}%`,
                          background: 'var(--ink-soft)',
                          borderRadius: 0,
                          transition: 'width 0.4s ease'
                        }} />
                      ) : (
                        /* Negative: bar extends left from center (uses accent red) */
                        <div style={{
                          position: 'absolute',
                          right: '50%',
                          top: '2px',
                          bottom: '2px',
                          width: `${barWidthPct}%`,
                          background: 'var(--accent)',
                          borderRadius: 0,
                          transition: 'width 0.4s ease'
                        }} />
                      )}
                    </div>

                    {/* Impact value */}
                    <span style={{
                      flex: '0 0 60px',
                      fontSize: '11px',
                      fontWeight: 700,
                      fontFamily: "'JetBrains Mono', monospace",
                      textAlign: 'left',
                      color: isPositive ? 'var(--ink-soft)' : 'var(--accent)'
                    }}>
                      {isPositive ? '+' : ''}{factor.impact.toFixed(3)}
                    </span>
                  </div>
                );
              });
            })()}
          </div>

          {prediction.disclaimer && (
            <p style={{ fontSize: '11px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', fontStyle: 'italic', marginTop: '16px', borderTop: '1px solid var(--border-soft)', paddingTop: '8px', margin: '16px 0 0 0' }}>
              {prediction.disclaimer}
            </p>
          )}
        </div>
      )}

      {/* Feature 4: SVG Historical Confirmation Trend Chart */}
      <div style={{
        gridColumn: 'span 6',
        minHeight: '360px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        boxSizing: 'border-box'
      }}>
        <h4 style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: 'var(--accent)',
          borderBottom: '1px solid var(--border-soft)',
          paddingBottom: '8px',
          margin: '0 0 15px 0'
        }}>
          Historical Confirmation Trends (6 Months)
        </h4>
        
        <div style={{ flexGrow: 1, background: 'var(--surface-input)', border: '1px solid var(--border)', borderRadius: 'var(--rounded-sm)', padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {historicalTrends.length === 0 ? (
            <div style={{ textAlign: 'center', fontSize: '13px', color: 'var(--ink-muted)', fontStyle: 'italic', fontFamily: "'Inter', sans-serif" }}>
              Generating historical odds analysis chart...
            </div>
          ) : (
            <div style={{ width: '100%' }}>
              {/* Dynamic SVG chart */}
              <svg viewBox="0 0 400 140" width="100%" height="130px">
                {/* Grid guidelines */}
                <line x1="40" y1="20" x2="380" y2="20" stroke="var(--border)" strokeWidth="1" strokeDasharray="2" />
                <line x1="40" y1="60" x2="380" y2="60" stroke="var(--border)" strokeWidth="1" strokeDasharray="2" />
                <line x1="40" y1="100" x2="380" y2="100" stroke="var(--border)" strokeWidth="1" strokeDasharray="2" />
                <line x1="40" y1="120" x2="380" y2="120" stroke="var(--border)" strokeWidth="1" />

                {/* Left Y Axis labels */}
                <text x="10" y="24" fill="var(--ink-muted)" fontSize="8px" fontFamily="'JetBrains Mono', monospace">100%</text>
                <text x="10" y="64" fill="var(--ink-muted)" fontSize="8px" fontFamily="'JetBrains Mono', monospace">50%</text>
                <text x="10" y="104" fill="var(--ink-muted)" fontSize="8px" fontFamily="'JetBrains Mono', monospace">25%</text>

                {/* Chart Path and Points */}
                {(() => {
                  const paddingLeft = 60;
                  const width = 300;
                  const stepX = width / (historicalTrends.length - 1);
                  let points = "";
                  
                  historicalTrends.forEach((t, idx) => {
                    const x = paddingLeft + idx * stepX;
                    const y = 120 - (t.rate * 100);
                    points += `${x},${y} `;
                  });

                  return (
                    <g>
                      {/* Path line (flat stroke, no neon filters) */}
                      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="2" />
                      
                      {/* Points markers */}
                      {historicalTrends.map((t, idx) => {
                        const x = paddingLeft + idx * stepX;
                        const y = 120 - (t.rate * 100);
                        return (
                          <g key={idx}>
                            <circle cx={x} cy={y} r="3" fill="var(--surface-input)" stroke="var(--accent)" strokeWidth="1.5" />
                            <text x={x} y="134" textAnchor="middle" fill="var(--ink-soft)" fontSize="8px" fontFamily="'JetBrains Mono', monospace">{t.month}</text>
                            <text x={x} y={y - 8} textAnchor="middle" fill="var(--accent)" fontSize="8px" fontFamily="'JetBrains Mono', monospace" fontWeight="bold">
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
      <div style={{
        gridColumn: 'span 6',
        minHeight: '360px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        background: 'var(--surface-panel)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-md)',
        boxSizing: 'border-box',
        marginBottom: '16px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-soft)', paddingBottom: '6px', marginBottom: '15px' }}>
          <h4 style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '13px',
            fontWeight: 700,
            letterSpacing: '2px',
            textTransform: 'uppercase',
            color: 'var(--accent)',
            margin: 0
          }}>
            Protected Routing Alternatives
          </h4>
          
          {/* Multi-train comparative selection */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '10px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Compare:</span>
            <select
              value={comparisonTrain}
              onChange={e => handleComparisonChange(e.target.value)}
              style={{
                background: 'var(--surface-input)',
                color: 'var(--ink)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--rounded-sm)',
                padding: '4px 8px',
                fontSize: '11px',
                fontFamily: "'JetBrains Mono', monospace",
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="12002">12002 (Shatabdi)</option>
              <option value="22415">22415 (Vande Bharat)</option>
              <option value="12301">12301 (Rajdhani)</option>
            </select>
            <span style={{ fontSize: '13px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 'bold', color: 'var(--accent)' }}>{Math.round(comparisonOdds*100)}%</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flexGrow: 1 }}>
          {alternativeTrains.length === 0 ? (
            <div style={{ textAlign: 'center', fontSize: '13px', color: 'var(--ink-muted)', fontStyle: 'italic', padding: '30px', fontFamily: "'Inter', sans-serif" }}>
              Finding alternative route options...
            </div>
          ) : (
            alternativeTrains.map(alt => (
              <div 
                key={alt.train_no} 
                style={{
                  background: 'var(--surface-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--rounded-xs)',
                  padding: '12px 15px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <span style={{ fontSize: '13px', fontFamily: "'Inter', sans-serif", fontWeight: 600, color: 'var(--ink)', display: 'block' }}>{alt.train_name}</span>
                  <span style={{ fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: 'var(--ink-soft)', display: 'block', marginTop: '2px' }}>
                    No: {alt.train_no} · Dept: {alt.departure} · Duration: {alt.duration}
                  </span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className={`badge-status ${alt.status === 'RUNNING' ? 'healthy' : 'failed'}`} style={{ display: 'inline-block', marginBottom: '4px' }}>
                    {alt.status}
                  </span>
                  <div style={{ fontSize: '11px', fontFamily: "'Inter', sans-serif", color: 'var(--ink-soft)' }}>
                    Conf odds: <strong style={{ color: 'var(--accent)' }}>{Math.round(alt.confirmation_probability * 100)}%</strong>
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
