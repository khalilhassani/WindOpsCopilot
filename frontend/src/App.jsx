import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

/* ═══════════════════════════════════════════════════════
   WindOps Copilot — Administration Publique du Maroc
   المملكة المغربية — الإدارة العمومية بالمغرب — الطاقة الريحية
   ═══════════════════════════════════════════════════════ */

// Reusable Moroccan Zellige SVG Component
const ZelligePattern = ({ className }) => (
  <svg className={`zellige-overlay ${className}`} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <g stroke="currentColor" strokeWidth="0.6" fill="none">
      <polygon points="50,5 82,18 95,50 82,82 50,95 18,82 5,50 18,18" />
      <polygon points="50,15 75,25 85,50 75,75 50,85 25,75 15,50 25,25" />
      <polygon points="50,25 68,32 75,50 68,68 50,75 32,68 25,50 32,32" />
      <polygon points="50,35 60,40 65,50 60,60 50,65 40,60 35,50 40,40" />
      <line x1="50" y1="0" x2="50" y2="100" />
      <line x1="0" y1="50" x2="100" y2="50" />
      <line x1="15" y1="15" x2="85" y2="85" />
      <line x1="15" y1="85" x2="85" y2="15" />
      <path d="M50,35 L55,45 L65,50 L55,55 L50,65 L45,55 L35,50 L45,45 Z" fill="currentColor" opacity="0.15" />
    </g>
  </svg>
);

