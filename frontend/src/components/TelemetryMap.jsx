import React, { useState, useEffect, useRef } from 'react';

export default function TelemetryMap({ trains, disruptions, onNextStep, scenarioStep }) {
  // States for interactive features
  const [selectedTrain, setSelectedTrain] = useState(null);
  const [selectedDisruption, setSelectedDisruption] = useState(null);
  const [autoplay, setAutoplay] = useState(false);
  const [autoplayCountdown, setAutoplayCountdown] = useState(6); // 6s countdown
  const [viewMode, setViewMode] = useState('schematic'); // 'schematic' or 'geo'
  const [selectedZone, setSelectedZone] = useState('NORTH'); // 'NORTH', 'WEST', 'SOUTH', 'ALL'
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

  // Helper to generate mock trains for Western and Southern zones based on step
  const getTrainsForZone = () => {
    if (selectedZone === 'NORTH') {
      return trains;
    }
    
    const step = scenarioStep;
    
    if (selectedZone === 'WEST') {
      return [
        {
          train_no: "12009",
          train_name: "MMCT-ADI Shatabdi Express",
          current_station: step <= 1 ? "MMCT" : step <= 4 ? "ST" : "BRC",
          current_delay: step === 3 ? 15 : 0,
          status: step === 1 ? "HELD" : "RUNNING",
          latitude: 18.971 + (step / 6) * (23.027 - 18.971),
          longitude: 72.820 + (step / 6) * (72.601 - 72.820)
        },
        {
          train_no: "20901",
          train_name: "Mumbai-Gandhinagar Vande Bharat",
          current_station: step <= 2 ? "BRC" : "ADI",
          current_delay: 0,
          status: "RUNNING",
          latitude: 22.312 + (step / 6) * (23.027 - 22.312),
          longitude: 73.181 + (step / 6) * (72.601 - 73.181)
        },
        {
          train_no: "CONCOR-701",
          train_name: "Container Cargo Freight",
          current_station: "ST",
          current_delay: step >= 4 ? 30 : 5,
          status: step >= 4 ? "HELD_AT_LOOP" : "RUNNING",
          latitude: 21.205,
          longitude: 72.841
        }
      ];
    }
    
    if (selectedZone === 'SOUTH') {
      return [
        {
          train_no: "12008",
          train_name: "SBC-MAS Shatabdi Express",
          current_station: step <= 2 ? "SBC" : step <= 4 ? "BWT" : "JTJ",
          current_delay: step >= 3 ? 20 : 0,
          status: step === 2 ? "HELD" : "RUNNING",
          latitude: 12.978 + (step / 6) * (13.082 - 12.978),
          longitude: 77.572 + (step / 6) * (80.275 - 77.572)
        },
        {
          train_no: "20608",
          train_name: "SBC-MAS Vande Bharat",
          current_station: step <= 1 ? "JTJ" : "MAS",
          current_delay: 0,
          status: "RUNNING",
          latitude: 12.571 + (step / 6) * (13.082 - 12.571),
          longitude: 78.580 + (step / 6) * (80.275 - 78.580)
        },
        {
          train_no: "BOXN-505",
          train_name: "Steel Ore Cargo",
          current_station: "BWT",
          current_delay: step >= 3 ? 25 : 10,
          status: step >= 3 ? "HELD_AT_LOOP" : "RUNNING",
          latitude: 12.969,
          longitude: 78.204
        }
      ];
    }

    if (selectedZone === 'ALL') {
      const north = trains;
      const west = [
        {
          train_no: "12009",
          train_name: "MMCT-ADI Shatabdi Express",
          current_station: step <= 1 ? "MMCT" : step <= 4 ? "ST" : "BRC",
          current_delay: step === 3 ? 15 : 0,
          status: step === 1 ? "HELD" : "RUNNING",
          latitude: 18.971 + (step / 6) * (23.027 - 18.971),
          longitude: 72.820 + (step / 6) * (72.601 - 72.820)
        },
        {
          train_no: "20901",
          train_name: "Mumbai-Gandhinagar Vande Bharat",
          current_station: step <= 2 ? "BRC" : "ADI",
          current_delay: 0,
          status: "RUNNING",
          latitude: 22.312 + (step / 6) * (23.027 - 22.312),
          longitude: 73.181 + (step / 6) * (72.601 - 73.181)
        },
        {
          train_no: "CONCOR-701",
          train_name: "Container Cargo Freight",
          current_station: "ST",
          current_delay: step >= 4 ? 30 : 5,
          status: step >= 4 ? "HELD_AT_LOOP" : "RUNNING",
          latitude: 21.205,
          longitude: 72.841
        }
      ];
      const south = [
        {
          train_no: "12008",
          train_name: "SBC-MAS Shatabdi Express",
          current_station: step <= 2 ? "SBC" : step <= 4 ? "BWT" : "JTJ",
          current_delay: step >= 3 ? 20 : 0,
          status: step === 2 ? "HELD" : "RUNNING",
          latitude: 12.978 + (step / 6) * (13.082 - 12.978),
          longitude: 77.572 + (step / 6) * (80.275 - 77.572)
        },
        {
          train_no: "20608",
          train_name: "SBC-MAS Vande Bharat",
          current_station: step <= 1 ? "JTJ" : "MAS",
          current_delay: 0,
          status: "RUNNING",
          latitude: 12.571 + (step / 6) * (13.082 - 12.571),
          longitude: 78.580 + (step / 6) * (80.275 - 78.580)
        },
        {
          train_no: "BOXN-505",
          train_name: "Steel Ore Cargo",
          current_station: "BWT",
          current_delay: step >= 3 ? 25 : 10,
          status: step >= 3 ? "HELD_AT_LOOP" : "RUNNING",
          latitude: 12.969,
          longitude: 78.204
        }
      ];
      return [...north, ...west, ...south];
    }
    
    return trains;
  };

  const getStationsForZone = () => {
    if (selectedZone === 'WEST') {
      return {
        "MMCT": { name: "Mumbai Central", x: 100, y_up: 70, y_down: 135 },
        "ST": { name: "Surat", x: 280, y_up: 70, y_down: 135 },
        "BRC": { name: "Vadodara Jn", x: 550, y_up: 70, y_down: 135 },
        "ADI": { name: "Ahmedabad Jn", x: 800, y_up: 70, y_down: 135 }
      };
    }
    if (selectedZone === 'SOUTH') {
      return {
        "SBC": { name: "KSR Bengaluru", x: 100, y_up: 70, y_down: 135 },
        "BWT": { name: "Bangarapet", x: 280, y_up: 70, y_down: 135 },
        "JTJ": { name: "Jolarpettai", x: 550, y_up: 70, y_down: 135 },
        "MAS": { name: "Chennai Central", x: 800, y_up: 70, y_down: 135 }
      };
    }
    return stations;
  };

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

      // Station coordinates
      const northCoords = [
        [28.643, 77.222], // NDLS
        [28.672, 77.436], // GZB
        [27.892, 78.078], // ALJN
        [26.448, 80.350]  // CNB
      ];
      const westCoords = [
        [18.971, 72.820], // MMCT
        [21.205, 72.841], // ST
        [22.312, 73.181], // BRC
        [23.027, 72.601]  // ADI
      ];
      const southCoords = [
        [12.978, 77.572], // SBC
        [12.969, 78.204], // BWT
        [12.571, 78.580], // JTJ
        [13.082, 80.275]  // MAS
      ];

      // Draw all tracks
      L.polyline(northCoords, { color: '#00F0FF', weight: 3, opacity: 0.6, dashArray: '5, 8' }).addTo(map);
      L.polyline(northCoords.map(c => [c[0] - 0.02, c[1] - 0.02]), { color: '#A855F7', weight: 3, opacity: 0.6, dashArray: '5, 8' }).addTo(map);

      L.polyline(westCoords, { color: '#00F0FF', weight: 3, opacity: 0.6, dashArray: '5, 8' }).addTo(map);
      L.polyline(westCoords.map(c => [c[0] - 0.02, c[1] - 0.02]), { color: '#A855F7', weight: 3, opacity: 0.6, dashArray: '5, 8' }).addTo(map);

      L.polyline(southCoords, { color: '#00F0FF', weight: 3, opacity: 0.6, dashArray: '5, 8' }).addTo(map);
      L.polyline(southCoords.map(c => [c[0] - 0.02, c[1] - 0.02]), { color: '#A855F7', weight: 3, opacity: 0.6, dashArray: '5, 8' }).addTo(map);

      // Station Pins combined
      const allStationsGeo = {
        ...stationsGeo,
        "MMCT": { name: "Mumbai Central", lat: 18.971, lng: 72.820 },
        "ST": { name: "Surat", lat: 21.205, lng: 72.841 },
        "BRC": { name: "Vadodara Jn", lat: 22.312, lng: 73.181 },
        "ADI": { name: "Ahmedabad Jn", lat: 23.027, lng: 72.601 },
        "SBC": { name: "KSR Bengaluru", lat: 12.978, lng: 77.572 },
        "BWT": { name: "Bangarapet", lat: 12.969, lng: 78.204 },
        "JTJ": { name: "Jolarpettai", lat: 12.571, lng: 78.580 },
        "MAS": { name: "Chennai Central", lat: 13.082, lng: 80.275 }
      };

      Object.entries(allStationsGeo).forEach(([code, station]) => {
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

  // Pan and zoom map view dynamically based on selected zone
  useEffect(() => {
    if (leafletInstance.current && window.L) {
      const map = leafletInstance.current;
      if (selectedZone === 'NORTH') {
        map.setView([27.5, 78.8], 7);
      } else if (selectedZone === 'WEST') {
        map.setView([21.0, 73.0], 7);
      } else if (selectedZone === 'SOUTH') {
        map.setView([12.8, 79.0], 8);
      } else if (selectedZone === 'ALL') {
        map.setView([21.5, 78.0], 5);
      }
    }
  }, [selectedZone, viewMode]);

  // Update train markers on live geographic map
  useEffect(() => {
    if (viewMode === 'geo' && leafletInstance.current && window.L) {
      const L = window.L;
      const map = leafletInstance.current;
      const activeTrains = getTrainsForZone();

      activeTrains.forEach(train => {
        const lat = train.latitude;
        const lng = train.longitude;
        const isFreight = train.train_no === 'BOXN-902' || train.train_no === 'BOXN-505' || train.train_no === 'CONCOR-701';
        const isDelayed = train.current_delay > 0;
        const trainColor = isFreight ? 'var(--color-warning)' : isDelayed ? 'var(--color-danger)' : 'var(--color-accent)';

        // Offset DOWN trains slightly
        const isUpTrain = train.train_no === '22415' || train.train_no === '20901' || train.train_no === '20608';
        const latOffset = isUpTrain ? 0 : -0.02;
        const lngOffset = isUpTrain ? 0 : -0.02;

        const tooltipContent = `
          <div style="font-family: monospace; font-size: 0.7rem; line-height: 1.3;">
            <strong style="color:#ffffff">${train.train_no}</strong><br/>
            <span style="color:${trainColor}">${train.train_name}</span><br/>
            Status: <strong>${train.status}</strong><br/>
            Speed: <strong>${isUpTrain ? '130' : isFreight ? '65' : '110'} km/h</strong>
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
        if (!activeTrains.some(t => t.train_no === trainNo)) {
          markersRef.current[trainNo].remove();
          delete markersRef.current[trainNo];
        }
      });
    }
  }, [trains, viewMode, selectedZone]);

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

  const getTrainPosition = (train, currentStations) => {
    const lon = train.longitude;
    let x = 450;
    
    if (selectedZone === 'WEST') {
      if (lon >= 72.820) x = 100;
      else if (lon >= 72.841) x = 100 + ((72.820 - lon) / (72.820 - 72.841)) * 180;
      else if (lon >= 73.181) x = 280 + ((72.841 - lon) / (72.841 - 73.181)) * 270;
      else if (lon >= 72.601) x = 550 + ((73.181 - lon) / (73.181 - 72.601)) * 250;
      else x = 800;
    } else if (selectedZone === 'SOUTH') {
      if (lon <= 77.572) x = 100;
      else if (lon <= 78.204) x = 100 + ((lon - 77.572) / (78.204 - 77.572)) * 180;
      else if (lon <= 78.580) x = 280 + ((lon - 78.204) / (78.580 - 78.204)) * 270;
      else if (lon <= 80.275) x = 550 + ((lon - 78.580) / (80.275 - 78.580)) * 250;
      else x = 800;
    } else {
      if (lon <= 77.222) x = 100;
      else if (lon <= 77.436) x = 100 + ((lon - 77.222) / (77.436 - 77.222)) * 180;
      else if (lon <= 78.078) x = 280 + ((lon - 77.436) / (78.078 - 77.436)) * 270;
      else if (lon <= 80.350) x = 550 + ((lon - 78.078) / (80.350 - 78.078)) * 250;
      else x = 800;
    }
    
    let y = (train.train_no === "22415" || train.train_no === "20901" || train.train_no === "20608") ? 70 : 135;
    let xOffset = 0;
    const activeTrains = getTrainsForZone();
    if ((train.train_no === "BOXN-902" || train.train_no === "BOXN-505" || train.train_no === "CONCOR-701") && 
        activeTrains.some(t => (t.train_no === "12002" || t.train_no === "12008" || t.train_no === "12009") && Math.abs(t.longitude - train.longitude) < 0.02)) {
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

  const drawTrackSegment = (fromCode, toCode, yCoord, isUpLine, currentStations) => {
    const fromStation = currentStations[fromCode];
    const toStation = currentStations[toCode];
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
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, letterSpacing: '0.5px' }}>
            {selectedZone === 'ALL' ? 'All India Live Telemetry Network' : `Sector ${selectedZone.charAt(0) + selectedZone.slice(1).toLowerCase()} Live Telemetry Corridor`}
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Interactive Indian Railways Kavach Interlocking Desk</p>
        </div>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          {/* Zone Selector dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', background: 'rgba(255,255,255,0.02)', padding: '4px 8px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', fontWeight: 'bold', textTransform: 'uppercase', marginRight: '5px' }}>Zone:</span>
            <select 
              value={selectedZone} 
              onChange={(e) => {
                const zone = e.target.value;
                setSelectedZone(zone);
                if (zone === 'ALL') setViewMode('geo');
              }}
              style={{
                background: '#090d16',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                color: 'var(--color-text-main)',
                fontSize: '0.65rem',
                fontWeight: 'bold',
                padding: '2px 6px',
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="NORTH">Northern (NR/NCR)</option>
              <option value="WEST">Western (WR)</option>
              <option value="SOUTH">Southern (SR/SWR)</option>
              <option value="ALL">All India Grid</option>
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="toggle-group" style={{ display: 'flex', background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-color)', marginRight: '10px' }}>
            <button 
              onClick={() => setViewMode('schematic')} 
              disabled={selectedZone === 'ALL'}
              style={{
                padding: '4px 10px',
                fontSize: '0.65rem',
                fontWeight: 'bold',
                background: viewMode === 'schematic' ? 'var(--color-primary)' : 'transparent',
                color: viewMode === 'schematic' ? 'black' : 'var(--color-text-muted)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                opacity: selectedZone === 'ALL' ? 0.5 : 1
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
        (() => {
          const currentStations = getStationsForZone();
          const activeTrains = getTrainsForZone();
          return (
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
                {Object.values(currentStations).map((s, idx) => (
                  <line 
                    key={`cross-${idx}`} 
                    x1={s.x} 
                    y1={s.y_up} 
                    x2={s.x} 
                    y2={s.y_down} 
                    className={`crossover-line ${disruptions.some(d => d.status === 'ACTIVE' && d.section_from === Object.keys(currentStations)[idx]) ? 'active' : ''}`}
                  />
                ))}

                {/* UP Line Segments */}
                {Object.keys(currentStations).map((code, idx, arr) => {
                  if (idx === arr.length - 1) return null;
                  return drawTrackSegment(code, arr[idx+1], 70, true, currentStations);
                })}

                {/* DOWN Line Segments */}
                {Object.keys(currentStations).map((code, idx, arr) => {
                  if (idx === arr.length - 1) return null;
                  return drawTrackSegment(code, arr[idx+1], 135, false, currentStations);
                })}

                {/* Station Platform Nodes */}
                {Object.entries(currentStations).map(([code, station]) => {
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
                {activeTrains.map((train) => {
                  const pos = getTrainPosition(train, currentStations);
                  const isDelayed = train.current_delay > 0;
                  const isFreight = train.train_no === "BOXN-902" || train.train_no === "BOXN-505" || train.train_no === "CONCOR-701";
                  
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
          );
        })()
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
