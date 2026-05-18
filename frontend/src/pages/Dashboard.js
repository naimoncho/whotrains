import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './Dashboard.css';

const API = 'http://localhost:8000';

const ZONE_COLORS = {
  'Z5 - Máximo':       '#ff4757',
  'Z4 - Umbral':       '#ff6b35',
  'Z3 - Tempo':        '#ffa502',
  'Z2 - Aeróbico Base':'#2ed573',
  'Z1 - Recuperación': '#1e90ff',
  'Sin FC':            '#444',
};

export default function Dashboard() {
  const navigate    = useNavigate();
  const [user, setUser]             = useState(null);
  const [activities, setActivities] = useState([]);
  const [stats, setStats]           = useState(null);
  const [analysis, setAnalysis]     = useState('');
  const [loading, setLoading]       = useState(true);
  const [analyzing, setAnalyzing]   = useState(false);
  const [activeTab, setActiveTab]   = useState('activities');

  const token  = localStorage.getItem('wt_token');
  const headers = { Authorization: `Bearer ${token}` };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!token) { navigate('/'); return; }
    // Handle post-payment redirect
    const params = new URLSearchParams(window.location.search);
    if (params.get('upgraded') === 'true') {
      window.history.replaceState({}, '', '/dashboard');
    }
    loadData();
  }, []);

  const loadData = async () => {
    try {
      // Load user + activities first
      const [userRes, actRes] = await Promise.all([
        axios.get(`${API}/me`, { headers }),
        axios.get(`${API}/activities?days=14`, { headers }),
      ]);
      setUser(userRes.data);
      setActivities(actRes.data);
      setLoading(false);

      // Load stats after (avoid Strava rate limit)
      try {
        const statsRes = await axios.get(`${API}/stats`, { headers });
        setStats(statsRes.data);
      } catch {
        // Stats fail silently — not critical
      }
    } catch {
      localStorage.removeItem('wt_token');
      navigate('/');
      setLoading(false);
    }
  };

  const handleAnalysis = async () => {
    setAnalyzing(true);
    try {
      const res = await axios.post(`${API}/analysis`, {}, { headers });
      setAnalysis(res.data.analysis);
      setActiveTab('analysis');
    } catch (e) {
      alert(e.response?.data?.detail || 'Error al generar el análisis');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleUpgrade = async () => {
    try {
      const res = await axios.post(`${API}/stripe/create-checkout`, {}, { headers });
      window.location.href = res.data.checkout_url;
    } catch (e) {
      alert('Error al iniciar el pago');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('wt_token');
    navigate('/');
  };

  if (loading) return (
    <div className="loading-screen">
      <div className="loading-spinner" />
      <p>Loading your data...</p>
    </div>
  );

  const runs   = activities.filter(a => a.type === 'Run');
  const totalKm = runs.reduce((s, a) => s + a.distance_km, 0).toFixed(1);

  // Zone data from stats (all year) or fallback to local activities
  const ZONE_ORDER = [
    'Z1 - Recuperación',
    'Z2 - Aeróbico Base',
    'Z3 - Tempo',
    'Z4 - Umbral',
    'Z5 - Máximo',
    'Sin FC',
  ];
  const zoneSource = stats?.zone_distribution || {};
  const zoneCounts = Object.keys(zoneSource).length > 0
    ? zoneSource
    : activities.reduce((acc, a) => {
        if (a.distance_km > 0) acc[a.zona] = (acc[a.zona] || 0) + a.distance_km;
        return acc;
      }, {});
  const zoneData = ZONE_ORDER
    .filter(name => zoneCounts[name] > 0)
    .map(name => ({
      name:  name.split(' - ')[0],
      km:    parseFloat(Number(zoneCounts[name]).toFixed(1)),
      color: ZONE_COLORS[name] || '#444'
    }));

  return (
    <div className="dashboard">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="sidebar-logo">WHO TRAINS?</div>

        {user && (
          <div className="user-card">
            {user.profile_pic && <img src={user.profile_pic} alt="" className="avatar" />}
            <div>
              <p className="user-name">{user.name}</p>
              <span className={`badge ${user.is_pro ? 'badge-pro' : 'badge-free'}`}>
                {user.is_pro ? 'PRO' : 'FREE'}
              </span>
            </div>
          </div>
        )}

        <nav className="sidebar-nav">
          <button className={activeTab === 'activities' ? 'active' : ''} onClick={() => setActiveTab('activities')}>
            Activities
          </button>
          <button className={activeTab === 'stats' ? 'active' : ''} onClick={() => setActiveTab('stats')}>
            Stats
          </button>
          {user?.is_pro && (
            <button className={activeTab === 'analysis' ? 'active' : ''} onClick={() => setActiveTab('analysis')}>
              AI Analysis
            </button>
          )}
        </nav>

        {user?.is_pro ? (
          <button className="btn-analyze" onClick={handleAnalysis} disabled={analyzing}>
            {analyzing ? 'Analyzing...' : 'Generate Analysis'}
          </button>
        ) : (
          <div className="upgrade-card">
            <p>Unlock AI-powered weekly analysis</p>
            <button className="btn-upgrade" onClick={handleUpgrade}>
              Upgrade to Pro — 4.99€/mo
            </button>
          </div>
        )}

        <button className="btn-logout" onClick={handleLogout}>Log out</button>
      </aside>

      {/* MAIN */}
      <main className="main-content">

        {activeTab === 'activities' && (
          <div className="tab-content">
            <div className="tab-header">
              <h2>LAST 14 DAYS</h2>
              <span className="total-km">{totalKm} km running</span>
            </div>
            <div className="activities-list">
              {activities.length === 0 && <p className="empty">No activities found.</p>}
              {activities.map(a => (
                <a
                  className="activity-card"
                  key={a.id}
                  href={`/activity/${a.id}`}
                >
                  <div className="activity-left">
                    <span className="activity-emoji">
                      {a.type === 'Run' ? '🏃' : a.type === 'Ride' ? '🚴' : a.type === 'Swim' ? '🏊' : '🏋️'}
                    </span>
                    <div>
                      <p className="activity-name">{a.name}</p>
                      <p className="activity-date">{a.date}</p>
                    </div>
                  </div>
                  <div className="activity-right">
                    {a.distance_km > 0 && <span className="activity-km">{a.distance_km} km</span>}
                    {a.pace !== '0' && <span className="activity-pace">{a.pace}</span>}
                    <span className="activity-zone" style={{ color: ZONE_COLORS[a.zona] || '#fff' }}>
                      {a.zona}
                    </span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'stats' && stats && (
          <div className="tab-content">
            <div className="tab-header">
              <h2>YOUR STATS</h2>
              <span className="total-km">All time</span>
            </div>

            <h3 className="stats-section-title">🏃 Running</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-value">{stats.total_runs}</span>
                <span className="stat-label">Carreras</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{stats.total_km_running}</span>
                <span className="stat-label">km</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{stats.total_hours_running}h</span>
                <span className="stat-label">Horas</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{stats.total_elevation_running}m</span>
                <span className="stat-label">Desnivel</span>
              </div>
            </div>

            <h3 className="stats-section-title">🚴 Ciclismo</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-value">{stats.total_rides}</span>
                <span className="stat-label">Salidas</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{stats.total_km_riding}</span>
                <span className="stat-label">km</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{stats.total_hours_riding}h</span>
                <span className="stat-label">Horas</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{stats.total_elevation_riding}m</span>
                <span className="stat-label">Desnivel</span>
              </div>
            </div>

            {stats.total_gym > 0 && (
              <>
                <h3 className="stats-section-title">🏋️ Gimnasio <span className="stats-note">(último año)</span></h3>
                <div className="stats-grid">
                  <div className="stat-card">
                    <span className="stat-value">{stats.total_gym}</span>
                    <span className="stat-label">Sesiones</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{stats.total_hours_gym}h</span>
                    <span className="stat-label">Horas</span>
                  </div>
                </div>
              </>
            )}

            {stats.total_swims > 0 && (
              <>
                <h3 className="stats-section-title">🏊 Natación</h3>
                <div className="stats-grid">
                  <div className="stat-card">
                    <span className="stat-value">{stats.total_swims}</span>
                    <span className="stat-label">Sesiones</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{stats.total_km_swimming}</span>
                    <span className="stat-label">km</span>
                  </div>
                </div>
              </>
            )}
            {zoneData.length > 0 && (
              <div className="chart-section">
                <h3>ZONE DISTRIBUTION (last 365 days)</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={zoneData} barSize={32}>
                    <XAxis dataKey="name" stroke="#444" tick={{ fill: '#999', fontSize: 12 }} />
                    <YAxis stroke="#444" tick={{ fill: '#999', fontSize: 12 }} unit=" km" />
                    <Tooltip
                      contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 4 }}
                      labelStyle={{ color: '#fff' }}
                      itemStyle={{ color: '#999' }}
                    />
                    <Bar dataKey="km" radius={[4, 4, 0, 0]}>
                      {zoneData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="tab-content">
            <div className="tab-header">
              <h2>AI ANALYSIS</h2>
            </div>
            {analysis ? (
              <div className="analysis-content">
                {analysis.split('\n').map((line, i) => (
                  <p key={i} className={line.startsWith('1.') || line.startsWith('2.') || line.startsWith('3.') ? 'analysis-section' : ''}>
                    {line}
                  </p>
                ))}
              </div>
            ) : (
              <div className="empty-analysis">
                <p>Click "Generate Analysis" to get your AI-powered training report.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}