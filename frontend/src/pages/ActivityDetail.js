import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, CartesianGrid
} from 'recharts';
import './ActivityDetail.css';

const API = 'http://localhost:8000';

const ZONE_COLORS = {
  'Z5 - Máximo':       '#ff4757',
  'Z4 - Umbral':       '#ff6b35',
  'Z3 - Tempo':        '#ffa502',
  'Z2 - Aeróbico Base':'#2ed573',
  'Z1 - Recuperación': '#1e90ff',
  'Sin FC':            '#555',
};

const ZONE_SHORT = {
  'Z5 - Máximo': 'Z5', 'Z4 - Umbral': 'Z4', 'Z3 - Tempo': 'Z3',
  'Z2 - Aeróbico Base': 'Z2', 'Z1 - Recuperación': 'Z1', 'Sin FC': '—',
};

/* ====================== SHARED COMPONENTS ====================== */

function HrChart({ data, zoneColor }) {
  if (!data || data.length === 0) return null;
  return (
    <div className="ad-chart-section">
      <h3>Frecuencia cardíaca</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="hrGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={zoneColor} stopOpacity={0.4} />
              <stop offset="95%" stopColor={zoneColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#222" />
          <XAxis dataKey="time_sec" tickFormatter={v => `${Math.floor(v / 60)}'`}
            stroke="#444" tick={{ fill: '#888', fontSize: 11 }} />
          <YAxis domain={['dataMin - 10', 'dataMax + 10']} stroke="#444"
            tick={{ fill: '#888', fontSize: 11 }} unit=" bpm" />
          <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 6 }}
            labelFormatter={v => `${Math.floor(v / 60)}:${String(v % 60).padStart(2, '0')}`}
            formatter={(val) => [`${val} bpm`, 'FC']} />
          <Area type="monotone" dataKey="hr" stroke={zoneColor} strokeWidth={2} fill="url(#hrGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function AltChart({ data }) {
  if (!data || data.length === 0) return null;
  return (
    <div className="ad-chart-section">
      <h3>Altitud</h3>
      <ResponsiveContainer width="100%" height={150}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="altGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#666" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#666" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#222" />
          <XAxis dataKey="distance_km" stroke="#444" tick={{ fill: '#888', fontSize: 11 }} unit=" km" />
          <YAxis stroke="#444" tick={{ fill: '#888', fontSize: 11 }} unit="m" />
          <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 6 }}
            formatter={(val) => [`${val}m`, 'Altitud']} />
          <Area type="monotone" dataKey="altitude" stroke="#888" strokeWidth={1.5} fill="url(#altGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function RouteMap({ route, color }) {
  if (!route || route.length === 0) return null;
  return (
    <div className="ad-chart-section">
      <h3>Ruta</h3>
      <div className="ad-map">
        <svg viewBox={getMapViewBox(route)} className="ad-route-svg">
          <polyline
            points={route.map(([lat, lng]) => `${lng},${-lat}`).join(' ')}
            fill="none" stroke={color} strokeWidth="0.001"
            strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

function Stat({ value, label, color }) {
  return (
    <div className="ad-stat">
      <span className="ad-stat-value" style={color ? { color } : {}}>{value}</span>
      <span className="ad-stat-label">{label}</span>
    </div>
  );
}

/* ====================== RUN LAYOUT ====================== */

function RunDetail({ a, zoneColor }) {
  return (
    <>
      <div className="ad-stats-grid">
        <Stat value={`${a.distance_km} km`} label="Distancia" />
        <Stat value={`${a.duration_min}m`} label="Tiempo activo" />
        <Stat value={a.pace} label="Ritmo medio" />
        <Stat value={a.max_speed_pace} label="Ritmo máximo" />
        {a.fc > 0 && <Stat value={`${a.fc} bpm`} label="FC media" />}
        {a.fc_max > 0 && <Stat value={`${a.fc_max} bpm`} label="FC máx" />}
        <Stat value={`${a.elevation_gain}m`} label="Desnivel" />
        {a.calories > 0 && <Stat value={a.calories} label="Calorías" />}
        <Stat value={a.load} label="Carga (TRIMP)" color={zoneColor} />
      </div>

      <HrChart data={a.hr_chart} zoneColor={zoneColor} />
      <AltChart data={a.alt_chart} />

      {a.splits && a.splits.length > 0 && (
        <div className="ad-chart-section">
          <h3>Splits</h3>
          <div className="ad-splits-table">
            <div className="ad-splits-header">
              <span>#</span><span>Distancia</span><span>Ritmo</span>
              <span>FC</span><span>Zona</span><span>Desnivel</span>
            </div>
            {a.splits.map((s, i) => (
              <div className="ad-splits-row" key={i}>
                <span className="ad-split-num">{i + 1}</span>
                <span>{s.distance_km} km</span>
                <span className="ad-split-pace">{s.pace}</span>
                <span>{s.fc > 0 ? s.fc : '—'}</span>
                <span style={{ color: ZONE_COLORS[s.zona] || '#888' }}>{ZONE_SHORT[s.zona] || '—'}</span>
                <span>{s.elevation_gain > 0 ? `+${s.elevation_gain}m` : '—'}</span>
              </div>
            ))}
          </div>
          <div className="ad-splits-chart">
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={a.splits.map((s, i) => ({
                name: `${i + 1}`, pace_sec: s.moving_time / (s.distance_km || 1), zona: s.zona,
              }))}>
                <XAxis dataKey="name" stroke="#444" tick={{ fill: '#888', fontSize: 11 }} />
                <YAxis hide reversed />
                <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 6 }}
                  formatter={(val) => {
                    const m = Math.floor(val / 60); const s = Math.round(val % 60);
                    return [`${m}:${String(s).padStart(2, '0')} /km`, 'Ritmo'];
                  }} />
                <Bar dataKey="pace_sec" radius={[4, 4, 0, 0]}>
                  {a.splits.map((s, i) => <Cell key={i} fill={ZONE_COLORS[s.zona] || '#555'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <RouteMap route={a.route} color={zoneColor} />
    </>
  );
}

/* ====================== RIDE LAYOUT ====================== */

function RideDetail({ a, zoneColor }) {
  return (
    <>
      <div className="ad-stats-grid">
        <Stat value={`${a.distance_km} km`} label="Distancia" />
        <Stat value={`${a.duration_min}m`} label="Tiempo activo" />
        <Stat value={`${a.avg_speed_kmh || '—'} km/h`} label="Velocidad media" />
        <Stat value={`${a.max_speed_kmh || '—'} km/h`} label="Velocidad máx" />
        <Stat value={`${a.elevation_gain}m`} label="Desnivel" />
        {a.fc > 0 && <Stat value={`${a.fc} bpm`} label="FC media" />}
        {a.fc_max > 0 && <Stat value={`${a.fc_max} bpm`} label="FC máx" />}
        {a.avg_watts > 0 && <Stat value={`${a.avg_watts}W`} label="Potencia media" />}
        {a.max_watts > 0 && <Stat value={`${a.max_watts}W`} label="Potencia máx" />}
        {a.weighted_avg_watts > 0 && <Stat value={`${a.weighted_avg_watts}W`} label="NP (Normalized)" />}
        {a.kilojoules > 0 && <Stat value={`${a.kilojoules} kJ`} label="Energía" />}
        {a.calories > 0 && <Stat value={a.calories} label="Calorías" />}
        <Stat value={a.load} label="Carga" color={zoneColor} />
      </div>

      <HrChart data={a.hr_chart} zoneColor={zoneColor} />
      <AltChart data={a.alt_chart} />

      {/* Speed splits */}
      {a.splits && a.splits.length > 0 && (
        <div className="ad-chart-section">
          <h3>Splits</h3>
          <div className="ad-splits-table">
            <div className="ad-splits-header ad-splits-header--ride">
              <span>#</span><span>Distancia</span><span>Vel. media</span>
              <span>FC</span><span>Desnivel</span>
            </div>
            {a.splits.map((s, i) => (
              <div className="ad-splits-row ad-splits-row--ride" key={i}>
                <span className="ad-split-num">{i + 1}</span>
                <span>{s.distance_km} km</span>
                <span className="ad-split-pace">{s.pace}</span>
                <span>{s.fc > 0 ? s.fc : '—'}</span>
                <span>{s.elevation_gain > 0 ? `+${s.elevation_gain}m` : '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <RouteMap route={a.route} color={zoneColor} />
    </>
  );
}

/* ====================== GYM / WEIGHT LAYOUT ====================== */

function GymDetail({ a, zoneColor }) {
  return (
    <>
      <div className="ad-stats-grid">
        <Stat value={`${a.duration_min}m`} label="Duración" />
        <Stat value={`${a.elapsed_min}m`} label="Tiempo total" />
        {a.fc > 0 && <Stat value={`${a.fc} bpm`} label="FC media" />}
        {a.fc_max > 0 && <Stat value={`${a.fc_max} bpm`} label="FC máx" />}
        {a.calories > 0 && <Stat value={a.calories} label="Calorías" />}
        <Stat value={a.load} label="Carga" color={zoneColor} />
      </div>

      <HrChart data={a.hr_chart} zoneColor={zoneColor} />

      {/* Gym has no map, no altitude, no splits — just the effort summary */}
      {a.hr_chart && a.hr_chart.length > 0 && (
        <div className="ad-chart-section">
          <h3>Resumen de esfuerzo</h3>
          <div className="ad-effort-summary">
            {Object.entries(
              a.hr_chart.reduce((acc, p) => {
                const z = p.zona || 'Sin FC';
                acc[z] = (acc[z] || 0) + 1;
                return acc;
              }, {})
            )
              .sort(([, a], [, b]) => b - a)
              .map(([zona, count]) => {
                const pct = Math.round((count / a.hr_chart.length) * 100);
                return (
                  <div className="ad-effort-bar-row" key={zona}>
                    <span className="ad-effort-label" style={{ color: ZONE_COLORS[zona] || '#888' }}>
                      {ZONE_SHORT[zona] || zona}
                    </span>
                    <div className="ad-effort-track">
                      <div
                        className="ad-effort-fill"
                        style={{ width: `${pct}%`, background: ZONE_COLORS[zona] || '#555' }}
                      />
                    </div>
                    <span className="ad-effort-pct">{pct}%</span>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </>
  );
}

/* ====================== SWIM LAYOUT ====================== */

function SwimDetail({ a, zoneColor }) {
  return (
    <>
      <div className="ad-stats-grid">
        <Stat value={`${a.distance_km * 1000}m`} label="Distancia" />
        <Stat value={`${a.duration_min}m`} label="Tiempo activo" />
        <Stat value={a.pace_100m || '—'} label="Ritmo /100m" />
        {a.pool_length > 0 && <Stat value={`${a.pool_length}m`} label="Largo piscina" />}
        {a.avg_strokes > 0 && <Stat value={`${a.avg_strokes}`} label="Brazadas/min" />}
        {a.total_strokes > 0 && <Stat value={a.total_strokes} label="Brazadas totales" />}
        {a.fc > 0 && <Stat value={`${a.fc} bpm`} label="FC media" />}
        {a.fc_max > 0 && <Stat value={`${a.fc_max} bpm`} label="FC máx" />}
        {a.calories > 0 && <Stat value={a.calories} label="Calorías" />}
        <Stat value={a.load} label="Carga" color={zoneColor} />
      </div>

      <HrChart data={a.hr_chart} zoneColor={zoneColor} />

      {a.splits && a.splits.length > 0 && (
        <div className="ad-chart-section">
          <h3>Splits por largo</h3>
          <div className="ad-splits-table">
            <div className="ad-splits-header ad-splits-header--swim">
              <span>#</span><span>Distancia</span><span>Ritmo</span><span>FC</span>
            </div>
            {a.splits.map((s, i) => (
              <div className="ad-splits-row ad-splits-row--swim" key={i}>
                <span className="ad-split-num">{i + 1}</span>
                <span>{Math.round(s.distance_km * 1000)}m</span>
                <span className="ad-split-pace">{s.pace}</span>
                <span>{s.fc > 0 ? s.fc : '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

/* ====================== MAIN PAGE ====================== */

export default function ActivityDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem('wt_token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    if (!token) { navigate('/'); return; }
    loadActivity();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadActivity = async () => {
    try {
      const res = await axios.get(`${API}/activity/${id}`, { headers });
      setActivity(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al cargar la actividad');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="ad-loading"><div className="loading-spinner" /><p>Cargando actividad...</p></div>
  );
  if (error) return (
    <div className="ad-loading"><p>{error}</p>
      <button className="ad-back-btn" onClick={() => navigate('/dashboard')}>Volver</button>
    </div>
  );

  const a = activity;
  const emoji = { Run: '🏃', Ride: '🚴', Swim: '🏊', WeightTraining: '🏋️', Hike: '🥾' }[a.type] || '🏃';
  const zoneColor = ZONE_COLORS[a.zona] || '#555';
  const typeLabel = { Run: 'Carrera', Ride: 'Ciclismo', Swim: 'Natación', WeightTraining: 'Gimnasio', Hike: 'Senderismo' }[a.type] || a.type;

  return (
    <div className="ad-page">
      <div className="ad-topbar">
        <button className="ad-back-btn" onClick={() => navigate('/dashboard')}>← Volver</button>
        <a href={`https://www.strava.com/activities/${a.id}`} target="_blank"
          rel="noopener noreferrer" className="ad-strava-link">Ver en Strava ↗</a>
      </div>

      <div className="ad-header">
        <div className="ad-header-top">
          <span className="ad-emoji">{emoji}</span>
          <div>
            <h1 className="ad-title">{a.name}</h1>
            <p className="ad-subtitle">{a.date} · {a.start_time} · {typeLabel}</p>
          </div>
        </div>
        <span className="ad-zone-badge" style={{ background: zoneColor }}>{a.zona}</span>
      </div>

      {a.type === 'Run' && <RunDetail a={a} zoneColor={zoneColor} />}
      {a.type === 'Ride' && <RideDetail a={a} zoneColor={zoneColor} />}
      {a.type === 'WeightTraining' && <GymDetail a={a} zoneColor={zoneColor} />}
      {a.type === 'Swim' && <SwimDetail a={a} zoneColor={zoneColor} />}
      {!['Run', 'Ride', 'WeightTraining', 'Swim'].includes(a.type) && (
        <RunDetail a={a} zoneColor={zoneColor} />
      )}
    </div>
  );
}

function getMapViewBox(route) {
  if (!route.length) return "0 0 1 1";
  const lats = route.map(p => -p[0]);
  const lngs = route.map(p => p[1]);
  const minLat = Math.min(...lats); const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs); const maxLng = Math.max(...lngs);
  const padLat = (maxLat - minLat) * 0.1 || 0.001;
  const padLng = (maxLng - minLng) * 0.1 || 0.001;
  return `${minLng - padLng} ${minLat - padLat} ${maxLng - minLng + padLng * 2} ${maxLat - minLat + padLat * 2}`;
}
