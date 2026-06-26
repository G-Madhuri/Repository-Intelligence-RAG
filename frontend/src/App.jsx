import React, { useState, useEffect } from 'react';
import { Cpu, ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react';
import InputForm from './components/InputForm';
import RepoTree from './components/RepoTree';
import Dashboard from './components/Dashboard';
import { apiUrl } from './api';

const LOADING_STEPS = [
  { title: 'Access Verification',  desc: 'Checking GitHub repository accessibility...' },
  { title: 'Workspace Isolation',  desc: 'Cloning repository into isolated sandbox...' },
  { title: 'Static Profiling',     desc: 'Scanning files, parsing package manifests...' },
  { title: 'Gemini Reasoning',     desc: 'Analyzing codebase with Gemini 2.5 Flash...' },
  { title: 'Knowledge Indexing',   desc: 'Building semantic vector index (ChromaDB)...' },
];

export default function App() {
  const [appState, setAppState] = useState('idle'); // idle | loading | success | error
  const [analysisResult, setAnalysisResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    let interval;
    if (appState === 'loading') {
      setCurrentStep(0);
      interval = setInterval(() => {
        setCurrentStep(prev => (prev < LOADING_STEPS.length - 2 ? prev + 1 : prev));
      }, 3800);
    }
    return () => clearInterval(interval);
  }, [appState]);

  const handleStartAnalysis = async (formData) => {
    setAppState('loading');
    setError(null);
    setAnalysisResult(null);

    // API key is now server-side from .env — only send if user explicitly provided one
    const headers = {};
    if (formData.apiKey) headers['x-gemini-key'] = formData.apiKey;

    try {
      let response;
      if (formData.type === 'url') {
        setCurrentStep(0);
        response = await fetch(apiUrl('/api/analyze-url'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...headers },
          body: JSON.stringify({ url: formData.url, token: formData.token || null }),
        });
      } else {
        setCurrentStep(1);
        const fd = new FormData();
        fd.append('file', formData.file);
        response = await fetch(apiUrl('/api/analyze-zip'), { method: 'POST', headers, body: fd });
      }

      const resData = await response.json();
      if (!response.ok) throw new Error(resData.detail || 'Analysis failed.');

      setCurrentStep(4);
      setTimeout(() => {
        setAnalysisResult({ ...resData, apiKey: formData.apiKey || null });
        setAppState('success');
      }, 700);
    } catch (e) {
      setError(e.message);
      setAppState('error');
    }
  };

  const handleReset = () => {
    setAppState('idle');
    setAnalysisResult(null);
    setError(null);
  };

  return (
    <div className="app-container">

      {/* ── Header ── */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">
            <Cpu size={20} color="#fff" />
          </div>
          <div>
            <div className="brand-title">Repository Intelligence</div>
            <div className="brand-subtitle">AI-Powered Code Analysis Platform</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {appState === 'success' && (
            <>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {analysisResult?.project_name}
              </span>
              <button className="btn-secondary" onClick={handleReset}>
                <ArrowLeft size={14} /> New Analysis
              </button>
            </>
          )}
        </div>
      </header>

      {/* ── Main ── */}
      <main className="main-content">

        {/* IDLE */}
        {appState === 'idle' && (
          <InputForm onSubmit={handleStartAnalysis} loading={false} />
        )}

        {/* ERROR */}
        {appState === 'error' && (
          <div style={{ maxWidth: '680px', width: '100%', margin: '0 auto' }}>
            <div className="error-panel">
              <AlertCircle size={20} style={{ flexShrink: 0 }} />
              <div>
                <div className="error-title">Analysis Failed</div>
                <p style={{ fontSize: '0.88rem', marginTop: '0.25rem' }}>{error}</p>
              </div>
            </div>
            <InputForm onSubmit={handleStartAnalysis} loading={false} />
          </div>
        )}

        {/* LOADING */}
        {appState === 'loading' && (
          <div className="glass-panel progress-panel">
            <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
              <div className="spinner" />
              <h2 className="section-title" style={{ marginBottom: '0.5rem' }}>
                Generating Intelligence Report
              </h2>
              <p className="section-desc" style={{ margin: 0 }}>
                Scanning codebase, extracting semantics, and building your knowledge base.
                This may take up to a minute for large repositories.
              </p>
            </div>

            <div className="progress-steps">
              {LOADING_STEPS.map((step, idx) => {
                const state = idx < currentStep ? 'completed' : idx === currentStep ? 'active' : 'pending';
                return (
                  <div key={idx} className={`progress-step ${state}`}>
                    <div className={`step-icon ${state}`}>
                      {state === 'completed' ? <CheckCircle size={14} /> : idx + 1}
                    </div>
                    <div>
                      <div style={{
                        fontWeight: 600,
                        fontSize: '0.88rem',
                        color: state === 'active' ? 'var(--text-primary)' : 'var(--text-secondary)'
                      }}>
                        {step.title}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {step.desc}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* SUCCESS */}
        {appState === 'success' && analysisResult && (
          <div className="dashboard-grid">
            <aside className="glass-panel sidebar-panel">
              <RepoTree
                tree={analysisResult.tree}
                title={analysisResult.project_name?.split('/').pop()}
              />
            </aside>
            <section>
              <Dashboard analysisResult={analysisResult} />
            </section>
          </div>
        )}

      </main>
    </div>
  );
}
