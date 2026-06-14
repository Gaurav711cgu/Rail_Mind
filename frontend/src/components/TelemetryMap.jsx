import React, { useState, useEffect, useRef, useCallback } from 'react';

/* ─────────────────────────────────────────────────────────────────
   STATION COORDINATE REGISTRY
   Add any station code here to get automatic lat/lng on the map
───────────────────────────────────────────────────────────────── */
const STATION_COORDS = {
  NDLS: { name: 'New Delhi',       lat: 28.6430, lng: 77.2220 },
  GZB:  { name: 'Ghaziabad',       lat: 28.6720, lng: 77.4360 },
  ALJN: { name: 'Aligarh',         lat: 27.8920, lng: 78.0780 },
  CNB:  { name: 'Kanpur Central',  lat: 26.4480, lng: 80.3500 },
  MMCT: { name: 'Mumbai Central',  lat: 18.9710, lng: 72.8200 },
  ST:   { name: 'Surat',           lat: 21.2050, lng: 72.8410 },
  BRC:  { name: 'Vadodara Jn',     lat: 22.3120, lng: 73.1810 },
  ADI:  { name: 'Ahmedabad Jn',    lat: 23.0270, lng: 72.6010 },
  SBC:  { name: 'KSR Bengaluru',   lat: 12.9780, lng: 77.5720 },
  BWT:  { name: 'Bangarapet',      lat: 12.9690, lng: 78.2040 },
  JTJ:  { name: 'Jolarpettai',     lat: 12.5710, lng: 78.5800 },
  MAS:  { name: 'Chennai Central', lat: 13.0820, lng: 80.2750 },
  HWH:  { name: 'Howrah Jn',       lat: 22.5848, lng: 88.3426 },
  PNBE: { name: 'Patna Jn',        lat: 25.5987, lng: 85.1337 },
  MGS:  { name: 'Mughal Sarai',    lat: 25.2800, lng: 83.1200 },
  ALD:  { name: 'Prayagraj Jn',    lat: 25.4358, lng: 81.8463 },
  LKO:  { name: 'Lucknow NR',      lat: 26.8467, lng: 80.9462 },
  BSB:  { name: 'Varanasi',        lat: 25.3176, lng: 82.9739 },
  JP:   { name: 'Jaipur',          lat: 26.9124, lng: 75.7873 },
  AGC:  { name: 'Agra Cantt',      lat: 27.1601, lng: 78.0180 },
  MTJ:  { name: 'Mathura Jn',      lat: 27.4924, lng: 77.6737 },
  BPL:  { name: 'Bhopal Jn',       lat: 23.2694, lng: 77.4027 },
  NGP:  { name: 'Nagpur',          lat: 21.1502, lng: 79.0882 },
  SC:   { name: 'Secunderabad',    lat: 17.4399, lng: 78.4983 },
  HYB:  { name: 'Hyderabad',       lat: 17.3850, lng: 78.4867 },
};

const ZONE_CONFIG = {
  NORTH: {
    label: 'Northern (NR/NCR)',
    center: [27.5, 78.8],
    zoom: 7,
    color: '#FFFFFF',
    stations: ['NDLS', 'GZB', 'ALJN', 'CNB'],
  },
  WEST: {
    label: 'Western (WR)',
    center: [21.0, 73.0],
    zoom: 7,
    color: '#FFFFFF',
    stations: ['MMCT', 'ST', 'BRC', 'ADI'],
  },
  SOUTH: {
    label: 'Southern (SR/SWR)',
    center: [12.8, 79.0],
    zoom: 8,
    color: '#FFFFFF',
    stations: ['SBC', 'BWT', 'JTJ', 'MAS'],
  },
  ALL: {
    label: 'All India Grid',
    center: [21.5, 78.0],
    zoom: 5,
    color: '#FFFFFF',
    stations: Object.keys(STATION_COORDS),
  },
};

/* station code → coords (with small random scatter if unknown) */
function coordsFor(code) {
  return STATION_COORDS[code] || null;
}

/* colour by delay */
function trainColor(delay, isFreight) {
  if (delay >= 10) return 'var(--accent)'; // Crimson Red for delays
  return 'var(--ink)'; // Crisp White for on-time / freight
}

