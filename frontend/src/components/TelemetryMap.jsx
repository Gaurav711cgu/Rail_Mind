import React from 'react';

export default function TelemetryMap({ trains, disruptions }) {
  // Map stations to X-coordinates on a 900x200 SVG canvas
  const stations = {
    "NDLS": { name: "New Delhi", x: 100, y: 100 },
    "GZB": { name: "Ghaziabad", x: 280, y: 100 },
    "ALJN": { name: "Aligarh", x: 550, y: 100 },
    "CNB": { name: "Kanpur Central", x: 800, y: 100 }
  };

  // Helper to find if a section is blocked by a disruption
  const isSectionDisrupted = (fromCode, toCode) => {
    return disruptions.some(d => 
      d.status === 'ACTIVE' && 
      ((d.section_from === fromCode && d.section_to === toCode) ||
       (d.section_from === fromCode && toCode === 'ALJN')) // Cascade extends
    );
  };

  // Get segment class names based on disruption state
  const getSegmentClass = (fromCode, toCode) => {
    if (isSectionDisrupted(fromCode, toCode)) {
      const activeDisp = disruptions.find(d => d.status === 'ACTIVE');
      return activeDisp?.severity === 'CRITICAL' ? 'track-line disrupted critical' : 'track-line disrupted';
    }
    return 'track-line';
  };

  // Map train state to visual representation
  const getTrainPosition = (train) => {
    const station = stations[train.current_station];
    if (station) {
      // Offset y slightly for multiple trains at the same station
      let yOffset = 0;
      if (train.train_no === "BOXN-902") yOffset = 18;
      if (train.train_no === "22415") yOffset = -18;
      return { x: station.x, y: station.y + yOffset };
    }
    
    // Fallback default coordinates
    return { x: 450, y: 100 };
  };

  return (
    <div className="glass-card" style={{ gridColumn: 'span 7', minHeight: '340px' }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Sector North Live Telemetry Corridor</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Delhi - Ghaziabad - Aligarh Corridor Segment</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.8rem' }}>
            <span className="led-indicator active"></span> Kavach Active
          </span>
        </div>
      </div>

      <div className="map-container" style={{ position: 'relative', overflowX: 'auto', background: 'var(--bg-terminal)', borderRadius: '8px', padding: '10px' }}>
        <svg viewBox="0 0 900 200" width="100%" height="180px" style={{ minWidth: '700px' }}>
          <defs>
            <linearGradient id="glow-danger" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FF3131" stopOpacity="1" />
              <stop offset="100%" stopColor="#FF9F00" stopOpacity="0.5" />
            </linearGradient>
            <filter id="svg-neon-glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>

          {/* SVG CSS Styles for animations */}
          <style>{`
            .track-line { stroke: var(--border-color); stroke-width: 4; stroke-dasharray: 8 6; }
            .track-line.disrupted { stroke: var(--color-warning); stroke-width: 5; animation: blink-yellow 1.5s infinite; filter: url(#svg-neon-glow); }
            .track-line.disrupted.critical { stroke: var(--color-danger); stroke-width: 6; animation: blink-red 1s infinite; }
            .station-circle { fill: #0F172A; stroke: var(--border-color); stroke-width: 3; transition: all 0.3s; }
            .station-circle.active { stroke: var(--color-primary); fill: #1E293B; filter: url(#svg-neon-glow); }
            .station-circle.danger { stroke: var(--color-danger); filter: url(#svg-neon-glow); }
            .train-node { transition: all 0.8s cubic-bezier(0.25, 1, 0.5, 1); cursor: pointer; }
            .train-node:hover { filter: drop-shadow(0px 0px 8px var(--color-primary)); }
            .pulse-ring { animation: pulse-ring-anim 2s infinite; stroke-width: 1.5; fill: none; }
            
            @keyframes blink-yellow { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
            @keyframes blink-red { 0%, 100% { opacity: 0.2; stroke: #800000; } 50% { opacity: 1; stroke: var(--color-danger); } }
            @keyframes pulse-ring-anim {
              0% { r: 12; opacity: 0.8; }
              100% { r: 28; opacity: 0; }
            }
          `}</style>

          {/* Rail Track segments */}
          <line x1="100" y1="100" x2="280" y2="100" className={getSegmentClass("NDLS", "GZB")} />
          <line x1="280" y1="100" x2="550" y2="100" className={getSegmentClass("GZB", "ALJN")} />
          <line x1="550" y1="100" x2="800" y2="100" className={getSegmentClass("ALJN", "CNB")} />

          {/* Station Pulsing Rings */}
          {disruptions.some(d => d.status === 'ACTIVE') && (
            <circle cx="280" cy="100" r="15" stroke="var(--color-danger)" className="pulse-ring" />
          )}

          {/* Station Nodes */}
          {Object.entries(stations).map(([code, station]) => {
            const hasDisruption = disruptions.some(d => d.status === 'ACTIVE' && d.section_from === code);
            let circleClass = "station-circle active";
            if (hasDisruption) circleClass = "station-circle danger";

            return (
              <g key={code}>
                <circle cx={station.x} cy={station.y} r="10" className={circleClass} />
                <text x={station.x} y={station.y - 20} textAnchor="middle" fill="var(--color-text-main)" fontSize="0.75rem" fontWeight="600">{station.name}</text>
                <text x={station.x} y={station.y + 24} textAnchor="middle" fill="var(--color-text-muted)" fontSize="0.65rem">{code}</text>
              </g>
            );
          })}

          {/* Active Trains */}
          {trains.map((train) => {
            const pos = getTrainPosition(train);
            const isDelayed = train.current_delay > 0;
            const trainColor = train.train_no === "BOXN-902" ? "var(--color-warning)" : isDelayed ? "var(--color-danger)" : "var(--color-primary)";
            
            return (
              <g key={train.train_no} className="train-node" transform={`translate(${pos.x}, ${pos.y})`}>
                <title>{`${train.train_name} (${train.train_no})\nStatus: ${train.status}\nDelay: ${train.current_delay}m`}</title>
                {/* Train marker shadow/glow */}
                <circle cx="0" cy="0" r="8" fill={trainColor} filter="url(#svg-neon-glow)" />
                {/* Inner white core */}
                <circle cx="0" cy="0" r="4" fill="#FFFFFF" />
                {/* Train Label badge */}
                <rect x="-35" y="-12" width="70" height="8" rx="2" fill="rgba(4, 6, 10, 0.8)" stroke={trainColor} strokeWidth="0.5" />
                <text x="0" y="-8" textAnchor="middle" fill="#FFFFFF" fontSize="0.5rem" fontWeight="700">
                  {train.train_no}
                </text>
                {/* Speed indicator or delay warning indicator */}
                {isDelayed && (
                  <g transform="translate(12, -10)">
                    <circle cx="0" cy="0" r="5" fill="var(--color-danger)" />
                    <text x="0" y="2" textAnchor="middle" fill="white" fontSize="0.45rem" fontWeight="bold">!</text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px', marginTop: '20px' }}>
        {trains.map(t => (
          <div key={t.train_no} style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{t.train_name}</span>
              <span style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', background: t.current_delay > 0 ? 'rgba(255, 49, 49, 0.15)' : 'rgba(57, 255, 20, 0.15)', color: t.current_delay > 0 ? 'var(--color-danger)' : 'var(--color-accent)' }}>
                {t.status}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              <span>No: {t.train_no}</span>
              <span>Delay: <strong style={{ color: t.current_delay > 0 ? 'var(--color-danger)' : 'inherit' }}>{t.current_delay} min</strong></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