function App() {
  // ── State Management ──
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'simulation' | 'reports'
  const [turbines, setTurbines] = useState([]);
  const [selectedTurbineId, setSelectedTurbineId] = useState('WTG-001');
  const [kpi, setKpi] = useState({
    total_turbines: 0,
    avg_health: 100,
    active_alerts: 0,
    avg_latency_seconds: 0,
    db_mode: 'mock'
  });
  const [emails, setEmails] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [latestRunResult, setLatestRunResult] = useState(null);

  const [simParams, setSimParams] = useState({
    wind_speed: 12.0,
    rotor_speed: 16.5,
    blade_temp: 24.5,
    generator_temp: 52.0,
    vibration: 0.08,
    power_output: 2.4,
    status: 'active'
  });

  // ── Data Fetching ──
  useEffect(() => {
    fetchTurbines();
    fetchKPIs();
    fetchEmails();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      fetchTurbines();
      fetchKPIs();
      fetchEmails();
    }, 6000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const activeTurbine = turbines.find(t => t.turbine_id === selectedTurbineId);
    if (activeTurbine) {
      setSimParams(prev => ({ ...prev, status: activeTurbine.status }));
    }
  }, [selectedTurbineId, turbines]);

  const fetchTurbines = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/turbines`);
      if (res.ok) setTurbines(await res.json());
    } catch (e) { console.error('Échec de récupération des turbines', e); }
  };

  const fetchKPIs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/metrics`);
      if (res.ok) setKpi(await res.json());
    } catch (e) { console.error('Échec de récupération des métriques', e); }
  };

  const fetchEmails = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/emails`);
      if (res.ok) setEmails(await res.json());
    } catch (e) { console.error('Échec de récupération des e-mails', e); }
  };

  // ── Anomaly Presets ──
  const applyPreset = (type) => {
    const presets = {
      nominal: { wind_speed: 12.0, rotor_speed: 16.5, blade_temp: 24.5, generator_temp: 52.0, vibration: 0.08, power_output: 2.4, status: 'active' },
      storm: { wind_speed: 28.5, rotor_speed: 4.2, blade_temp: 18.0, generator_temp: 32.0, vibration: 0.14, power_output: 0.0, status: 'active' },
      vibration: { wind_speed: 14.5, rotor_speed: 18.0, blade_temp: 29.0, generator_temp: 61.5, vibration: 0.29, power_output: 2.8, status: 'active' },
      overheat: { wind_speed: 10.0, rotor_speed: 12.5, blade_temp: 22.0, generator_temp: 84.5, vibration: 0.11, power_output: 0.8, status: 'active' },
      offline: { wind_speed: 4.0, rotor_speed: 0.0, blade_temp: 15.0, generator_temp: 20.0, vibration: 0.0, power_output: 0.0, status: 'offline' }
    };
    if (presets[type]) setSimParams(presets[type]);
  };

  // ── Ingest Telemetry ──
  const runIngest = async () => {
    setIsProcessing(true);
    setLatestRunResult(null);
    try {
      const payload = {
        turbine_id: selectedTurbineId,
        wind_speed: parseFloat(simParams.wind_speed),
        rotor_speed: parseFloat(simParams.rotor_speed),
        blade_temp: parseFloat(simParams.blade_temp),
        generator_temp: parseFloat(simParams.generator_temp),
        vibration: parseFloat(simParams.vibration),
        power_output: parseFloat(simParams.power_output),
        status: simParams.status
      };

      const res = await fetch(`${API_BASE}/api/telemetry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const result = await res.json();
        setLatestRunResult(result);
        fetchTurbines();
        fetchKPIs();
        fetchEmails();
        // Automatically switch to reports tab so the operator can see the detailed multi-agent execution run
        setActiveTab('reports');
      } else {
        alert('Échec de l\'envoi de la télémétrie');
      }
    } catch (e) {
      console.error(e);
      alert('Erreur de connexion à l\'API du backend');
    } finally {
      setIsProcessing(false);
    }
  };

  // ── Agent color mapping for timeline ──
  const getAgentMeta = (log) => {
    if (log.includes('Monitoring Agent'))  return { name: 'Agent de Surveillance',  color: '#28a745' };
    if (log.includes('Diagnosis Agent'))   return { name: 'Agent de Diagnostic',     color: '#fd7e14' };
    if (log.includes('Decision Agent'))    return { name: 'Agent de Décision',       color: '#dc3545' };
    if (log.includes('Reporting Agent'))   return { name: 'Agent de Rapports',       color: '#0284c7' };
    if (log.includes('System Completed'))  return { name: 'Système Finalisé',        color: '#28a745' };
    return { name: 'Superviseur', color: '#4caf50' };
  };

  // ── Health color utility ──
  const healthColor = (score) => score >= 85 ? '#28a745' : (score >= 60 ? '#fd7e14' : '#dc3545');

  // ── Dynamic SVG Chart Data mapping ──
  const getChartData = (turbineId) => {
    const dataMap = {
      'WTG-001': [95, 96, 95, 97, 98, 97, 98, 99, 100, 98, 99, 100],
      'WTG-002': [90, 88, 85, 82, 80, 75, 62, 55, 45, 48, 52, 45],
      'WTG-003': [95, 95, 92, 90, 85, 70, 40, 20, 0, 0, 0, 0],
      'WTG-004': [98, 98, 99, 97, 98, 99, 100, 100, 99, 100, 99, 100]
    };
    return dataMap[turbineId] || [85, 88, 87, 89, 90, 92, 91, 93, 94, 95, 96, 95];
  };

  // Build SVG Path helper
  const generateSvgPath = (data, width, height, padding) => {
    const activeWidth = width - padding.left - padding.right;
    const activeHeight = height - padding.top - padding.bottom;
    const points = data.map((val, idx) => {
      const x = padding.left + (idx * (activeWidth / (data.length - 1)));
      const y = padding.top + activeHeight - (val / 100) * activeHeight;
      return { x, y };
    });

    const lineD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    const areaD = `${lineD} L ${points[points.length - 1].x.toFixed(1)} ${(padding.top + activeHeight).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padding.top + activeHeight).toFixed(1)} Z`;
    return { lineD, areaD, points };
  };

  const chartData = getChartData(selectedTurbineId);
  const chartWidth = 680;
  const chartHeight = 180;
  const chartPadding = { left: 40, right: 20, top: 15, bottom: 25 };
  const { lineD, areaD, points: chartPoints } = generateSvgPath(chartData, chartWidth, chartHeight, chartPadding);
  const months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'];

  // ── Render Turbine SVG Helper ──
  const renderTurbineSvg = (status) => {
    const isOffline = status === 'offline';
    const rotorRPM = isOffline ? 0 : (status === 'curtailed' ? 8.0 : 16.5);
    const rotationStyle = rotorRPM > 0
      ? { '--rotor-speed': `${60 / rotorRPM}s` }
      : { animationPlayState: 'paused' };

    return (
      <svg width="65" height="105" viewBox="0 0 100 150" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="towerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#cbd5e1" />
            <stop offset="50%" stopColor="#f1f5f9" />
            <stop offset="100%" stopColor="#94a3b8" />
          </linearGradient>
          <linearGradient id="bladeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8cd08c" />
            <stop offset="100%" stopColor="#2e7d32" />
          </linearGradient>
          <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(76, 175, 80, 0.25)" />
            <stop offset="100%" stopColor="rgba(76, 175, 80, 0.0)" />
          </linearGradient>
        </defs>
        <path d="M 12 143 C 40 134, 60 134, 88 143 L 88 148 L 12 148 Z" fill="#cbd5e1" opacity="0.5" />
        <polygon points="47,140 53,140 51.5,58 48.5,58" fill="url(#towerGrad)" />
        <rect x="42" y="140" width="16" height="3" rx="1.5" fill="#64748b" />
        <rect x="43" y="53" width="14" height="7" rx="2" fill="#3d8b40" />
        <path d="M 57 53 L 60 56.5 L 57 60 Z" fill="#c5963a" />
        <g className="rotor" style={rotationStyle}>
          <circle cx="50" cy="56.5" r="4" fill="#f8fafc" stroke="#2e7d32" strokeWidth="1.5" />
          <path d="M 50 56.5 L 50 14 C 51.5 24, 51 42, 50 56.5 Z" fill="url(#bladeGrad)" stroke="#1b5e20" strokeWidth="0.5" />
          <path d="M 50 56.5 L 86 78 C 76 74, 61 64, 50 56.5 Z" fill="url(#bladeGrad)" stroke="#1b5e20" strokeWidth="0.5" />
          <path d="M 50 56.5 L 14 78 C 24 74, 39 64, 50 56.5 Z" fill="url(#bladeGrad)" stroke="#1b5e20" strokeWidth="0.5" />
        </g>
      </svg>
    );
  };

  // Find active turbine details for the selected card
  const selectedTurbine = turbines.find(t => t.turbine_id === selectedTurbineId) || {
    turbine_id: selectedTurbineId,
    status: 'active',
    health_score: 100,
    active_alerts_count: 0
  };

  return (
    <div className="app-layout">
      {/* Corner Zellige Ornament Overlay */}
      <ZelligePattern className="top-left" />
      <ZelligePattern className="top-right" />
      <ZelligePattern className="bottom-right" />

      {/* ══════ LEFT SIDEBAR NAVIGATION ══════ */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="45" stroke="#c5963a" strokeWidth="1.5" fill="none" strokeDasharray="3 3"/>
            <g transform="translate(50,45)">
              <line x1="0" y1="0" x2="0" y2="-28" stroke="#3d8b40" strokeWidth="4" strokeLinecap="round"/>
              <line x1="0" y1="0" x2="24" y2="14" stroke="#3d8b40" strokeWidth="4" strokeLinecap="round"/>
              <line x1="0" y1="0" x2="-24" y2="14" stroke="#3d8b40" strokeWidth="4" strokeLinecap="round"/>
              <circle cx="0" cy="0" r="4" fill="#c5963a"/>
            </g>
            <rect x="47" y="45" width="6" height="35" rx="2.5" fill="#3d8b40" />
            <rect x="36" y="80" width="28" height="4" rx="2" fill="#c5963a" />
          </svg>
        </div>
        <nav className="sidebar-menu">
          <div className={`sidebar-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <svg viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
            </svg>
            <span className="sidebar-label">Régie</span>
          </div>
          <div className={`sidebar-item ${activeTab === 'simulation' ? 'active' : ''}`} onClick={() => setActiveTab('simulation')}>
            <svg viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
            </svg>
            <span className="sidebar-label">Simulateur</span>
          </div>
          <div className={`sidebar-item ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
            <svg viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0l-7.5-4.615a2.25 2.25 0 0 1-1.07-1.916V6.75" />
            </svg>
            <span className="sidebar-label">Alertes</span>
          </div>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-item" onClick={() => applyPreset('nominal')}>
            <svg viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <span className="sidebar-label">Mise à Zéro</span>
          </div>
        </div>
      </aside>

      {/* ══════ MAIN CONTENT PANEL ══════ */}
      <main className="main-content">

        {/* ─── Page Header / Branding ─── */}
        <header className="page-header">
          <div className="logo-block">
            <div className="logo-svg-wrap">
              <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <g transform="translate(50,35)">
                  <line x1="0" y1="0" x2="0" y2="-28" stroke="white" strokeWidth="4.5" strokeLinecap="round"/>
                  <line x1="0" y1="0" x2="24" y2="14" stroke="white" strokeWidth="4.5" strokeLinecap="round"/>
                  <line x1="0" y1="0" x2="-24" y2="14" stroke="white" strokeWidth="4.5" strokeLinecap="round"/>
                  <circle cx="0" cy="0" r="4.5" fill="white"/>
                </g>
                <rect x="47" y="35" width="6" height="35" rx="3.5" fill="white" opacity="0.9" />
                <rect x="38" y="70" width="24" height="5" rx="2" fill="white" opacity="0.8" />
              </svg>
            </div>
            <div className="logo-text-wrap">
              <p className="logo-top-arabic">المملكة المغربية</p>
              <h1 className="logo-main-title">WindOps Copilot</h1>
              <p className="logo-sub-french">Administration Publique du Maroc — Énergie Éolienne</p>
              <p className="logo-sub-arabic">وزارة الانتقال الطاقي والتنمية المستدامة — الإدارة العمومية بالمغرب</p>
            </div>
          </div>
          <div className="header-controls">
            <div className="tab-container">
              <button className={`tab-button ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
                Tableau de Bord
              </button>
              <button className={`tab-button ${activeTab === 'simulation' ? 'active' : ''}`} onClick={() => setActiveTab('simulation')}>
                Simulation & Flotte
              </button>
              <button className={`tab-button ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
                Historique & Rapports
              </button>
            </div>
            <button className="btn btn-refresh" onClick={() => { fetchTurbines(); fetchKPIs(); fetchEmails(); }}>
              ⟳ Synchroniser
            </button>
          </div>
        </header>

        {/* ─── KPI Metric Cards Overview ─── */}
        <section className="kpi-summary-row">
          <div className="kpi-card">
            <div className="kpi-title-wrap">
              <span className="kpi-label">Turbines Actives</span>
              <div className="kpi-icon-circle">⚡</div>
            </div>
            <span className="kpi-value">{kpi.total_turbines || turbines.length}</span>
          </div>
          <div className="kpi-card health">
            <div className="kpi-title-wrap">
              <span className="kpi-label">Santé Moyenne</span>
              <div className="kpi-icon-circle">💚</div>
            </div>
            <span className="kpi-value">{kpi.avg_health}%</span>
          </div>
          <div className="kpi-card alerts">
            <div className="kpi-title-wrap">
              <span className="kpi-label">Alertes Actives</span>
              <div className="kpi-icon-circle">⚠</div>
            </div>
            <span className="kpi-value" style={{ color: kpi.active_alerts > 0 ? '#dc3545' : undefined }}>
              {kpi.active_alerts}
            </span>
          </div>
          <div className="kpi-card latency">
            <div className="kpi-title-wrap">
              <span className="kpi-label">Latence Agents</span>
              <div className="kpi-icon-circle">⏱</div>
            </div>
            <span className="kpi-value">{kpi.avg_latency_seconds}s</span>
          </div>
        </section>

        {/* ═══════════════════════════════════════════
            TAB 1: DASHBOARD MAIN VIEW
            ═══════════════════════════════════════════ */}
        {activeTab === 'dashboard' && (
          <div className="dashboard-layout-grid">
            
            {/* 1. Supervisor Status Card */}
            <div className="panel panel-supervisor">
              <h3 className="panel-heading">
                <svg viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/></svg>
                Supervisor Orchestrator
              </h3>
              <div className="supervisor-switch-row">
                <span className="supervisor-switch-label">
                  <span className="supervisor-status-dot" />
                  État Graph
                </span>
                <label className="switch">
                  <input type="checkbox" defaultChecked readOnly disabled />
                  <span className="slider-round" />
                </label>
              </div>
              <div className="supervisor-meta-group">
                <span className="supervisor-meta-label">Correlation ID</span>
                <span className="supervisor-meta-value" title={latestRunResult?.correlation_id || "WINDFARM-RUN-2026-ALPHA"}>
                  {latestRunResult?.correlation_id || "WINDFARM-RUN-2026-ALPHA"}
                </span>
              </div>
            </div>

            {/* 2. Critical Alert Panel */}
            <div className="panel panel-alert-critique">
              <h3 className="panel-heading" style={{ color: '#dc3545', borderBottomColor: '#fca5a5' }}>
                <svg viewBox="0 0 24 24" style={{ stroke: '#dc3545' }}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"/></svg>
                Alerte Critique
              </h3>
              <div className="alert-critique-container">
                {selectedTurbine.active_alerts_count > 0 ? (
                  <>
                    <div className="alert-critique-icon-wrap">
                      <svg viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0 3.75h.008v.008H12v-.008ZM21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                      {selectedTurbine.status === 'curtailed' ? 'Alerte Thermique détectée' : 'Anomalie Turbine détectée'}
                    </div>
                    <p className="alert-critique-desc">
                      Télémétrie en dehors des limites de sécurité sur la turbine {selectedTurbine.turbine_id}. Santé abaissée à {selectedTurbine.health_score}%.
                    </p>
                    <button className="alert-critique-btn" onClick={() => setActiveTab('simulation')}>
                      Évaluer l'alerte
                    </button>
                  </>
                ) : (
                  <p className="alert-nominal-text">
                    <span className="alert-nominal-dot" />
                    Aucune alerte critique détectée. La turbine {selectedTurbine.turbine_id} fonctionne de façon optimale.
                  </p>
                )}
              </div>
            </div>

            {/* 3. Decision Support Card */}
            <div className="panel panel-decision-support">
              <h3 className="panel-heading">
                <svg viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0V3m7.5 13.5V3M3.75 21h16.5M12 6.75a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM18 11.25a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z"/></svg>
                Aide à la Décision
              </h3>
              <div className="decision-support-container">
                <div className="decision-support-header">
                  <span className="decision-support-title">Action recommandée</span>
                  <span style={{ fontSize: '0.68rem', background: 'rgba(255,255,255,0.2)', padding: '0.1rem 0.4rem', borderRadius: '4px', fontWeight: 700 }}>
                    {selectedTurbine.health_score < 85 ? 'Prioritaire' : 'Standard'}
                  </span>
                </div>
                <p className="decision-support-desc">
                  {selectedTurbine.health_score < 60
                    ? 'Déclenchement immédiat de l\'arrêt d\'urgence recommandé.'
                    : (selectedTurbine.health_score < 85
                      ? 'Réduction de puissance émise (50% de charge) ou maintenance préventive à programmer.'
                      : 'Maintenir les opérations nominales sur l\'ensemble des turbines éoliennes.')
                  }
                </p>
                <div className="decision-support-actions">
                  <div className="decision-support-btn primary" onClick={() => setActiveTab('reports')}>Voir Décisions</div>
                  <div className="decision-support-btn secondary" onClick={() => setActiveTab('simulation')}>Modifier Paramètres</div>
                </div>
              </div>
            </div>

            {/* 4. Agent Health Status Panel */}
            <div className="panel panel-agents-health">
              <h3 className="panel-heading">
                <svg viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.97 5.97 0 0 0-.75-2.985m-.001-3.978a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm-9.75 3.978a9.054 9.054 0 0 0-3.741-.479 3 3 0 0 0-4.682 2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c2.17 0 4.207-.576 5.963-1.584A6.062 6.062 0 0 0 18 18.722m-12 0a5.97 5.97 0 0 1 .75-2.985m-.001-3.978a3 3 0 1 0-6 0 3 3 0 0 1 6 0Z"/></svg>
                Santé des Agents
              </h3>
              <div className="agent-health-list">
                <div className="agent-health-card monitoring">
                  <div className="agent-identity">
                    <span className="agent-circle-icon">🔍</span>
                    <span className="agent-title-text">Surveillance</span>
                  </div>
                  <div className="agent-metrics">
                    <span className="agent-pct-value">100%</span>
                    <span className="agent-health-status-dot nominal" />
                  </div>
                </div>

                <div className="agent-health-card diagnosis">
                  <div className="agent-identity">
                    <span className="agent-circle-icon">⚙</span>
                    <span className="agent-title-text">Diagnostic</span>
                  </div>
                  <div className="agent-metrics">
                    <span className="agent-pct-value">{selectedTurbine.health_score < 85 ? '90%' : 'Inactif'}</span>
                    <span className={`agent-health-status-dot ${selectedTurbine.health_score < 85 ? 'nominal' : 'inactive'}`} />
                  </div>
                </div>

                <div className="agent-health-card decision">
                  <div className="agent-identity">
                    <span className="agent-circle-icon">💡</span>
                    <span className="agent-title-text">Décision</span>
                  </div>
                  <div className="agent-metrics">
                    <span className="agent-pct-value">100%</span>
                    <span className="agent-health-status-dot nominal" />
                  </div>
                </div>

                <div className="agent-health-card reporting">
                  <div className="agent-identity">
                    <span className="agent-circle-icon">📄</span>
                    <span className="agent-title-text">Rapports</span>
                  </div>
                  <div className="agent-metrics">
                    <span className="agent-pct-value">100%</span>
                    <span className="agent-health-status-dot nominal" />
                  </div>
                </div>
              </div>
            </div>

            {/* 5. Interaction Agent Panel */}
            <div className="panel panel-interaction-agent">
              <span className="interaction-pct-title">{selectedTurbine.health_score}%</span>
              <span className="interaction-pct-subtitle">Santé de la turbine sélectionnée</span>
              <div className="interaction-grid-details">
                <div className="interaction-grid-col">
                  <span className="interaction-grid-label">Date d'exécution</span>
                  <span className="interaction-grid-value">
                    {latestRunResult ? new Date(latestRunResult.timestamp || Date.now()).toLocaleDateString('fr-FR') : new Date().toLocaleDateString('fr-FR')}
                  </span>
                </div>
                <div className="interaction-grid-col">
                  <span className="interaction-grid-label">Total Alertes</span>
                  <span className="interaction-grid-value" style={{ color: selectedTurbine.active_alerts_count > 0 ? '#dc3545' : undefined }}>
                    {selectedTurbine.active_alerts_count}
                  </span>
                </div>
              </div>
            </div>

            {/* 6. Interactive Graph Panel */}
            <div className="panel panel-interactive-graphs">
              <div className="graphs-header">
                <h3 className="graphs-header-title">
                  <svg viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z"/></svg>
                  Historique d'Indice de Santé ({selectedTurbineId})
                </h3>
                <select className="graphs-select" value={selectedTurbineId} onChange={(e) => setSelectedTurbineId(e.target.value)}>
                  {turbines.map(t => (
                    <option key={t.turbine_id} value={t.turbine_id}>{t.turbine_id}</option>
                  ))}
                  {turbines.length === 0 && <option value="WTG-001">WTG-001</option>}
                </select>
              </div>
              <div className="graphs-svg-wrapper">
                <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
                  {/* Grid Lines */}
                  {[10, 50, 90, 130].map((y, index) => {
                    const healthPct = [100, 66, 33, 0][index];
                    return (
                      <g key={y}>
                        <line x1={chartPadding.left} y1={y} x2={chartWidth - chartPadding.right} y2={y} className="chart-grid-line" />
                        <text x={chartPadding.left - 10} y={y + 4} textAnchor="end" className="chart-text">{healthPct}%</text>
                      </g>
                    );
                  })}
                  {/* Area fill with Gradient */}
                  <path className="chart-area" d={areaD} />
                  {/* Line path */}
                  <path className="chart-line" d={lineD} />
                  {/* Data Points */}
                  {chartPoints.map((pt, idx) => (
                    <g key={idx}>
                      <circle cx={pt.x} cy={pt.y} r="5" className="chart-dot" />
                      {/* Tooltip on hover (simplified display) */}
                      <text x={pt.x} y={pt.y - 10} textAnchor="middle" className="chart-text" style={{ fontSize: '8px', fontWeight: 'bold', fill: 'var(--pistachio-800)' }}>
                        {chartData[idx]}%
                      </text>
                    </g>
                  ))}
                  {/* X Axis Line */}
                  <line x1={chartPadding.left} y1={chartHeight - chartPadding.bottom} x2={chartWidth - chartPadding.right} y2={chartHeight - chartPadding.bottom} className="chart-axis-line" />
                  {/* X Axis Labels */}
                  {months.map((m, idx) => {
                    const x = chartPadding.left + idx * ((chartWidth - chartPadding.left - chartPadding.right) / (months.length - 1));
                    return (
                      <text key={m} x={x} y={chartHeight - 8} textAnchor="middle" className="chart-text">{m}</text>
                    );
                  })}
                </svg>
              </div>
            </div>

          </div>
        )}

        {/* ═══════════════════════════════════════════
            TAB 2: SIMULATION & FLEET VIEW
            ═══════════════════════════════════════════ */}
        {activeTab === 'simulation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
            
            {/* Turbine fleet selector */}
            <div className="panel" style={{ borderTop: '4px solid var(--pistachio-600)' }}>
              <h2 className="panel-heading">Surveillance et Sélection de la Flotte</h2>
              <div className="turbine-cards-list">
                {turbines.map(t => {
                  const isSelected = t.turbine_id === selectedTurbineId;
                  const fillPercent = t.health_score;
                  const fillBg = healthColor(fillPercent);
                  
                  return (
                    <div
                      key={t.turbine_id}
                      className={`turbine-visual-card ${isSelected ? 'selected' : ''} ${t.status === 'offline' ? 'offline' : ''} ${t.status === 'curtailed' ? 'curtailed' : ''}`}
                      onClick={() => setSelectedTurbineId(t.turbine_id)}
                    >
                      <div className="turbine-card-title-row">
                        <span className="turbine-card-title">{t.turbine_id}</span>
                        <span className={`turbine-card-status-badge ${t.status}`}>{t.status}</span>
                      </div>

                      {/* Turbine SVG */}
                      <div className="turbine-card-svg-container">
                        {renderTurbineSvg(t.status)}
                      </div>

                      <div className="turbine-card-metrics">
                        <span>Santé: {t.health_score}%</span>
                        <span>Alertes: {t.active_alerts_count}</span>
                      </div>
                      <div className="turbine-card-health-gauge">
                        <div className="turbine-card-health-gauge-fill" style={{ width: `${fillPercent}%`, backgroundColor: fillBg }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Sensor Injection Console */}
            <div className="panel simulator-panel">
              <h2 className="panel-heading">Console d'Injection de Capteurs ({selectedTurbineId})</h2>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '-0.75rem', marginBottom: '1.25rem' }}>
                Ajustez les curseurs physiques pour simuler des anomalies et observer les diagnostics des agents.
              </p>
              
              <div className="moroccan-divider" />

              {/* Quick Presets Row */}
              <div className="simulator-presets-row">
                <button className="simulator-preset-btn" onClick={() => applyPreset('nominal')}>Opérations Normales</button>
                <button className="simulator-preset-btn warn" onClick={() => applyPreset('vibration')}>Vibration Élevée</button>
                <button className="simulator-preset-btn danger" onClick={() => applyPreset('overheat')}>Surchauffe Génératrice</button>
                <button className="simulator-preset-btn danger" onClick={() => applyPreset('storm')}>Tempête (Rafales)</button>
                <button className="simulator-preset-btn" onClick={() => applyPreset('offline')}>Arrêt Hors Ligne</button>
              </div>

              {/* Sliders Grid */}
              <div className="simulator-sliders-grid">
                {/* Wind Speed */}
                <div className="simulator-slider-wrapper">
                  <div className="simulator-slider-headers">
                    <span>Vitesse du Vent</span>
                    <span>{simParams.wind_speed} m/s</span>
                  </div>
                  <input type="range" className="simulator-slider" min="0" max="35" step="0.5"
                    value={simParams.wind_speed}
                    onChange={(e) => setSimParams({ ...simParams, wind_speed: parseFloat(e.target.value) })}
                  />
                </div>

                {/* Rotor Speed */}
                <div className="simulator-slider-wrapper">
                  <div className="simulator-slider-headers">
                    <span>Vitesse du Rotor</span>
                    <span>{simParams.rotor_speed} RPM</span>
                  </div>
                  <input type="range" className="simulator-slider" min="0" max="25" step="0.5"
                    value={simParams.rotor_speed}
                    onChange={(e) => setSimParams({ ...simParams, rotor_speed: parseFloat(e.target.value) })}
                  />
                </div>

                {/* Blade Temp */}
                <div className="simulator-slider-wrapper">
                  <div className="simulator-slider-headers">
                    <span>Température des Pales</span>
                    <span>{simParams.blade_temp} °C</span>
                  </div>
                  <input type="range" className="simulator-slider" min="10" max="80" step="0.5"
                    value={simParams.blade_temp}
                    onChange={(e) => setSimParams({ ...simParams, blade_temp: parseFloat(e.target.value) })}
                  />
                </div>

                {/* Generator Temp */}
                <div className="simulator-slider-wrapper">
                  <div className="simulator-slider-headers">
                    <span>Température Génératrice</span>
                    <span>{simParams.generator_temp} °C</span>
                  </div>
                  <input type="range" className="simulator-slider" min="20" max="105" step="0.5"
                    value={simParams.generator_temp}
                    onChange={(e) => setSimParams({ ...simParams, generator_temp: parseFloat(e.target.value) })}
                  />
                </div>

                {/* Vibration */}
                <div className="simulator-slider-wrapper">
                  <div className="simulator-slider-headers">
                    <span>Vibration</span>
                    <span>{simParams.vibration} mm/s</span>
                  </div>
                  <input type="range" className="simulator-slider" min="0" max="0.5" step="0.01"
                    value={simParams.vibration}
                    onChange={(e) => setSimParams({ ...simParams, vibration: parseFloat(e.target.value) })}
                  />
                </div>

                {/* Power Output */}
                <div className="simulator-slider-wrapper">
                  <div className="simulator-slider-headers">
                    <span>Puissance Produite</span>
                    <span>{simParams.power_output} MW</span>
                  </div>
                  <input type="range" className="simulator-slider" min="0" max="3.5" step="0.1"
                    value={simParams.power_output}
                    onChange={(e) => setSimParams({ ...simParams, power_output: parseFloat(e.target.value) })}
                  />
                </div>
              </div>

              {/* Simulator Footer */}
              <div className="simulator-panel-footer">
                <div className="simulator-footer-left">
                  <span className="simulator-footer-label">État du Réseau :</span>
                  <select
                    className="simulator-select"
                    value={simParams.status}
                    onChange={(e) => setSimParams({ ...simParams, status: e.target.value })}
                  >
                    <option value="active">Actif</option>
                    <option value="offline">Hors Ligne</option>
                    <option value="maintenance">Maintenance</option>
                    <option value="curtailed">Réduit</option>
                  </select>
                </div>
                <button className="btn btn-primary" onClick={runIngest} disabled={isProcessing}>
                  {isProcessing ? 'Traitement en cours...' : 'Envoyer la Télémétrie au Superviseur'}
                </button>
              </div>

            </div>

          </div>
        )}

        {/* ═══════════════════════════════════════════
            TAB 3: REPORTS AND MAILBOX VIEW
            ═══════════════════════════════════════════ */}
        {activeTab === 'reports' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            
            {/* Multi-Agent Run Log Timeline */}
            <div className="panel" style={{ borderTop: '4px solid var(--pistachio-500)' }}>
              <h2 className="panel-heading">Trace d'Exécution Multi-Agent</h2>

              {!latestRunResult && !isProcessing && (
                <div className="empty-state">
                  <p>Aucune trace d'exécution active.</p>
                  <p>Déclenchez l'ingestion de télémétrie dans l'onglet Simulation pour observer la boucle de décision.</p>
                </div>
              )}

              {isProcessing && (
                <div style={{ textAlign: 'center', padding: '2.5rem 0', color: '#4caf50' }}>
                  <div className="spinner" />
                  <p style={{ fontWeight: 600, margin: 0 }}>L'orchestrateur superviseur exécute le graphe LangGraph...</p>
                </div>
              )}

              {latestRunResult && (
                <div>
                  <div className="trace-correlation-row">
                    <span>ID de Corrélation : <b>{latestRunResult.correlation_id}</b></span>
                    <span>Santé Finale : <b style={{ color: healthColor(latestRunResult.health_score) }}>{latestRunResult.health_score}%</b></span>
                  </div>

                  <div className="trace-log-timeline">
                    {latestRunResult.logs.map((log, index) => {
                      const meta = getAgentMeta(log);
                      return (
                        <div key={index} className="trace-timeline-step completed">
                          <div className="trace-timeline-dot">{index + 1}</div>
                          <div className="trace-timeline-body">
                            <div className="trace-timeline-agent" style={{ color: meta.color }}>{meta.name}</div>
                            <div className="trace-timeline-log">{log}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Recommendations */}
                  <div className="trace-reco-container">
                    <h4 className="trace-reco-title">Synthèse et Actions Préconisées</h4>

                    {latestRunResult.diagnosis && (
                      <div className="trace-reco-diagnosis">
                        <b>Cause Racine :</b> {latestRunResult.diagnosis.cause} (Confiance : {(latestRunResult.diagnosis.confidence * 100).toFixed(0)}%)
                      </div>
                    )}

                    {latestRunResult.decisions.map((dec, i) => (
                      <div key={i} className="trace-reco-item">
                        <div>
                          <div className="trace-reco-action-title">{dec.action}</div>
                          <div className="trace-reco-action-desc">{dec.description}</div>
                        </div>
                        <span className={`trace-reco-badge-pill ${dec.risk_level}`}>
                          {dec.risk_level === 'high' ? 'Risque Élevé' : (dec.risk_level === 'medium' ? 'Risque Moyen' : 'Risque Faible')}
                        </span>
                      </div>
                    ))}

                    {latestRunResult.pdf_path && (
                      <div className="trace-pdf-link-container">
                        <a href={`${API_BASE}/api/reports/${latestRunResult.pdf_path}`} target="_blank" rel="noreferrer" className="trace-pdf-btn-link">
                          📄 Télécharger le Rapport PDF Officiel
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Email Inbox */}
            <div className="panel" style={{ borderTop: '4px solid var(--moroccan-gold)' }}>
              <h2 className="panel-heading">Boîte de Réception — Rapports Automatiques</h2>

              {emails.length === 0 ? (
                <div className="empty-state">
                  <p>Boîte de réception vide.</p>
                  <p>Les e-mails de notification officiels générés par l'agent de reporting s'afficheront ici.</p>
                </div>
              ) : (
                <div className="mailbox-list-wrapper">
                  {emails.map(email => (
                    <div key={email.id} className="mailbox-card">
                      <div className="mailbox-card-header">
                        <span>De: {email.sender}</span>
                        <span>{new Date(email.timestamp).toLocaleTimeString('fr-FR')}</span>
                      </div>
                      <div className="mailbox-card-subject">{email.subject}</div>
                      <div className="mailbox-card-to">À: {email.recipient}</div>
                      <div className="mailbox-card-body">{email.body}</div>

                      {email.pdf_filename && (
                        <div className="mailbox-card-attachment">
                          <span className="mailbox-card-attachment-name">📎 {email.pdf_filename}</span>
                          <a href={`${API_BASE}/api/reports/${email.pdf_filename}`} target="_blank" rel="noreferrer"
                            className="btn btn-secondary" style={{ fontSize: '0.68rem', padding: '0.2rem 0.5rem' }}>
                            Voir le PDF
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

      </main>
    </div>
  );
}

export default App;
