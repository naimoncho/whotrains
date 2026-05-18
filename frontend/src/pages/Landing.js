import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Landing.css';
 
const API = 'http://localhost:8000';
 
export default function Landing() {
  const navigate = useNavigate();
 
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      localStorage.setItem('wt_token', token);
      navigate('/dashboard');
    }
  }, [navigate]);
 
  const handleLogin = () => {
    window.location.href = `${API}/auth/login`;
  };
 
  return (
    <div className="landing">
      <div className="landing-noise" />
 
      <nav className="landing-nav">
        <span className="logo">WHO TRAINS?</span>
      </nav>
 
      <main className="landing-main">
        <div className="landing-tag">AI-powered training analysis</div>
 
        <h1 className="landing-title">
          KNOW<br />
          YOUR<br />
          <span className="accent">LIMITS.</span>
        </h1>
 
        <p className="landing-sub">
          Connect your Strava. Get weekly AI analysis of your training load,
          recovery, and next session — delivered straight to your phone.
        </p>
 
        <button className="btn-strava" onClick={handleLogin}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169"/>
          </svg>
          Connect with Strava
        </button>
 
        <div className="landing-features">
          <div className="feature">
            <span className="feature-icon">📊</span>
            <span>Training stats</span>
          </div>
          <div className="feature">
            <span className="feature-icon">🤖</span>
            <span>AI analysis</span>
          </div>
          <div className="feature">
            <span className="feature-icon">📱</span>
            <span>Push notifications</span>
          </div>
        </div>
      </main>
 
      <div className="landing-ticker">
        <div className="ticker-track">
          {Array(6).fill('WHO TRAINS? · STRAVA · AI COACH · WEEKLY ANALYSIS · PUSH NOTIFICATIONS · ').map((t, i) => (
            <span key={i}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
 