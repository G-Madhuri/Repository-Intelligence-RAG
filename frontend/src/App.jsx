import React, { useState, useEffect } from 'react';
import { Cpu, ArrowLeft, AlertCircle, CheckCircle, Shield, User, Clock, LogOut, X } from 'lucide-react';
import { createClient } from '@supabase/supabase-js';
import InputForm from './components/InputForm';
import RepoTree from './components/RepoTree';
import Dashboard from './components/Dashboard';
import AuthModal from './components/AuthModal';
import { apiUrl } from './api';

const SUPABASE_URL = 'https://sjjnisutudwpijfymmgx.supabase.co';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqam5pc3V0dWR3cGlqZnltbWd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxNzkyMjEsImV4cCI6MjEwNTc1NTIyMX0.7lZvYXBs1d7k8p2P9fMHKHdrkqExnY7jAMLB-NxcypI';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const LOADING_STEPS = [
  { title: 'Supabase Auth Check',  desc: 'Verifying user identity and Bearer JWT token...' },
  { title: 'Workspace Isolation',  desc: 'Cloning repository into isolated sandbox...' },
  { title: 'Static Profiling',     desc: 'Scanning files, parsing package manifests...' },
  { title: 'Gemini Reasoning',     desc: 'Analyzing codebase with Gemini 2.5 Flash...' },
  { title: 'Pinecone RAG Indexing',desc: 'Building semantic vector index with llama-text-embed-v2...' },
];

export default function App() {
  const [appState, setAppState] = useState('idle');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [session, setSession] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    }).catch(() => {});

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Clear authentication error banner automatically upon successful login
  useEffect(() => {
    if (session?.access_token) {
      setError(prevError => {
        if (prevError && (prevError.includes('Authentication required') || prevError.includes('Please sign in'))) {
          setAppState('idle');
          return null;
        }
        return prevError;
      });
    }
  }, [session]);

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
    if (!session || !session.access_token) {
      setIsAuthModalOpen(true);
      setError("Authentication required: Please sign in with Supabase to analyze repositories.");
      setAppState('error');
      return;
    }

    setAppState('loading');
    setError(null);
    setAnalysisResult(null);

    const headers = {
      'Authorization': `Bearer ${session.access_token}`
    };

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
        setAnalysisResult(resData);
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

  const userEmail = session?.user?.email;

  return (
    <div className="app-container">

      {/* ── Top Header ── */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">
            <Cpu size={20} color="#fff" />
          </div>
          <div>
            <div className="brand-title">Repository Intelligence</div>
            <div className="brand-subtitle">Pinecone RAG (llama-text-embed-v2) + Supabase Auth</div>
          </div>
        </div>

        {/* Top Right Real Supabase Auth Section */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <button 
            onClick={() => setIsAuthModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.45rem 0.85rem',
              borderRadius: '20px',
              background: session 
                ? 'rgba(16, 185, 129, 0.12)' 
                : 'rgba(239, 68, 68, 0.12)',
              border: session 
                ? '1px solid rgba(16, 185, 129, 0.35)' 
                : '1px solid rgba(239, 68, 68, 0.35)',
              color: session ? '#34d399' : '#fca5a5',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 600,
              transition: 'all 0.2s ease'
            }}
          >
            {session ? (
              <>
                <Shield size={14} color="#34d399" />
                <span>{userEmail}</span>
                <span style={{ 
                  background: 'rgba(16, 185, 129, 0.2)', 
                  color: '#6ee7b7', 
                  padding: '0.15rem 0.45rem', 
                  borderRadius: '10px', 
                  fontSize: '0.7rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.2rem'
                }}>
                  <Clock size={10} /> 1h TTL Active
                </span>
              </>
            ) : (
              <>
                <User size={14} />
                <span>Sign In with Supabase</span>
              </>
            )}
          </button>

          {session && (
            <button 
              onClick={() => supabase.auth.signOut()} 
              className="btn-secondary" 
              title="Sign Out"
              style={{ padding: '0.45rem', borderRadius: '50%' }}
            >
              <LogOut size={14} />
            </button>
          )}

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

      {/* ── Main Content ── */}
      <main className="main-content">

        {/* IDLE */}
        {appState === 'idle' && (
          <InputForm onSubmit={handleStartAnalysis} loading={false} />
        )}

        {/* ERROR */}
        {appState === 'error' && (
          <div style={{ maxWidth: '680px', width: '100%', margin: '0 auto' }}>
            <div className="error-panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                <AlertCircle size={20} style={{ flexShrink: 0 }} />
                <div>
                  <div className="error-title">Authentication / Analysis Error</div>
                  <p style={{ fontSize: '0.88rem', marginTop: '0.25rem' }}>{error}</p>
                </div>
              </div>
              <button
                onClick={handleReset}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'inherit',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: '4px',
                  opacity: 0.7,
                  display: 'flex',
                  alignItems: 'center',
                  marginLeft: '0.75rem'
                }}
                title="Dismiss Error"
              >
                <X size={18} />
              </button>
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
                Scanning codebase under authenticated Supabase identity ({userEmail}).
                Repository RAG index set to 1-Hour TTL.
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

      {/* Auth Modal */}
      <AuthModal 
        isOpen={isAuthModalOpen} 
        onClose={() => setIsAuthModalOpen(false)} 
        supabase={supabase}
        currentUser={session?.user}
      />
    </div>
  );
}
