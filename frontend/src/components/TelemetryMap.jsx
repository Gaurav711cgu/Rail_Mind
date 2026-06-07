import React from 'react';

export default function TelemetryMap({ trains, disruptions }) {
  // Map stations to X-coordinates on a 900x240 SVG canvas
  const stations = {
    "NDLS": { name: "New Delhi", x: 100, y_up: 80, y_down: 140 },
    "GZB": { name: "Ghaziabad", x: 280, y_up: 80, y_down: 140 },
    "ALJN": { name: "Aligarh", x: 550, y_up: 80, y_down: 140 },
    "CNB": { name: "Kanpur Central", x: 800, y_up: 80, y_down: 140 }
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
      return activeDisp?.severity === 'CRITICAL' ? 'disrupted critical' : 'disrupted';
    }
    return '';
  };

  // Map train GPS longitude to visual X coordinate, and train direction/no to Y coordinate
  const getTrainPosition = (train) => {
    const lon = train.longitude;
    let x = 450; // default middle fallback
    
    // Project longitude mapping NDLS(77.222) -> GZB(77.436) -> ALJN(78.078) -> CNB(80.350)
    if (lon <= 77.222) {
      x = 100;
    } else if (lon <= 77.436) {
      const pct = (lon - 77.222) / (77.436 - 77.222);
      x = 100 + pct * (280 - 100);
    } else if (lon <= 78.078) {
      const pct = (lon - 77.436) / (78.078 - 77.436);
      x = 280 + pct * (550 - 280);
    } else if (lon <= 80.350) {
      const pct = (lon - 78.078) / (80.350 - 78.078);
      x = 550 + pct * (800 - 550);
    } else {
      x = 800;
    }
    
    // Determine track Y coordinate:
    // Train 22415 (Vande Bharat) is UP line -> Y = 80
    // Train 12002 (Shatabdi) and BOXN-902 (Freight) are DOWN line -> Y = 140
    let y = 140;
    if (train.train_no === "22415") {
      y = 80;
    }
    
    // Add micro-offset to prevent overlapping if they share similar longitude
    let xOffset = 0;
    if (train.train_no === "BOXN-902" && trains.some(t => t.train_no === "12002" && Math.abs(t.longitude - train.longitude) < 0.02)) {
      xOffset = 18;
    }

    return { x: x + xOffset, y };
  };

  const drawTrackSegment = (fromCode, toCode, yCoord, isUpLine) => {
    const fromStation = stations[fromCode];
    const toStation = stations[toCode];
    const disruptionClass = getSegmentClass(fromCode, toCode);
    const trackColorClass = isUpLine ? 'up-line' : 'down-line';
    
    return (
      <g key={`${fromCode}-${toCode}-${yCoord}`}>
        {/* Glow backdrop line */}
        <line 
          x1={fromStation.x} 
          y1={yCoord} 
          x2={toStation.x} 
          y2={yCoord} 
          className={`track-glow ${trackColorClass} ${disruptionClass}`}
        />
        {/* Solid core line */}
        <line 
          x1={fromStation.x} 
          y1={yCoord} 
          x2={toStation.x} 
          y2={yCoord} 
          className={`track-core ${trackColorClass} ${disruptionClass}`}
        />
      </g>
    );
  };

  return (
    <div className="glass-card" style={{ gridColumn: 'span 8', minHeight: '380px', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: '0.5px' }}>Sector North Live Telemetry Corridor</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Delhi - Ghaziabad - Aligarh Corridor Segment</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-accent)' }}>
            <span className="led-indicator active" style={{ width: '8px', height: '8px' }}></span> KAVACH TELEMETRY ACTIVE
          </span>
        </div>
      </div>

      <div className="map-container" style={{ position: 'relative', overflowX: 'auto', background: 'var(--bg-terminal)', borderRadius: '10px', padding: '15px', border: '1px solid var(--border-color)', flexGrow: 1 }}>
        <svg viewBox="0 0 900 220" width="100%" height="200px" style={{ minWidth: '700px' }}>
          <defs>
            <filter id="svg-neon-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            
            <pattern id="radar-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.012)" strokeWidth="1" />
            </pattern>
          </defs>

          {/* Grid Background */}
          <rect width="900" height="220" fill="url(#radar-grid)" />

          <style>{`
            .track-glow { stroke-width: 8; stroke-linecap: round; opacity: 0.15; transition: all 0.5s; }
            .track-glow.up-line { stroke: var(--color-primary); }
            .track-glow.down-line { stroke: var(--color-secondary); }
            .track-glow.disrupted { stroke: var(--color-warning); opacity: 0.4; animation: pulse-glow 1.5s infinite; filter: url(#svg-neon-glow); }
            .track-glow.disrupted.critical { stroke: var(--color-danger); opacity: 0.5; animation: pulse-glow-fast 1s infinite; }
            
            .track-core { stroke-width: 2.5; stroke-linecap: round; stroke-dasharray: 6 5; transition: all 0.5s; }
            .track-core.up-line { stroke: var(--color-primary); opacity: 0.6; }
            .track-core.down-line { stroke: var(--color-secondary); opacity: 0.6; }
            .track-core.disrupted { stroke: var(--color-warning); opacity: 0.9; animation: blink-yellow 1.5s infinite; }
            .track-core.disrupted.critical { stroke: var(--color-danger); opacity: 1; animation: blink-red 1s infinite; }

            .crossover-line { stroke: rgba(255, 255, 255, 0.08); stroke-width: 1.5; stroke-dasharray: 3 3; }
            .crossover-line.active { stroke: var(--color-primary); opacity: 0.3; }

            .station-outer { fill: #080D1A; stroke: rgba(255, 255, 255, 0.15); stroke-width: 1.5; transition: all 0.3s; }
            .station-outer.active { stroke: var(--color-primary); filter: url(#svg-neon-glow); }
            .station-outer.danger { stroke: var(--color-danger); filter: url(#svg-neon-glow); }
            .station-inner { fill: rgba(255, 255, 255, 0.2); transition: all 0.3s; }
            .station-inner.active { fill: var(--color-primary); }
            .station-inner.danger { fill: var(--color-danger); }
            
            .train-node { transition: all 0.8s cubic-bezier(0.25, 1, 0.5, 1); cursor: pointer; }
            .train-node:hover { filter: drop-shadow(0px 0px 8px var(--color-primary)); }
            .train-label-bg { fill: rgba(5, 8, 16, 0.9); stroke-width: 1; }
            
            @keyframes pulse-glow { 0%, 100% { opacity: 0.2; } 50% { opacity: 0.5; } }
            @keyframes pulse-glow-fast { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.7; } }
            @keyframes blink-yellow { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
            @keyframes blink-red { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
          `}</style>

          {/* Draw Station Cross-over switch tracks */}
          {Object.values(stations).map((s, idx) => (
            <line 
              key={`cross-${idx}`} 
              x1={s.x} 
              y1="80" 
              x2={s.x} 
              y2="140" 
              className={`crossover-line ${disruptions.some(d => d.status === 'ACTIVE' && d.section_from === Object.keys(stations)[idx]) ? 'active' : ''}`}
            />
          ))}

          {/* UP Line Segments (y = 80) */}
          {drawTrackSegment("NDLS", "GZB", 80, true)}
          {drawTrackSegment("GZB", "ALJN", 80, true)}
          {drawTrackSegment("ALJN", "CNB", 80, true)}

          {/* DOWN Line Segments (y = 140) */}
          {drawTrackSegment("NDLS", "GZB", 140, false)}
          {drawTrackSegment("GZB", "ALJN", 140, false)}
          {drawTrackSegment("ALJN", "CNB", 140, false)}

          {/* Station Nodes */}
          {Object.entries(stations).map(([code, station]) => {
            const hasDisruption = disruptions.some(d => d.status === 'ACTIVE' && d.section_from === code);
            const isActive = !hasDisruption;

            let outerClass = "station-outer active";
            let innerClass = "station-inner active";
            if (hasDisruption) {
              outerClass = "station-outer danger";
              innerClass = "station-inner danger";
            }

            return (
              <g key={code}>
                {/* Station Central Junction platform bars */}
                <rect x={station.x - 4} y="74" width="8" height="72" rx="2" fill="rgba(255, 255, 255, 0.04)" stroke="rgba(255, 255, 255, 0.1)" strokeWidth="1" />
                
                {/* UP Platform Junction node */}
                <circle cx={station.x} cy="80" r="8" className={outerClass} />
                <circle cx={station.x} cy="80" r="3.5" className={innerClass} />

                {/* DOWN Platform Junction node */}
                <circle cx={station.x} cy="140" r="8" className={outerClass} />
                <circle cx={station.x} cy="140" r="3.5" className={innerClass} />

                {/* Labels */}
                <rect x={station.x - 50} y="176" width="100" height="28" rx="4" fill="rgba(6, 10, 18, 0.7)" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                <text x={station.x} y="188" textAnchor="middle" fill="var(--color-text-main)" fontSize="0.7rem" fontWeight="700" letterSpacing="0.5px">{station.name}</text>
                <text x={station.x} y="199" textAnchor="middle" fill="var(--color-primary)" fontSize="0.6rem" fontWeight="600" letterSpacing="1px">{code}</text>
              </g>
            );
          })}

          {/* Active Trains */}
          {trains.map((train) => {
            const pos = getTrainPosition(train);
            const isDelayed = train.current_delay > 0;
            const isFreight = train.train_no === "BOXN-902";
            
            // Neon colors
            const trainColor = isFreight ? "var(--color-warning)" : isDelayed ? "var(--color-danger)" : "var(--color-accent)";
            const glowShadow = isFreight ? "var(--shadow-neon-purple)" : isDelayed ? "var(--shadow-neon-red)" : "var(--shadow-neon-cyan)";
            
            return (
              <g key={train.train_no} className="train-node" transform={`translate(${pos.x}, ${pos.y})`}>
                <title>{`${train.train_name} (${train.train_no})\nStatus: ${train.status}\nDelay: ${train.current_delay}m`}</title>
                
                {/* Outer pulsing glow */}
                <circle cx="0" cy="0" r="12" fill="transparent" stroke={trainColor} strokeWidth="1" opacity="0.3" className="pulse-ring" style={{ animationDuration: isDelayed ? '1s' : '2.5s' }} />
                
                {/* Main Train circular coordinate */}
                <circle cx="0" cy="0" r="7" fill={trainColor} filter="url(#svg-neon-glow)" />
                <circle cx="0" cy="0" r="3" fill="#FFFFFF" />

                {/* Train Info Badge - positioned above for UP line, below for DOWN line */}
                <g transform={`translate(0, ${pos.y === 80 ? -24 : 24})`}>
                  <rect x="-35" y="-10" width="70" height="15" rx="3" className="train-label-bg" fill="#0A0F1D" stroke={trainColor} strokeWidth="1" />
                  <text x="0" y="0" textAnchor="middle" fill="var(--color-text-main)" fontSize="0.55rem" fontWeight="700" letterSpacing="0.5px">
                    {train.train_no}
                  </text>
                  {isDelayed && (
                    <text x="0" y="10" textAnchor="middle" fill="var(--color-danger)" fontSize="0.45rem" fontWeight="700">
                      +{train.current_delay}m
                    </text>
                  )}
                </g>

                {/* Hazard marker */}
                {isDelayed && (
                  <g transform="translate(11, -9)">
                    <circle cx="0" cy="0" r="5.5" fill="var(--color-danger)" stroke="#080C14" strokeWidth="1" />
                    <text x="0" y="2" textAnchor="middle" fill="white" fontSize="0.45rem" fontWeight="900">!</text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px', marginTop: '15px' }}>
        {trains.map(t => {
          const isDelayed = t.current_delay > 0;
          return (
            <div key={t.train_no} style={{ background: 'var(--bg-card)', padding: '12px 15px', borderRadius: '8px', border: `1px solid ${isDelayed ? 'rgba(255, 49, 49, 0.15)' : 'var(--border-color)'}`, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: t.train_no === 'BOXN-902' ? 'var(--color-warning)' : 'var(--color-text-main)' }}>{t.train_name}</span>
                <span style={{ fontSize: '0.65rem', padding: '2px 8px', borderRadius: '4px', background: t.status === 'HELD' ? 'rgba(255, 49, 49, 0.1)' : 'rgba(57, 255, 20, 0.1)', color: t.status === 'HELD' ? 'var(--color-danger)' : 'var(--color-accent)', fontWeight: 700 }}>
                  {t.status}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                <span>Train No: <strong style={{ color: 'var(--color-text-main)' }}>{t.train_no}</strong></span>
                <span>Delay: <strong style={{ color: isDelayed ? 'var(--color-danger)' : 'var(--color-accent)' }}>{t.current_delay} min</strong></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
