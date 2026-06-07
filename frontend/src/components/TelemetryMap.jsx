import React, { useState, useEffect, useRef } from 'react';

export default function TelemetryMap({ trains, disruptions, onNextStep, scenarioStep }) {
  // States for interactive features
  const [selectedTrain, setSelectedTrain] = useState(null);
  const [selectedDisruption, setSelectedDisruption] = useState(null);
  const [autoplay, setAutoplay] = useState(false);
  const [autoplayCountdown, setAutoplayCountdown] = useState(6); // 6s countdown
  const [viewMode, setViewMode] = useState('schematic'); // 'schematic' or 'geo'
  const [kavachStates, setKavachStates] = useState({
    "DLI-GZB": true,
    "GZB-ALJN": true,
    "ALJN-CNB": false
  });
  const [weatherState, setWeatherState] = useState({
    visibility_meters: 2200,
    fog_density: 12,
    wind_speed: 14,
    temperature: 29.5,
    active_warning: "NONE",
    recommended_speed_limit: 130
  });
  const [speedLimits, setSpeedLimits] = useState({
    "DLI-GZB": 110,
    "GZB-ALJN": 130,
    "ALJN-CNB": 130
  });
  const [metrics, setMetrics] = useState({
    efficiency_score: 94.5,
    capacity_load: 34.0,
    average_speed: 104.2,
    safety_index: 100.0
  });

  const timerRef = useRef(null);

  // Sync selected train data when scenario step updates
  useEffect(() => {
    if (selectedTrain) {
      const updated = trains.find(t => t.train_no === selectedTrain.train_no);
      if (updated) setSelectedTrain(updated);
    }
  }, [trains]);

  // Fetch metrics dynamically based on scenario step
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch('/api/v1/cascade/corridor-metrics');
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error("Failed to fetch corridor metrics", err);
      }
    };
    fetchMetrics();
  }, [scenarioStep]);

  // Autoplay handler
  useEffect(() => {
    if (autoplay) {
      timerRef.current = setInterval(() => {
        setAutoplayCountdown((prev) => {
          if (prev <= 1) {
            onNextStep();
            return 6;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [autoplay, onNextStep]);

  // Reset countdown if step changes manually
  useEffect(() => {
    setAutoplayCountdown(6);
  }, [scenarioStep]);

  // Handle Kavach toggles via backend
  const handleKavachToggle = async (sectionCode) => {
    const nextVal = !kavachStates[sectionCode];
    setKavachStates(prev => ({ ...prev, [sectionCode]: nextVal }));
    try {
      await fetch(`/api/v1/cascade/kavach-toggle?section_code=${sectionCode}&active=${nextVal}`, { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  // Handle speed limit overrides
  const handleSpeedLimitChange = async (sectionCode, newLimit) => {
    setSpeedLimits(prev => ({ ...prev, [sectionCode]: newLimit }));
    try {
      await fetch(`/api/v1/trains/speed-lock?section_code=${sectionCode}&speed_limit=${newLimit}`, { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  // Fog visibility simulation slider
  const handleVisibilitySlider = async (e) => {
    const visibility = parseInt(e.target.value);
    const density = Math.round((1 - (visibility / 3000)) * 100);
    const speedLimit = visibility < 500 ? 30 : visibility < 1000 ? 60 : 130;
    
    const nextWeather = {
      ...weatherState,
      visibility_meters: visibility,
      fog_density: density,
      recommended_speed_limit: speedLimit,
      active_warning: visibility < 500 ? "SEVERE_FOG_WARNING" : "NONE"
    };
    setWeatherState(nextWeather);

    try {
      await fetch(`/api/v1/cascade/weather?visibility=${visibility}&fog_density=${density}&speed_limit=${speedLimit}`, { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  // Station coordinate projection
  const stations = {
    "NDLS": { name: "New Delhi", x: 100, y_up: 70, y_down: 135 },
    "GZB": { name: "Ghaziabad", x: 280, y_up: 70, y_down: 135 },
    "ALJN": { name: "Aligarh", x: 550, y_up: 70, y_down: 135 },
    "CNB": { name: "Kanpur Central", x: 800, y_up: 70, y_down: 135 }
  };

  const stationsGeo = {
    "NDLS": { name: "New Delhi", lat: 28.643, lng: 77.222 },
    "GZB": { name: "Ghaziabad", lat: 28.672, lng: 77.436 },
    "ALJN": { name: "Aligarh", lat: 27.892, lng: 78.078 },
    "CNB": { name: "Kanpur Central", lat: 26.448, lng: 80.350 }
  };

  const mapRef = useRef(null);
  const leafletInstance = useRef(null);
  const markersRef = useRef({});

  // Leaflet map initialization
  useEffect(() => {
    if (viewMode === 'geo' && mapRef.current && !leafletInstance.current && window.L) {
      const L = window.L;
      
      const map = L.map(mapRef.current, {
        center: [27.5, 78.8],
        zoom: 7,
        zoomControl: false,
        attributionControl: false
      });

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 18
      }).addTo(map);

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      const stationCoords = [
        [28.643, 77.222], // NDLS
        [28.672, 77.436], // GZB
        [27.892, 78.078], // ALJN
        [26.448, 80.350]  // CNB
      ];

      // UP Track (Cyan)
      L.polyline(stationCoords, {
        color: '#00F0FF',
        weight: 3,
        opacity: 0.6,
        dashArray: '5, 8'
      }).addTo(map);

      // DOWN Track (Purple)
      L.polyline(stationCoords.map(c => [c[0] - 0.02, c[1] - 0.02]), {
        color: '#A855F7',
        weight: 3,
        opacity: 0.6,
        dashArray: '5, 8'
      }).addTo(map);

      // Station Pins
      Object.entries(stationsGeo).forEach(([code, station]) => {
        const outerCircle = L.circleMarker([station.lat, station.lng], {
          radius: 7,
          color: '#ffffff',
          weight: 1.5,
          fillColor: '#030712',
          fillOpacity: 1
        }).addTo(map);

        outerCircle.bindTooltip(`<strong style="color: var(--color-primary)">${station.name} (${code})</strong>`, {
          permanent: false,
          direction: 'top',
          className: 'custom-map-tooltip'
        });
      });

      leafletInstance.current = map;
    }

    return () => {
      if (leafletInstance.current) {
        leafletInstance.current.remove();
        leafletInstance.current = null;
        markersRef.current = {};
      }
    };
  }, [viewMode]);

  // Update train markers on live geographic map
  useEffect(() => {
    if (viewMode === 'geo' && leafletInstance.current && window.L) {
      const L = window.L;
      const map = leafletInstance.current;

      trains.forEach(train => {
        const lat = train.latitude;
        const lng = train.longitude;
        const isFreight = train.train_no === 'BOXN-902';
        const isDelayed = train.current_delay > 0;
        const trainColor = isFreight ? 'var(--color-warning)' : isDelayed ? 'var(--color-danger)' : 'var(--color-accent)';

        // Offset DOWN trains slightly so they align with the DOWN polyline
        const latOffset = train.train_no === '22415' ? 0 : -0.02;
        const lngOffset = train.train_no === '22415' ? 0 : -0.02;

        const tooltipContent = `
          <div style="font-family: monospace; font-size: 0.7rem; line-height: 1.3;">
            <strong style="color:#ffffff">${train.train_no}</strong><br/>
            <span style="color:${trainColor}">${train.train_name}</span><br/>
            Status: <strong>${train.status}</strong><br/>
            Speed: <strong>${train.train_no === '22415' ? '130' : isFreight ? '65' : '110'} km/h</strong>
            ${isDelayed ? `<br/><span style="color:var(--color-danger)">Delay: +${train.current_delay}m</span>` : ''}
          </div>
        `;

        if (markersRef.current[train.train_no]) {
          markersRef.current[train.train_no].setLatLng([lat + latOffset, lng + lngOffset]);
          markersRef.current[train.train_no].setStyle({ fillColor: trainColor, color: trainColor });
          markersRef.current[train.train_no].getTooltip().setContent(tooltipContent);
        } else {
          const marker = L.circleMarker([lat + latOffset, lng + lngOffset], {
            radius: 8,
            fillColor: trainColor,
            color: '#ffffff',
            weight: 1.5,
            fillOpacity: 1
          }).addTo(map);

          marker.bindTooltip(tooltipContent, {
            permanent: true,
            direction: 'top',
            offset: [0, -10],
            className: 'custom-map-tooltip'
          });

          marker.on('click', () => {
            setSelectedTrain(train);
            setSelectedDisruption(null);
          });

          markersRef.current[train.train_no] = marker;
        }
      });

      // Cleanup removed trains
      Object.keys(markersRef.current).forEach(trainNo => {
        if (!trains.some(t => t.train_no === trainNo)) {
          markersRef.current[trainNo].remove();
          delete markersRef.current[trainNo];
        }
      });
    }
  }, [trains, viewMode]);

  const isSectionDisrupted = (fromCode, toCode) => {
    return disruptions.some(d => 
      d.status === 'ACTIVE' && 
      ((d.section_from === fromCode && d.section_to === toCode) ||
       (d.section_from === fromCode && toCode === 'ALJN'))
    );
  };

  const getSegmentClass = (fromCode, toCode) => {
    if (isSectionDisrupted(fromCode, toCode)) {
      const activeDisp = disruptions.find(d => d.status === 'ACTIVE');
      return activeDisp?.severity === 'CRITICAL' ? 'disrupted critical' : 'disrupted';
    }
    return '';
  };

  const getTrainPosition = (train) => {
    const lon = train.longitude;
    let x = 450;
    
    if (lon <= 77.222) x = 100;
    else if (lon <= 77.436) x = 100 + ((lon - 77.222) / (77.436 - 77.222)) * 180;
    else if (lon <= 78.078) x = 280 + ((lon - 77.436) / (78.078 - 77.436)) * 270;
    else if (lon <= 80.350) x = 550 + ((lon - 78.078) / (80.350 - 78.078)) * 250;
    else x = 800;
    
    let y = train.train_no === "22415" ? 70 : 135;
    let xOffset = 0;
    if (train.train_no === "BOXN-902" && trains.some(t => t.train_no === "12002" && Math.abs(t.longitude - train.longitude) < 0.02)) {
      xOffset = 18;
    }

    return { x: x + xOffset, y };
  };

  const fetchDisruptionDetails = async (disp) => {
    setSelectedTrain(null);
    try {
      const res = await fetch(`/api/v1/cascade/disruption-details?disruption_id=${disp.id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedDisruption({ ...disp, ...data });
      }
    } catch (err) {
      console.error(err);
      setSelectedDisruption(disp);
    }
  };

  const drawTrackSegment = (fromCode, toCode, yCoord, isUpLine) => {
    const fromStation = stations[fromCode];
    const toStation = stations[toCode];
    const disruptionClass = getSegmentClass(fromCode, toCode);
    const trackColorClass = isUpLine ? 'up-line' : 'down-line';
    
    return (
      <g key={`${fromCode}-${toCode}-${yCoord}`}>
        <line 
          x1={fromStation.x} 
          y1={yCoord} 
          x2={toStation.x} 
          y2={yCoord} 
          className={`track-glow ${trackColorClass} ${disruptionClass}`}
        />
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
    <div className="glass-card" style={{ gridColumn: 'span 8', minHeight: '520px', display: 'flex', flexDirection: 'column', padding: '24px' }}>
      {/* Header Info */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
        <div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, letterSpacing: '0.5px' }}>Sector North Live Telemetry Corridor</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Interactive Indian Railways Kavach Interlocking Desk</p>
        </div>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          {/* View Mode Toggle */}
          <div className="toggle-group" style={{ display: 'flex', background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-color)', marginRight: '10px' }}>
            <button 
              onClick={() => setViewMode('schematic')} 
              style={{
                padding: '4px 10px',
                fontSize: '0.65rem',
                fontWeight: 'bold',
                background: viewMode === 'schematic' ? 'var(--color-primary)' : 'transparent',
                color: viewMode === 'schematic' ? 'black' : 'var(--color-text-muted)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              SCHEMATIC VIEW
            </button>
            <button 
              onClick={() => setViewMode('geo')} 
              style={{
                padding: '4px 10px',
                fontSize: '0.65rem',
                fontWeight: 'bold',
                background: viewMode === 'geo' ? 'var(--color-primary)' : 'transparent',
                color: viewMode === 'geo' ? 'black' : 'var(--color-text-muted)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              GEOGRAPHIC RADAR
            </button>
          </div>

          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-accent)' }}>
            <span className="led-indicator active" style={{ width: '8px', height: '8px' }}></span> KAVACH DESK SYNCED
          </span>
        </div>
      </div>

      {/* SVG Railway Track Map or Geographic Map */}
      {viewMode === 'schematic' ? (
        <div className="map-container" style={{ position: 'relative', background: 'var(--bg-terminal)', borderRadius: '10px', padding: '15px', border: '1px solid var(--border-color)', marginBottom: '20px' }}>
          <svg viewBox="0 0 900 220" width="100%" height="190px" style={{ minWidth: '700px' }}>
            <defs>
              <filter id="svg-neon-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <pattern id="radar-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(255, 255, 255, 0.01)" strokeWidth="1" />
              </pattern>
            </defs>

            <rect width="900" height="220" fill="url(#radar-grid)" />

            <style>{`
              .track-glow { stroke-width: 8; stroke-linecap: round; opacity: 0.12; transition: all 0.5s; }
              .track-glow.up-line { stroke: var(--color-primary); }
              .track-glow.down-line { stroke: var(--color-secondary); }
              .track-glow.disrupted { stroke: var(--color-warning); opacity: 0.35; animation: pulse-glow 1.5s infinite; filter: url(#svg-neon-glow); }
              .track-glow.disrupted.critical { stroke: var(--color-danger); opacity: 0.45; animation: pulse-glow-fast 1s infinite; filter: url(#svg-neon-glow); }
              
              .track-core { stroke-width: 2.5; stroke-linecap: round; stroke-dasharray: 6 5; transition: all 0.5s; }
              .track-core.up-line { stroke: var(--color-primary); opacity: 0.5; }
              .track-core.down-line { stroke: var(--color-secondary); opacity: 0.5; }
              .track-core.disrupted { stroke: var(--color-warning); opacity: 0.8; animation: blink-yellow 1.5s infinite; }
              .track-core.disrupted.critical { stroke: var(--color-danger); opacity: 0.95; animation: blink-red 1s infinite; }

              .crossover-line { stroke: rgba(255, 255, 255, 0.06); stroke-width: 1.5; stroke-dasharray: 3 3; }
              .crossover-line.active { stroke: var(--color-primary); opacity: 0.3; }

              .station-outer { fill: #030712; stroke: rgba(255, 255, 255, 0.1); stroke-width: 1.5; cursor: pointer; transition: all 0.3s; }
              .station-outer.active { stroke: var(--color-primary); }
              .station-outer.danger { stroke: var(--color-danger); filter: url(#svg-neon-glow); }
              .station-inner { fill: rgba(255, 255, 255, 0.15); transition: all 0.3s; }
              .station-inner.active { fill: var(--color-primary); }
              .station-inner.danger { fill: var(--color-danger); }
              
              .train-node { transition: all 0.8s cubic-bezier(0.25, 1, 0.5, 1); cursor: pointer; }
              .train-node:hover { filter: drop-shadow(0px 0px 8px var(--color-primary)); }
              .train-label-bg { fill: #090d16; stroke-width: 1; }
              
              @keyframes pulse-glow { 0%, 100% { opacity: 0.15; } 50% { opacity: 0.4; } }
              @keyframes pulse-glow-fast { 0%, 100% { opacity: 0.25; } 50% { opacity: 0.6; } }
              @keyframes blink-yellow { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
              @keyframes blink-red { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
            `}</style>

            {/* Draw Station Crossovers */}
            {Object.values(stations).map((s, idx) => (
              <line 
                key={`cross-${idx}`} 
                x1={s.x} 
                y1={s.y_up} 
                x2={s.x} 
                y2={s.y_down} 
                className={`crossover-line ${disruptions.some(d => d.status === 'ACTIVE' && d.section_from === Object.keys(stations)[idx]) ? 'active' : ''}`}
              />
            ))}

            {/* UP Line Segments */}
            {drawTrackSegment("NDLS", "GZB", 70, true)}
            {drawTrackSegment("GZB", "ALJN", 70, true)}
            {drawTrackSegment("ALJN", "CNB", 70, true)}

            {/* DOWN Line Segments */}
            {drawTrackSegment("NDLS", "GZB", 135, false)}
            {drawTrackSegment("GZB", "ALJN", 135, false)}
            {drawTrackSegment("ALJN", "CNB", 135, false)}

            {/* Station Platform Nodes */}
            {Object.entries(stations).map(([code, station]) => {
              const disp = disruptions.find(d => d.status === 'ACTIVE' && d.section_from === code);
              const hasDisruption = !!disp;

              let outerClass = hasDisruption ? "station-outer danger" : "station-outer active";
              let innerClass = hasDisruption ? "station-inner danger" : "station-inner active";

              return (
                <g key={code} onClick={() => hasDisruption ? fetchDisruptionDetails(disp) : null}>
                  <rect x={station.x - 4} y={station.y_up - 6} width="8" height={station.y_down - station.y_up + 12} rx="2" fill="rgba(255, 255, 255, 0.02)" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" />
                  
                  <circle cx={station.x} cy={station.y_up} r="8" className={outerClass} />
                  <circle cx={station.x} cy={station.y_up} r="3.5" className={innerClass} />

                  <circle cx={station.x} cy={station.y_down} r="8" className={outerClass} />
                  <circle cx={station.x} cy={station.y_down} r="3.5" className={innerClass} />

                  <rect x={station.x - 45} y="180" width="90" height="26" rx="4" fill="rgba(3, 5, 10, 0.85)" stroke="var(--border-color)" strokeWidth="1" />
                  <text x={station.x} y="192" textAnchor="middle" fill="var(--color-text-main)" fontSize="0.65rem" fontWeight="800" letterSpacing="0.5px">{station.name}</text>
                  <text x={station.x} y="203" textAnchor="middle" fill="var(--color-primary)" fontSize="0.55rem" fontWeight="600" letterSpacing="1px">{code}</text>
                </g>
              );
            })}

            {/* Active Train Nodes */}
            {trains.map((train) => {
              const pos = getTrainPosition(train);
              const isDelayed = train.current_delay > 0;
              const isFreight = train.train_no === "BOXN-902";
              
              const trainColor = isFreight ? "var(--color-warning)" : isDelayed ? "var(--color-danger)" : "var(--color-accent)";
              
              return (
                <g key={train.train_no} className="train-node" transform={`translate(${pos.x}, ${pos.y})`} onClick={() => { setSelectedTrain(train); setSelectedDisruption(null); }}>
                  {/* Double Pulsing Radar Rings using native SVG <animate> */}
                  <circle cx="0" cy="0" r="7.5" fill="none" stroke={trainColor} strokeWidth="1.2" opacity="0.8">
                    <animate attributeName="r" values="7.5;22" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.8;0" dur="2s" repeatCount="indefinite" />
                  </circle>
                  <circle cx="0" cy="0" r="7.5" fill="none" stroke={trainColor} strokeWidth="1.2" opacity="0.8">
                    <animate attributeName="r" values="7.5;22" dur="2s" begin="1s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.8;0" dur="2s" begin="1s" repeatCount="indefinite" />
                  </circle>

                  {/* Train Core Node */}
                  <circle cx="0" cy="0" r="8" fill={trainColor} filter="url(#svg-neon-glow)" />
                  
                  {/* Direction Chevrons (UP: ▶, DOWN: ◀) */}
                  {pos.y === 70 ? (
                    <path d="M-1.5,-3 L2,0 L-1.5,3" fill="none" stroke="#FFFFFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  ) : (
                    <path d="M1.5,-3 L-2,0 L1.5,3" fill="none" stroke="#FFFFFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  )}

                  <g transform={`translate(0, ${pos.y === 70 ? -24 : 24})`}>
                    <rect x="-35" y="-10" width="70" height="15" rx="3" className="train-label-bg" fill="#030712" stroke={trainColor} strokeWidth="1" />
                    <text x="0" y="0.5" textAnchor="middle" fill="var(--color-text-main)" fontSize="0.55rem" fontWeight="800" letterSpacing="0.5px">
                      {train.train_no}
                    </text>
                    {isDelayed && (
                      <text x="0" y="10" textAnchor="middle" fill="var(--color-danger)" fontSize="0.45rem" fontWeight="700">
                        +{train.current_delay}m
                      </text>
                    )}
                  </g>
                </g>
              );
            })}
          </svg>
        </div>
      ) : (
        <div className="map-container" style={{ position: 'relative', background: '#030712', borderRadius: '10px', height: '190px', border: '1px solid var(--border-color)', marginBottom: '20px', overflow: 'hidden' }}>
          <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
        </div>
      )}

      {/* Grid: 3 Interactive Control Panels */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.5fr 1.3fr', gap: '15px' }}>
        
        {/* Panel 1: Weather & Kavach Control */}
        <div style={{ background: 'rgba(255,255,255,0.01)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h4 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
            Sensors & Kavach
          </h4>
          
          {/* Weather Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '3px' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Visibility</span>
              <span style={{ color: weatherState.visibility_meters < 500 ? 'var(--color-danger)' : 'var(--color-accent)', fontWeight: 700 }}>
                {weatherState.visibility_meters}m {weatherState.active_warning !== 'NONE' && '⚠️'}
              </span>
            </div>
            <input 
              type="range" 
              min="100" 
              max="3000" 
              step="100"
              value={weatherState.visibility_meters} 
              onChange={handleVisibilitySlider}
              style={{ width: '100%', height: '3px', background: 'var(--border-color)', outline: 'none', appearance: 'none', cursor: 'pointer' }}
            />
          </div>

          {/* Kavach toggles */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '4px' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Kavach Segment Links:</span>
            {Object.keys(kavachStates).map(sec => (
              <label key={sec} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.7rem', background: 'rgba(0,0,0,0.15)', padding: '6px 8px', borderRadius: '4px', cursor: 'pointer' }}>
                <span style={{ fontWeight: 600 }}>{sec}</span>
                <input 
                  type="checkbox" 
                  checked={kavachStates[sec]} 
                  onChange={() => handleKavachToggle(sec)}
                  style={{ accentColor: 'var(--color-primary)' }}
                />
              </label>
            ))}
          </div>
        </div>

        {/* Panel 2: Telemetry Inspector */}
        <div style={{ background: 'rgba(255,255,255,0.01)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
          <h4 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px', marginBottom: '10px' }}>
            Telemetry Inspector
          </h4>
          
          {!selectedTrain && !selectedDisruption ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: '0.7rem', color: 'var(--color-text-dark)', fontStyle: 'italic', textAlign: 'center', padding: '10px' }}>
              Click on a train node or warning platform to inspect telemetry.
            </div>
          ) : selectedTrain ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 800, color: 'white' }}>{selectedTrain.train_name}</span>
                <span style={{ color: 'var(--color-accent)', fontWeight: 700 }}>{selectedTrain.train_no}</span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px', background: 'rgba(0,0,0,0.2)', padding: '6px', borderRadius: '4px', fontSize: '0.65rem' }}>
                <div>Station: <strong style={{ color: 'white' }}>{selectedTrain.current_station}</strong></div>
                <div>Status: <strong style={{ color: 'white' }}>{selectedTrain.status}</strong></div>
                <div>Lat: <strong style={{ color: 'white' }}>{selectedTrain.latitude}</strong></div>
                <div>Lon: <strong style={{ color: 'white' }}>{selectedTrain.longitude}</strong></div>
              </div>

              {/* Interactive Speed limit lock */}
              <div style={{ marginTop: '4px' }}>
                <label style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'block', marginBottom: '3px' }}>Safety Speed Lock:</label>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {[30, 60, 110, 130].map(sp => (
                    <button 
                      key={sp}
                      onClick={() => handleSpeedLimitChange("GZB-ALJN", sp)}
                      style={{
                        flex: 1,
                        background: speedLimits["GZB-ALJN"] === sp ? 'var(--color-primary)' : 'rgba(255,255,255,0.02)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '3px',
                        color: speedLimits["GZB-ALJN"] === sp ? 'black' : 'white',
                        fontSize: '0.6rem',
                        fontWeight: 'bold',
                        padding: '3px 0',
                        cursor: 'pointer'
                      }}
                    >
                      {sp}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 800, color: 'var(--color-danger)' }}>DISRUPTION ACTIVE</span>
                <span style={{ color: 'white', fontFamily: 'monospace' }}>{selectedDisruption.error_code}</span>
              </div>
              <p style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', lineHeight: '1.3' }}>
                {selectedDisruption.details}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', background: 'rgba(255,49,49,0.05)', padding: '5px 8px', borderRadius: '4px', border: '1px solid rgba(255,49,49,0.1)' }}>
                <span>Clearance: <strong>{selectedDisruption.estimated_clearance_minutes}m</strong></span>
                <span>Passengers: <strong>{selectedDisruption.affected_passengers}</strong></span>
              </div>
            </div>
          )}
        </div>

        {/* Panel 3: Performance & Autoplay */}
        <div style={{ background: 'rgba(255,255,255,0.01)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyStyle: 'stretch', gap: '10px' }}>
          <h4 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
            System Core Metrics
          </h4>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.7rem' }}>
            <div style={{ background: 'rgba(0,0,0,0.15)', padding: '6px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.55rem' }}>LINE EFFICIENCY</div>
              <div style={{ fontWeight: 800, color: 'var(--color-accent)', fontSize: '0.9rem' }}>{metrics.efficiency_score}%</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.15)', padding: '6px', borderRadius: '4px', textAlign: 'center' }}>
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.55rem' }}>CAPACITY LOAD</div>
              <div style={{ fontWeight: 800, color: 'var(--color-primary)', fontSize: '0.9rem' }}>{metrics.capacity_load}%</div>
            </div>
          </div>

          {/* Autoplay controllers */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: 'auto' }}>
            <button 
              className={autoplay ? "btn-secondary" : "btn-primary"} 
              onClick={() => setAutoplay(!autoplay)}
              style={{
                width: '100%', 
                padding: '6px', 
                fontSize: '0.7rem', 
                background: autoplay ? 'transparent' : 'linear-gradient(135deg, var(--color-primary), rgba(0, 240, 255, 0.4))',
                borderColor: autoplay ? 'var(--color-danger)' : '',
                color: autoplay ? 'var(--color-danger)' : 'black'
              }}
            >
              {autoplay ? "PAUSE AUTOPLAY" : "START AUTOPLAY"}
            </button>
            {autoplay && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ flexGrow: 1, height: '3px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: `${(autoplayCountdown / 6) * 100}%`, height: '100%', background: 'var(--color-primary)', transition: 'width 1s linear' }} />
                </div>
                <span style={{ fontSize: '0.55rem', color: 'var(--color-text-muted)' }}>{autoplayCountdown}s</span>
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