/* ─────────────────────────────────────────────────────────────────
   MAIN COMPONENT
───────────────────────────────────────────────────────────────── */
export default function TelemetryMap({ trains: scenarioTrains, disruptions, onNextStep, scenarioStep }) {
  /* ── view state ── */
  const [viewMode, setViewMode]           = useState('geo');        // 'geo' | 'schematic'
  const [selectedZone, setSelectedZone]   = useState('NORTH');
  const [selectedTrain, setSelectedTrain] = useState(null);

  /* ── live route search ── */
  const [fromCode, setFromCode]           = useState('NDLS');
  const [toCode,   setToCode]             = useState('CNB');
  const [fromInput, setFromInput]         = useState('NDLS');
  const [toInput,   setToInput]           = useState('CNB');
  const [routeTrains, setRouteTrains]     = useState([]);
  const [routeLoading, setRouteLoading]   = useState(false);
  const [routeError, setRouteError]       = useState(null);
  const [searchMode, setSearchMode]       = useState(false);       // true = showing route search results
  const [stationBoard, setStationBoard]   = useState(null);        // live station board data
  const [stationLoading, setStationLoading] = useState(false);

  /* ── live train status panel ── */
  const [liveStatus, setLiveStatus]       = useState(null);
  const [liveLoading, setLiveLoading]     = useState(false);

  /* ── map refs ── */
  const mapRef           = useRef(null);
  const leafletRef        = useRef(null);
  const markersRef        = useRef({});
  const routeLineRef      = useRef(null);
  const stationMarkersRef = useRef({});

  /* ── scenario state ── */
  const [metrics, setMetrics] = useState({
    efficiency_score: 94.5, capacity_load: 34.0,
    average_speed: 104.2,   safety_index: 100.0,
  });
  const [kavachStates, setKavachStates] = useState({
    'DLI-GZB': true, 'GZB-ALJN': true, 'ALJN-CNB': false,
  });
  const [weatherState, setWeatherState] = useState({
    visibility_meters: 2200, fog_density: 12,
    wind_speed: 14, temperature: 29.5,
    active_warning: 'NONE', recommended_speed_limit: 130,
  });
  const [speedLimits, setSpeedLimits] = useState({
    'DLI-GZB': 110, 'GZB-ALJN': 130, 'ALJN-CNB': 130,
  });
  const [autoplay, setAutoplay]           = useState(false);
  const [autoplayCountdown, setAutoplayCD] = useState(6);
  const timerRef = useRef(null);

  /* ────────────────────────────────────────────
     Fetch corridor metrics
  ──────────────────────────────────────────── */
  useEffect(() => {
    fetch('/api/v1/cascade/corridor-metrics')
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setMetrics(d))
      .catch(() => {});
  }, [scenarioStep]);

  /* ────────────────────────────────────────────
     Autoplay
  ──────────────────────────────────────────── */
  useEffect(() => {
    if (autoplay) {
      timerRef.current = setInterval(() => {
        setAutoplayCD(p => {
          if (p <= 1) { onNextStep(); return 6; }
          return p - 1;
        });
      }, 1000);
    } else clearInterval(timerRef.current);
    return () => clearInterval(timerRef.current);
  }, [autoplay, onNextStep]);

  useEffect(() => { setAutoplayCD(6); }, [scenarioStep]);

  /* ────────────────────────────────────────────
     Kavach & Speed
  ──────────────────────────────────────────── */
  const handleKavachToggle = async (sec) => {
    const next = !kavachStates[sec];
    setKavachStates(p => ({ ...p, [sec]: next }));
    try { await fetch(`/api/v1/cascade/kavach-toggle?section_code=${sec}&active=${next}`, { method: 'POST' }); } catch {}
  };
  const handleSpeedLimitChange = async (sec, limit) => {
    setSpeedLimits(p => ({ ...p, [sec]: limit }));
    try { await fetch(`/api/v1/trains/speed-lock?section_code=${sec}&speed_limit=${limit}`, { method: 'POST' }); } catch {}
  };
  const handleVisibilitySlider = async (e) => {
    const v = parseInt(e.target.value);
    const d = Math.round((1 - v / 3000) * 100);
    const s = v < 500 ? 30 : v < 1000 ? 60 : 130;
    const next = { ...weatherState, visibility_meters: v, fog_density: d, recommended_speed_limit: s, active_warning: v < 500 ? 'SEVERE_FOG_WARNING' : 'NONE' };
    setWeatherState(next);
    try { await fetch(`/api/v1/cascade/weather?visibility=${v}&fog_density=${d}&speed_limit=${s}`, { method: 'POST' }); } catch {}
  };

  /* ────────────────────────────────────────────
     LIVE ROUTE SEARCH  →  trainBetweenStations
  ──────────────────────────────────────────── */
  const searchRoute = useCallback(async () => {
    if (!fromCode || !toCode) return;
    setRouteLoading(true);
    setRouteError(null);
    setRouteTrains([]);
    setSearchMode(true);
    try {
      const today = new Date();
      const dateStr = `${today.getDate().toString().padStart(2,'0')}-${(today.getMonth()+1).toString().padStart(2,'0')}-${today.getFullYear()}`;
      const res = await fetch(
        `/api/v1/trains/rapidapi/trains-between-stations?from_station_code=${fromCode}&to_station_code=${toCode}&date_of_journey=${dateStr}`
      );
      if (!res.ok) throw new Error(`API ${res.status}`);
      const json = await res.json();
      /* irctc1 provider returns data.data[] or data[] */
      const list = json?.data?.data || json?.data || [];
      setRouteTrains(Array.isArray(list) ? list : []);
    } catch (err) {
      setRouteError(err.message || 'Failed to fetch route trains');
    } finally {
      setRouteLoading(false);
    }
  }, [fromCode, toCode]);

  /* ────────────────────────────────────────────
     LIVE STATION BOARD  →  getLiveStation
  ──────────────────────────────────────────── */
  const fetchStationBoard = useCallback(async (code) => {
    setStationLoading(true);
    setStationBoard(null);
    try {
      const res = await fetch(`/api/v1/trains/rapidapi/live-station?station_code=${code}&hours=2`);
      if (!res.ok) throw new Error(`API ${res.status}`);
      const json = await res.json();
      const list = json?.data?.data || json?.data || [];
      setStationBoard({ code, trains: Array.isArray(list) ? list : [] });
    } catch {
      setStationBoard({ code, trains: [], error: true });
    } finally {
      setStationLoading(false);
    }
  }, []);

  /* ────────────────────────────────────────────
     LIVE TRAIN STATUS FETCH
  ──────────────────────────────────────────── */
  const fetchLiveStatus = useCallback(async (trainNo) => {
    setLiveLoading(true);
    setLiveStatus(null);
    try {
      const res = await fetch(`/api/v1/trains/rapidapi/live-status?train_no=${trainNo}&start_day=0`);
      if (!res.ok) throw new Error(`API ${res.status}`);
      const json = await res.json();
      setLiveStatus({ trainNo, data: json?.data || json });
    } catch {
      setLiveStatus({ trainNo, data: null, error: true });
    } finally {
      setLiveLoading(false);
    }
  }, []);

  /* ────────────────────────────────────────────
     DETERMINE ACTIVE TRAINS for the map
  ──────────────────────────────────────────── */
  const activeTrains = (() => {
    if (searchMode && routeTrains.length) {
      /* Map IRCTC response fields → our internal shape */
      return routeTrains.slice(0, 20).map(t => {
        const no   = t.train_no || t.trainNo || '';
        const name = t.train_name || t.trainName || `Train ${no}`;
        const from = (t.from_stn_code || t.source_stn_code || fromCode || '').toUpperCase();
        const delay = parseInt(t.delay || t.delayed_by || t.lateBy || 0) || 0;
        const coords = coordsFor(from);
        return {
          train_no:        no,
          train_name:      name,
          current_station: from,
          current_delay:   delay,
          status:          t.running_status || t.status || 'SCHEDULED',
          latitude:        coords?.lat || 0,
          longitude:       coords?.lng || 0,
          arrival_time:    t.arrival_time || t.arrivalTime || '--',
          departure_time:  t.departure_time || t.departureTime || '--',
          duration:        t.duration || '--',
          classes:         t.class_type || t.classes || '',
        };
      });
    }
    /* Scenario trains enriched with coords */
    const zone = ZONE_CONFIG[selectedZone];
    return scenarioTrains
      .filter(t => {
        if (selectedZone === 'ALL') return true;
        const c = coordsFor(t.current_station);
        if (!c) return true;
        return zone.stations.includes(t.current_station) ||
          zone.stations.some(s => Math.abs(STATION_COORDS[s]?.lat - c.lat) < 3 &&
                                   Math.abs(STATION_COORDS[s]?.lng - c.lng) < 3);
      });
  })();

  /* ────────────────────────────────────────────
     MAP INITIALIZATION
  ──────────────────────────────────────────── */
  useEffect(() => {
    if (viewMode !== 'geo') return;
    if (!mapRef.current || !window.L) return;
    if (leafletRef.current) return;   // already init

    const L = window.L;
    const map = L.map(mapRef.current, {
      center: [22.0, 78.0],
      zoom: 5,
      zoomControl: false,
      attributionControl: false,
    });

    // Dark CartoDB tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Draw all zone track lines
    Object.values(ZONE_CONFIG).forEach(zone => {
      if (zone.stations.length < 2) return;
      const pts = zone.stations
        .map(c => STATION_COORDS[c])
        .filter(Boolean)
        .map(s => [s.lat, s.lng]);
      if (pts.length >= 2) {
        L.polyline(pts, { color: zone.color, weight: 2.5, opacity: 0.5, dashArray: '6 8' }).addTo(map);
      }
    });

    // Station markers (permanent label, clickable for station board)
    Object.entries(STATION_COORDS).forEach(([code, s]) => {
      const m = L.circleMarker([s.lat, s.lng], {
        radius: 5, color: '#ffffff', weight: 1.2,
        fillColor: '#030712', fillOpacity: 1,
      }).addTo(map);

      m.bindTooltip(
        `<div style="font-family:monospace;font-size:0.65rem;"><strong style="color:#FFFFFF">${s.name}</strong><br/><span style="color:#aaa">${code}</span></div>`,
        { permanent: false, direction: 'top', className: 'custom-map-tooltip' }
      );

      // Click → fetch live station board
      m.on('click', () => fetchStationBoard(code));
      stationMarkersRef.current[code] = m;
    });

    leafletRef.current = map;

    return () => {
      leafletRef.current?.remove();
      leafletRef.current = null;
      markersRef.current = {};
      stationMarkersRef.current = {};
    };
  }, [viewMode]);   // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Zone pan/zoom ── */
  useEffect(() => {
    const map = leafletRef.current;
    if (!map) return;
    const cfg = ZONE_CONFIG[selectedZone];
    map.flyTo(cfg.center, cfg.zoom, { duration: 1 });
  }, [selectedZone]);

  /* ── Train markers update ── */
  useEffect(() => {
    const map = leafletRef.current;
    if (!map || !window.L) return;
    const L = window.L;

    const seen = new Set();

    activeTrains.forEach(train => {
      const lat = train.latitude;
      const lng = train.longitude;
      if (!lat && !lng) return;   // skip if no coords

      const delay     = train.current_delay || 0;
      const isFreight = /BOXN|CONCOR|GOODS|FRT/i.test(train.train_no);
      const color     = trainColor(delay, isFreight);
      const label     = `
        <div style="font-family:monospace;font-size:0.68rem;line-height:1.4;">
          <strong style="color:#fff">${train.train_no}</strong><br/>
          <span style="color:${color}">${train.train_name}</span><br/>
          <span style="color:#aaa">@ ${train.current_station}</span>
          ${delay ? `<br/><span style="color:#EF4444">+${delay}m delay</span>` : ''}
          ${train.arrival_time && train.arrival_time !== '--' ? `<br/>Arr: ${train.arrival_time}` : ''}
        </div>`;

      seen.add(train.train_no);

      if (markersRef.current[train.train_no]) {
        const m = markersRef.current[train.train_no];
        m.setLatLng([lat, lng]);
        m.setStyle({ fillColor: color, color });
        m.getTooltip()?.setContent(label);
      } else {
        const m = L.circleMarker([lat, lng], {
          radius: 9, fillColor: color, color, weight: 1.5, fillOpacity: 1,
        }).addTo(map);
        m.bindTooltip(label, { permanent: true, direction: 'top', offset: [0, -10], className: 'custom-map-tooltip' });
        m.on('click', () => { setSelectedTrain(train); fetchLiveStatus(train.train_no); });
        markersRef.current[train.train_no] = m;
      }
    });

    /* Remove stale markers */
    Object.keys(markersRef.current).forEach(no => {
      if (!seen.has(no)) {
        markersRef.current[no].remove();
        delete markersRef.current[no];
      }
    });
  }, [activeTrains, viewMode]);   // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Draw route line on map when search returns results ── */
  useEffect(() => {
    const map = leafletRef.current;
    if (!map || !window.L) return;
    const L = window.L;

    if (routeLineRef.current) { routeLineRef.current.remove(); routeLineRef.current = null; }

    if (searchMode) {
      const a = STATION_COORDS[fromCode];
      const b = STATION_COORDS[toCode];
      if (a && b) {
        routeLineRef.current = L.polyline([[a.lat, a.lng], [b.lat, b.lng]], {
          color: '#FACC15', weight: 3, opacity: 0.85, dashArray: '10 6',
        }).addTo(map);
        map.flyToBounds([[a.lat, a.lng], [b.lat, b.lng]], { padding: [60, 60], duration: 1 });
      }
    }
  }, [searchMode, fromCode, toCode, routeTrains]);

  /* ── Schematic: station & train position helpers ── */
  const schStations = {
    NDLS: { name: 'New Delhi', x: 100, y_up: 70, y_down: 135 },
    GZB:  { name: 'Ghaziabad', x: 280, y_up: 70, y_down: 135 },
    ALJN: { name: 'Aligarh',   x: 550, y_up: 70, y_down: 135 },
    CNB:  { name: 'Kanpur Central', x: 800, y_up: 70, y_down: 135 },
  };

  const getSchTrainX = (train) => {
    const lng = train.longitude || 0;
    if (lng <= 77.222) return 100;
    if (lng <= 77.436) return 100 + ((lng - 77.222) / (77.436 - 77.222)) * 180;
    if (lng <= 78.078) return 280 + ((lng - 77.436) / (78.078 - 77.436)) * 270;
    if (lng <= 80.350) return 550 + ((lng - 78.078) / (80.350 - 78.078)) * 250;
    return 800;
  };

  const isSectionDisrupted = (a, b) =>
    disruptions.some(d => d.status === 'ACTIVE' &&
      (d.section_from === a && d.section_to === b || d.section_from === a));

  /* ════════════════════════════════════════════
     RENDER
  ════════════════════════════════════════════ */
  return (
    <div style={{
      gridColumn: 'span 8', minHeight: '560px',
      display: 'flex', flexDirection: 'column', padding: '24px',
      background: 'var(--surface-panel)', border: '1px solid var(--border)',
      borderRadius: 'var(--rounded-lg)'
    }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h3 style={{ fontFamily: "'Inter', sans-serif", fontSize: '16px', fontWeight: 600, color: 'var(--ink)', margin: 0 }}>
            {searchMode
              ? `Live Trains: ${fromCode} → ${toCode}`
              : ZONE_CONFIG[selectedZone].label + ' Live Telemetry'}
          </h3>
          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', color: 'var(--ink-soft)', margin: 0 }}>
            {searchMode
              ? `${routeTrains.length} trains found · click a marker for live status`
              : 'Kavach Interlocking Desk · Click station for live board'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Zone selector */}
          {!searchMode && (
            <select
              value={selectedZone}
              onChange={e => { setSelectedZone(e.target.value); if (e.target.value === 'ALL') setViewMode('geo'); }}
              style={{
                background: 'var(--surface-input)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--rounded-sm)',
                color: 'var(--ink)',
                fontSize: '11px',
                fontFamily: "'JetBrains Mono', monospace",
                padding: '4px 8px',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              {Object.entries(ZONE_CONFIG).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          )}

          {/* View toggle */}
          <div style={{ display: 'flex', background: 'var(--surface-input)', padding: '2px', borderRadius: 'var(--rounded-sm)', border: '1px solid var(--border)' }}>
            <button
              onClick={() => setViewMode('schematic')}
              disabled={searchMode || selectedZone === 'ALL'}
              style={{
                padding: '4px 10px', fontSize: '11px', fontFamily: "'Inter', sans-serif", fontWeight: '700', border: 'none', borderRadius: 'var(--rounded-xs)', cursor: 'pointer', transition: 'all 0.15s',
                background: viewMode === 'schematic' ? 'var(--accent)' : 'transparent',
                color: viewMode === 'schematic' ? 'var(--ink-on-red)' : 'var(--ink-soft)',
                opacity: (searchMode || selectedZone === 'ALL') ? 0.4 : 1,
              }}
            >SCHEMATIC</button>
            <button
              onClick={() => setViewMode('geo')}
              style={{
                padding: '4px 10px', fontSize: '11px', fontFamily: "'Inter', sans-serif", fontWeight: '700', border: 'none', borderRadius: 'var(--rounded-xs)', cursor: 'pointer', transition: 'all 0.15s',
                background: viewMode === 'geo' ? 'var(--accent)' : 'transparent',
                color: viewMode === 'geo' ? 'var(--ink-on-red)' : 'var(--ink-soft)',
              }}
            >GEO MAP</button>
          </div>

          {/* KAVACH indicator */}
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.68rem', fontWeight: 600, color: 'var(--accent)' }}>
            <span className="led-indicator active" style={{ width: '7px', height: '7px' }} />
            KAVACH LIVE
          </span>
        </div>
      </div>

      {/* ── Route Search Bar ── */}
      <div style={{
        background: 'var(--surface-input)', border: '1px solid var(--border)',
        borderRadius: 'var(--rounded-sm)', padding: '10px 14px', marginBottom: '12px',
        display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Live Route
        </span>
        <input
          value={fromInput}
          onChange={e => { setFromInput(e.target.value.toUpperCase()); setFromCode(e.target.value.toUpperCase()); }}
          placeholder="FROM (e.g. NDLS)"
          maxLength={6}
          style={{
            width: '90px', background: 'var(--surface-input)', border: '1px solid var(--border)',
            borderRadius: 'var(--rounded-sm)', color: 'var(--accent)', fontSize: '13px',
            fontWeight: 700, padding: '6px 10px', outline: 'none', fontFamily: "'JetBrains Mono', monospace",
            textTransform: 'uppercase',
          }}
        />
        <span style={{ color: 'var(--ink-soft)', fontSize: '0.75rem' }}>→</span>
        <input
          value={toInput}
          onChange={e => { setToInput(e.target.value.toUpperCase()); setToCode(e.target.value.toUpperCase()); }}
          placeholder="TO (e.g. CNB)"
          maxLength={6}
          style={{
            width: '90px', background: 'var(--surface-input)', border: '1px solid var(--border)',
            borderRadius: '4px', color: 'var(--accent)', fontSize: '0.75rem',
            fontWeight: 700, padding: '5px 8px', outline: 'none', fontFamily: 'monospace',
            textTransform: 'uppercase',
          }}
        />
        <button
          onClick={searchRoute}
          disabled={routeLoading}
          className="btn-primary"
          style={{
            height: '32px',
            padding: '0 16px',
            fontSize: '11px'
          }}
        >
          {routeLoading ? '...' : 'SEARCH'}
        </button>
        {searchMode && (
          <button
            onClick={() => { setSearchMode(false); setRouteTrains([]); setRouteError(null); setStationBoard(null); }}
            style={{
              background: 'transparent', border: '1px solid var(--border)',
              borderRadius: '4px', color: 'var(--ink-soft)', fontWeight: 700,
              fontSize: '0.65rem', padding: '5px 10px', cursor: 'pointer',
            }}
          >Clear</button>
        )}
        {routeError && (
          <span style={{ fontSize: '0.65rem', color: 'var(--accent)' }}>Warning: {routeError}</span>
        )}
        {/* Quick preset buttons */}
        <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
          {[
            ['NDLS', 'CNB', 'DEL→KNP'],
            ['NDLS', 'HWH', 'DEL→HWH'],
            ['MMCT', 'ADI', 'BOM→ADI'],
            ['SBC', 'MAS', 'BLR→MAS'],
          ].map(([f, t, lbl]) => (
            <button
              key={lbl}
              onClick={() => { setFromCode(f); setFromInput(f); setToCode(t); setToInput(t); }}
              style={{
                background: fromCode === f && toCode === t ? 'var(--accent-subtle)' : 'transparent',
                border: `1px solid ${fromCode === f && toCode === t ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: '4px', color: fromCode === f && toCode === t ? 'var(--accent)' : 'var(--ink-soft)',
                fontSize: '0.58rem', fontWeight: 700, padding: '3px 7px', cursor: 'pointer',
              }}
            >{lbl}</button>
          ))}
        </div>
      </div>

      {/* ── Map Area ── */}
      <div style={{ position: 'relative', flex: '1 1 auto', minHeight: '240px', background: 'var(--surface-input)', borderRadius: 'var(--rounded-md)', border: '1px solid var(--border)', overflow: 'hidden', marginBottom: '14px' }}>
        {/* Leaflet geo map */}
        <div
          ref={mapRef}
          style={{ width: '100%', height: '100%', display: viewMode === 'geo' ? 'block' : 'none' }}
        />

        {/* Schematic SVG */}
        {viewMode === 'schematic' && (
          <svg viewBox="0 0 900 220" width="100%" height="100%" style={{ display: 'block' }}>
            <defs>
              <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <pattern id="sch-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(255,255,255,0.015)" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width="900" height="220" fill="url(#sch-grid)" />
            <style>{`
              .sch-glow { stroke-width:8; stroke-linecap:round; opacity:0.12; }
              .sch-core { stroke-width:2.5; stroke-linecap:round; stroke-dasharray:6 5; }
              .up   { stroke:var(--accent); }
              .down { stroke:var(--ink-soft); }
              .disrupted.sch-glow { stroke:var(--status-warn); opacity:.35; }
              .disrupted.sch-core { stroke:var(--status-warn); opacity:.8; }
              .stn-out { fill:#030712; stroke:rgba(255,255,255,.12); stroke-width:1.5; cursor:pointer; }
              .stn-out.act { stroke:var(--accent); }
              .stn-out.danger { stroke:var(--status-fail); }
              .stn-in { fill:rgba(255,255,255,.15); }
              .stn-in.act { fill:var(--accent); }
              .stn-in.danger { fill:var(--status-fail); }
              .train-node { cursor:pointer; }
              .train-node:hover { stroke:var(--accent); }
              
              
            `}</style>

            {/* Track segments */}
            {Object.keys(schStations).map((code, idx, arr) => {
              if (idx === arr.length - 1) return null;
              const next = arr[idx + 1];
              const x1 = schStations[code].x, x2 = schStations[next].x;
              const dis = isSectionDisrupted(code, next) ? ' disrupted' : '';
              return (
                <g key={`seg-${code}`}>
                  <line x1={x1} y1={70}  x2={x2} y2={70}  className={`sch-glow up${dis}`} />
                  <line x1={x1} y1={70}  x2={x2} y2={70}  className={`sch-core up${dis} opacity-50`} />
                  <line x1={x1} y1={135} x2={x2} y2={135} className={`sch-glow down${dis}`} />
                  <line x1={x1} y1={135} x2={x2} y2={135} className={`sch-core down${dis} opacity-50`} />
                </g>
              );
            })}

            {/* Stations */}
            {Object.entries(schStations).map(([code, s]) => {
              const hasDis = disruptions.some(d => d.status === 'ACTIVE' && d.section_from === code);
              return (
                <g key={code} onClick={() => fetchStationBoard(code)} style={{ cursor: 'pointer' }}>
                  <circle cx={s.x} cy={s.y_up}   r="8" className={`stn-out ${hasDis ? 'danger' : 'act'}`} />
                  <circle cx={s.x} cy={s.y_up}   r="3.5" className={`stn-in ${hasDis ? 'danger' : 'act'}`} />
                  <circle cx={s.x} cy={s.y_down} r="8" className={`stn-out ${hasDis ? 'danger' : 'act'}`} />
                  <circle cx={s.x} cy={s.y_down} r="3.5" className={`stn-in ${hasDis ? 'danger' : 'act'}`} />
                  <rect x={s.x - 45} y="180" width="90" height="28" rx="4" fill="var(--surface-input)" stroke="var(--border)" strokeWidth="1" />
                  <text x={s.x} y="193" textAnchor="middle" fill="var(--ink)" fontSize="0.62rem" fontWeight="800">{s.name}</text>
                  <text x={s.x} y="204" textAnchor="middle" fill="var(--accent)" fontSize="0.55rem" fontWeight="600" letterSpacing="1px">{code}</text>
                </g>
              );
            })}

            {/* Train nodes (schematic) */}
            {activeTrains.map(train => {
              const x = getSchTrainX(train);
              const y = (train.train_no === '22415' || train.train_no === '12002') ? 70 : 135;
              const isFreight = /BOXN|CONCOR/i.test(train.train_no);
              const color = trainColor(train.current_delay || 0, isFreight);
              return (
                <g key={train.train_no} className="train-node" transform={`translate(${x},${y})`}
                  onClick={() => { setSelectedTrain(train); fetchLiveStatus(train.train_no); }}>
                  <circle cx="0" cy="0" r="7.5" fill="none" stroke={color} strokeWidth="1.2" opacity="0.8">
                    <animate attributeName="r" values="7.5;22" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.8;0" dur="2s" repeatCount="indefinite" />
                  </circle>
                  <circle cx="0" cy="0" r="8" fill={color} filter="url(#neon-glow)" />
                  <path d={y === 70 ? 'M-1.5,-3 L2,0 L-1.5,3' : 'M1.5,-3 L-2,0 L1.5,3'}
                    fill="none" stroke="#FFF" strokeWidth="1.8" strokeLinecap="round" />
                  <g transform={`translate(0,${y === 70 ? -24 : 24})`}>
                    <rect x="-35" y="-10" width="70" height="15" rx="3" fill="#030712" stroke={color} strokeWidth="1" />
                    <text x="0" y="0.5" textAnchor="middle" fill="var(--ink)" fontSize="0.55rem" fontWeight="800">
                      {train.train_no}
                    </text>
                    {(train.current_delay > 0) && (
                      <text x="0" y="10" textAnchor="middle" fill="var(--accent)" fontSize="0.45rem" fontWeight="700">
                        +{train.current_delay}m
                      </text>
                    )}
                  </g>
                </g>
              );
            })}
          </svg>
        )}

        {/* Loading overlay */}
        {routeLoading && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(13,13,11,0.7)', zIndex: 500,
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 700 }}>Fetching live trains…</div>
            </div>
          </div>
        )}

        {/* Route results count badge */}
        {searchMode && !routeLoading && (
          <div style={{
            position: 'absolute', top: '10px', left: '10px', zIndex: 400,
            background: 'rgba(0,0,0,0.8)', border: '1px solid var(--border-accent)',
            borderRadius: '6px', padding: '6px 12px', fontSize: '0.7rem', fontWeight: 700,
          }}>
            <span style={{ color: 'var(--accent)' }}>{routeTrains.length}</span>
            <span style={{ color: 'var(--ink-soft)', marginLeft: '5px' }}>trains · {fromCode} → {toCode}</span>
          </div>
        )}
      </div>

      {/* ── Three bottom panels ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.6fr 1.3fr', gap: '16px' }}>

        {/* Panel 1: Sensors & Kavach / Station Board */}
        <div style={{
          background: 'var(--surface-panel)', border: '1px solid var(--border)',
          borderRadius: 'var(--rounded-md)', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px'
        }}>
          {stationBoard ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0 }}>
                  {stationBoard.code} Live Board
                </h4>
                <button
                  onClick={() => setStationBoard(null)}
                  style={{ background: 'none', border: 'none', color: 'var(--ink-soft)', cursor: 'pointer', fontSize: '0.8rem' }}
                >X</button>
              </div>
              <div style={{ borderBottom: '1px solid var(--border-soft)', paddingBottom: '4px' }} />
              {stationLoading && <div style={{ fontSize: '0.65rem', color: 'var(--ink-soft)', textAlign: 'center', padding: '10px' }}>Loading…</div>}
              {stationBoard.error && <div style={{ fontSize: '0.65rem', color: 'var(--color-warning)', textAlign: 'center' }}>API unavailable — check key</div>}
              {!stationLoading && !stationBoard.error && stationBoard.trains.length === 0 && (
                <div style={{ fontSize: '0.65rem', color: 'var(--color-text-dark)', textAlign: 'center', padding: '10px' }}>No trains in next 2h</div>
              )}
              <div style={{ overflowY: 'auto', maxHeight: '130px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {stationBoard.trains.slice(0, 8).map((t, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', padding: '3px 5px', background: 'rgba(0,0,0,0.2)', borderRadius: '3px' }}>
                    <span style={{ fontWeight: 700, color: 'white' }}>{t.train_no || t.trainNo}</span>
                    <span style={{ color: 'var(--ink-soft)' }} title={t.train_name || t.trainName}>
                      {(t.train_name || t.trainName || '').substring(0, 14)}
                    </span>
                    <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{t.expected_arrival || t.arrival || '--'}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <h4 style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-soft)', paddingBottom: '5px', margin: 0 }}>
                Sensors & Kavach
              </h4>
              {/* Visibility slider */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', marginBottom: '3px' }}>
                  <span style={{ color: 'var(--ink-soft)' }}>Visibility</span>
                  <span style={{ color: weatherState.visibility_meters < 500 ? 'var(--accent)' : 'var(--ink)', fontWeight: 700 }}>
                    {weatherState.visibility_meters}m {weatherState.active_warning !== 'NONE' && ' WARNING'}
                  </span>
                </div>
                <input type="range" min="100" max="3000" step="100" value={weatherState.visibility_meters} onChange={handleVisibilitySlider}
                  style={{ width: '100%', height: '3px', background: 'var(--border)', outline: 'none', appearance: 'none', cursor: 'pointer' }} />
              </div>
              {/* Kavach toggles */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span style={{ fontSize: '0.58rem', color: 'var(--ink-soft)', textTransform: 'uppercase' }}>Kavach Segments</span>
                {Object.keys(kavachStates).map(sec => (
                  <label key={sec} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.65rem', background: 'rgba(0,0,0,0.15)', padding: '4px 7px', borderRadius: '4px', cursor: 'pointer' }}>
                    <span style={{ fontWeight: 600 }}>{sec}</span>
                    <input type="checkbox" checked={kavachStates[sec]} onChange={() => handleKavachToggle(sec)}
                      style={{ accentColor: 'var(--accent)' }} />
                  </label>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Panel 2: Telemetry Inspector */}
        <div style={{
          background: 'var(--surface-panel)', border: '1px solid var(--border)',
          borderRadius: 'var(--rounded-md)', padding: '16px', display: 'flex', flexDirection: 'column'
        }}>
          <h4 style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-soft)', paddingBottom: '5px', marginBottom: '8px', marginTop: 0 }}>
            Telemetry Inspector
          </h4>

          {/* Route train list (when search active) */}
          {searchMode && !selectedTrain && (
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '3px', maxHeight: '180px' }}>
              {routeLoading && <div style={{ fontSize: '0.65rem', color: 'var(--ink-soft)', textAlign: 'center', padding: '20px' }}>Fetching live data…</div>}
              {!routeLoading && routeTrains.length === 0 && !routeError && (
                <div style={{ fontSize: '0.65rem', color: 'var(--color-text-dark)', textAlign: 'center', padding: '16px', fontStyle: 'italic' }}>
                  Enter stations above & click SEARCH to see live trains
                </div>
              )}
              {routeTrains.slice(0, 15).map((t, i) => {
                const no   = t.train_no || t.trainNo || '';
                const name = t.train_name || t.trainName || `Train ${no}`;
                const dep  = t.departure_time || t.departureTime || '--';
                const arr  = t.arrival_time || t.arrivalTime || '--';
                const dur  = t.duration || '--';
                return (
                  <div
                    key={i}
                    onClick={() => { setSelectedTrain({ train_no: no, train_name: name }); fetchLiveStatus(no); }}
                    style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      fontSize: '0.62rem', padding: '4px 7px', background: 'rgba(0,0,0,0.2)',
                      borderRadius: '4px', cursor: 'pointer', border: '1px solid transparent',
                      transition: 'border-color 0.15s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
                  >
                    <span style={{ fontWeight: 700, color: 'white', minWidth: '50px' }}>{no}</span>
                    <span style={{ color: 'var(--ink-soft)', flex: 1, marginLeft: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
                    <span style={{ color: 'var(--accent)', fontWeight: 700, marginLeft: '6px', whiteSpace: 'nowrap' }}>{dep}→{arr}</span>
                    <span style={{ color: 'var(--color-text-dark)', marginLeft: '6px' }}>{dur}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* No selection placeholder */}
          {!searchMode && !selectedTrain && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: '0.7rem', color: 'var(--color-text-dark)', fontStyle: 'italic', textAlign: 'center', padding: '10px' }}>
              Click on a train node or warning platform to inspect telemetry.
            </div>
          )}

          {/* Selected train detail */}
          {selectedTrain && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.7rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 800, color: 'white' }}>{selectedTrain.train_name}</span>
                <div style={{ display: 'flex', gap: '5px' }}>
                  <span style={{ color: 'var(--accent)', fontWeight: 700, fontFamily: 'monospace' }}>{selectedTrain.train_no}</span>
                  <button
                    onClick={() => setSelectedTrain(null)}
                    style={{ background: 'none', border: 'none', color: 'var(--ink-soft)', cursor: 'pointer', fontSize: '0.75rem' }}
                  >X</button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', background: 'rgba(0,0,0,0.2)', padding: '6px', borderRadius: '4px', fontSize: '0.62rem' }}>
                {selectedTrain.current_station && <div>Station: <strong style={{ color: 'white' }}>{selectedTrain.current_station}</strong></div>}
                {selectedTrain.status && <div>Status: <strong style={{ color: 'white' }}>{selectedTrain.status}</strong></div>}
                {(selectedTrain.current_delay !== undefined) && <div>Delay: <strong style={{ color: selectedTrain.current_delay > 0 ? 'var(--accent)' : 'var(--ink)' }}>{selectedTrain.current_delay > 0 ? `+${selectedTrain.current_delay}m` : 'On time'}</strong></div>}
                {selectedTrain.latitude > 0 && <div>Lat: <strong style={{ color: 'white' }}>{selectedTrain.latitude.toFixed(3)}</strong></div>}
                {selectedTrain.arrival_time && selectedTrain.arrival_time !== '--' && <div>Arrival: <strong style={{ color: 'white' }}>{selectedTrain.arrival_time}</strong></div>}
                {selectedTrain.departure_time && selectedTrain.departure_time !== '--' && <div>Departure: <strong style={{ color: 'white' }}>{selectedTrain.departure_time}</strong></div>}
                {selectedTrain.duration && selectedTrain.duration !== '--' && <div>Duration: <strong style={{ color: 'white' }}>{selectedTrain.duration}</strong></div>}
                {selectedTrain.classes && <div>Classes: <strong style={{ color: 'white' }}>{selectedTrain.classes}</strong></div>}
              </div>

              {/* Live status fetch result */}
              {liveLoading && <div style={{ fontSize: '0.62rem', color: 'var(--ink-soft)', textAlign: 'center' }}>Fetching live status…</div>}
              {liveStatus && !liveLoading && (
                <div style={{ background: 'var(--accent-subtle)', border: '1px solid var(--border-accent)', borderRadius: '4px', padding: '6px', fontSize: '0.62rem' }}>
                  <div style={{ color: 'var(--accent)', fontWeight: 700, marginBottom: '3px' }}>Live Telemetry</div>
                  {liveStatus.error ? (
                    <span style={{ color: 'var(--color-warning)' }}>Live status API unavailable</span>
                  ) : (
                    <pre style={{ margin: 0, fontSize: '0.55rem', color: 'var(--ink-soft)', overflowX: 'auto', maxHeight: '80px' }}>
                      {JSON.stringify(liveStatus.data, null, 1).substring(0, 400)}
                    </pre>
                  )}
                </div>
              )}

              {/* Speed lock */}
              <div style={{ marginTop: '2px' }}>
                <label style={{ fontSize: '0.62rem', color: 'var(--ink-soft)', display: 'block', marginBottom: '3px' }}>Safety Speed Lock (GZB-ALJN):</label>
                <div style={{ display: 'flex', gap: '5px' }}>
                  {[30, 60, 110, 130].map(sp => (
                    <button
                      key={sp}
                      onClick={() => handleSpeedLimitChange('GZB-ALJN', sp)}
                      style={{
                        flex: 1,
                        background: speedLimits['GZB-ALJN'] === sp ? 'var(--accent)' : 'transparent',
                        border: '1px solid var(--border)', borderRadius: '3px',
                        color: speedLimits['GZB-ALJN'] === sp ? 'var(--ink-on-red)' : 'var(--ink-soft)',
                        fontSize: '0.58rem', fontWeight: 'bold', padding: '3px 0', cursor: 'pointer',
                      }}
                    >{sp}</button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Panel 3: System Core Metrics & Autoplay */}
        <div style={{
          background: 'var(--surface-panel)', border: '1px solid var(--border)',
          borderRadius: 'var(--rounded-md)', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px'
        }}>
          <h4 style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--border-soft)', paddingBottom: '5px', margin: 0 }}>
            System Metrics
          </h4>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            {[
              ['LINE EFF', `${metrics.efficiency_score}%`, 'var(--ink)'],
              ['CAPACITY', `${metrics.capacity_load}%`, 'var(--accent)'],
              ['AVG SPEED', `${metrics.average_speed} km/h`, 'var(--ink)'],
              ['SAFETY IDX', `${metrics.safety_index}%`, 'var(--ink)'],
            ].map(([label, val, color]) => (
              <div key={label} style={{ background: 'var(--surface-elevated)', padding: '6px', border: '1px solid var(--border)', borderRadius: 'var(--rounded-xs)', textAlign: 'center' }}>
                <div style={{ color: 'var(--ink-muted)', fontSize: '10px', fontFamily: "'Inter', sans-serif", fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase' }}>{label}</div>
                <div style={{ fontWeight: 700, color, fontSize: '14px', fontFamily: "'JetBrains Mono', monospace", marginTop: '4px' }}>{val}</div>
              </div>
            ))}
          </div>

          {/* Active trains count */}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', background: 'var(--surface-input)', border: '1px solid var(--border)', borderRadius: 'var(--rounded-xs)', padding: '5px 8px' }}>
            <span style={{ color: 'var(--ink-soft)' }}>Active Trains</span>
            <span style={{ fontWeight: 700, color: 'var(--accent)' }}>{activeTrains.length}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', background: 'var(--surface-input)', border: '1px solid var(--border)', borderRadius: 'var(--rounded-xs)', padding: '5px 8px' }}>
            <span style={{ color: 'var(--ink-soft)' }}>Disruptions</span>
            <span style={{ fontWeight: 700, color: disruptions.some(d => d.status === 'ACTIVE') ? 'var(--accent)' : 'var(--ink-soft)' }}>
              {disruptions.filter(d => d.status === 'ACTIVE').length} ACTIVE
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', background: 'var(--surface-input)', border: '1px solid var(--border)', borderRadius: 'var(--rounded-xs)', padding: '5px 8px' }}>
            <span style={{ color: 'var(--ink-soft)' }}>Data Source</span>
            <span style={{ fontWeight: 700, color: 'var(--accent)', fontSize: '0.58rem' }}>
              {searchMode ? 'RapidAPI IRCTC' : 'SCENARIO+LIVE'}
            </span>
          </div>

          {/* Autoplay */}
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '5px' }}>
            <button
              className={autoplay ? 'btn-secondary' : 'btn-primary'}
              onClick={() => setAutoplay(!autoplay)}
              style={{
                width: '100%',
                height: '36px',
                padding: '0 20px',
                fontSize: '12px'
              }}
            >{autoplay ? 'PAUSE AUTOPLAY' : 'START AUTOPLAY'}</button>
            {autoplay && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ flexGrow: 1, height: '3px', background: 'var(--border)', overflow: 'hidden' }}>
                  <div style={{ width: `${(autoplayCountdown / 6) * 100}%`, height: '100%', background: 'var(--accent)', transition: 'width 1s linear' }} />
                </div>
                <span style={{ fontSize: '0.55rem', color: 'var(--ink-soft)' }}>{autoplayCountdown}s</span>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
