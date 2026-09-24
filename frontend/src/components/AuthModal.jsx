import React, { useState } from 'react';
import { Shield, CheckCircle, Clock, X, Lock, Mail, AlertTriangle } from 'lucide-react';

export default function AuthModal({ isOpen, onClose, supabase, currentUser }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [authSuccessMsg, setAuthSuccessMsg] = useState(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    setAuthError(null);
    setAuthSuccessMsg(null);
    setLoading(true);

    try {
      if (isSignUp) {
        // Attempt Supabase Sign Up
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) {
          if (error.message?.includes('rate limit')) {
            // If rate limited, attempt sign-in in case account exists
            const signInRes = await supabase.auth.signInWithPassword({ email, password });
            if (signInRes.data?.session) {
              onClose();
              return;
            }
            throw new Error("Supabase rate limit reached. Your account is created! Please switch to 'Sign In' and enter your password.");
          }
          throw error;
        }

        if (data?.session) {
          onClose();
        } else {
          setAuthSuccessMsg("Account created! Click 'Sign In' to log in.");
          setIsSignUp(false);
        }
      } else {
        // Supabase Sign In
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) {
          if (error.message?.includes('Email not confirmed')) {
            throw new Error("Email was auto-confirmed in Supabase database! Click 'Sign In' again.");
          }
          if (error.message?.includes('Invalid login credentials')) {
            throw new Error("Invalid email or password. If you haven't created an account yet, click 'Create Account' above.");
          }
          throw error;
        }
        if (data?.session) {
          onClose();
        }
      }
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      animation: 'fadeIn 0.2s ease'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '440px',
        padding: '2rem',
        borderRadius: 'var(--radius-lg)',
        background: '#FFFFFF',
        border: '1px solid var(--border-color)',
        boxShadow: 'var(--shadow-xl)',
        position: 'relative',
        color: 'var(--text-primary)'
      }} onClick={e => e.stopPropagation()}>
        
        {/* Close button */}
        <button onClick={onClose} style={{
          position: 'absolute',
          top: '1.25rem',
          right: '1.25rem',
          background: 'none',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          padding: '4px',
          borderRadius: 'var(--radius-sm)'
        }}>
          <X size={18} />
        </button>

        {/* Modal Header */}
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, var(--accent-teal) 0%, var(--accent-indigo) 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem auto',
            boxShadow: '0 4px 12px rgba(46, 158, 158, 0.25)'
          }}>
            <Shield size={24} color="#fff" />
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>
            {currentUser ? 'Supabase Account' : (isSignUp ? 'Create Supabase Account' : 'Sign In to Platform')}
          </h2>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '0.35rem', lineHeight: 1.4 }}>
            {currentUser 
              ? 'Your repository RAG vector memory is active with a 1-Hour TTL.' 
              : 'Authenticated users receive 1-Hour RAG memory persistence & Supabase database tracking.'}
          </p>
        </div>

        {/* Error Alert */}
        {authError && (
          <div style={{
            padding: '0.75rem 1rem',
            borderRadius: 'var(--radius-md)',
            background: 'var(--status-error-bg)',
            border: '1px solid #FECDD3',
            color: 'var(--status-error-txt)',
            fontSize: '0.82rem',
            marginBottom: '1.25rem',
            lineHeight: 1.4,
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.5rem'
          }}>
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{authError}</div>
          </div>
        )}

        {/* Success Alert */}
        {authSuccessMsg && (
          <div style={{
            padding: '0.75rem 1rem',
            borderRadius: 'var(--radius-md)',
            background: 'var(--status-success-bg)',
            border: '1px solid #A7F3D0',
            color: 'var(--status-success-txt)',
            fontSize: '0.82rem',
            marginBottom: '1.25rem',
            lineHeight: 1.4,
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.5rem'
          }}>
            <CheckCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{authSuccessMsg}</div>
          </div>
        )}

        {currentUser ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{
              padding: '1.25rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-muted)',
              border: '1px solid var(--border-color)',
              marginBottom: '1.5rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', fontWeight: 600, color: 'var(--accent-teal-dk)', fontSize: '0.92rem' }}>
                <CheckCircle size={17} /> Authenticated User
              </div>
              <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', marginTop: '0.35rem', fontWeight: 500 }}>
                {currentUser.email}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem', fontSize: '0.78rem', color: 'var(--accent-green)', marginTop: '0.65rem', fontWeight: 600 }}>
                <Clock size={14} /> 1-Hour RAG Vector TTL Active
              </div>
            </div>

            <button 
              className="btn-secondary" 
              style={{ width: '100%', padding: '0.75rem' }}
              onClick={handleSignOut}
            >
              Sign Out
            </button>
          </div>
        ) : (
          <div>
            {/* Pill Tabs for Sign In vs Create Account */}
            <div style={{
              display: 'flex',
              background: '#F1F5F9',
              borderRadius: 'var(--radius-md)',
              padding: '4px',
              marginBottom: '1.5rem',
              border: '1px solid var(--border-color)'
            }}>
              <button
                type="button"
                onClick={() => { setIsSignUp(false); setAuthError(null); setAuthSuccessMsg(null); }}
                style={{
                  flex: 1,
                  padding: '0.55rem',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.18s ease',
                  background: !isSignUp ? '#FFFFFF' : 'transparent',
                  color: !isSignUp ? 'var(--accent-teal-dk)' : 'var(--text-muted)',
                  boxShadow: !isSignUp ? 'var(--shadow-sm)' : 'none'
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setIsSignUp(true); setAuthError(null); setAuthSuccessMsg(null); }}
                style={{
                  flex: 1,
                  padding: '0.55rem',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.18s ease',
                  background: isSignUp ? '#FFFFFF' : 'transparent',
                  color: isSignUp ? 'var(--accent-teal-dk)' : 'var(--text-muted)',
                  boxShadow: isSignUp ? 'var(--shadow-sm)' : 'none'
                }}
              >
                Create Account
              </button>
            </div>

            <form onSubmit={handleEmailAuth}>
              <div style={{ marginBottom: '1.15rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  Email Address
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="email"
                    placeholder="developer@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem 0.75rem 2.4rem',
                      borderRadius: 'var(--radius-md)',
                      background: '#FFFFFF',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-primary)',
                      fontSize: '0.9rem',
                      outline: 'none',
                      transition: 'border-color 0.18s ease'
                    }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  Password
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem 0.75rem 2.4rem',
                      borderRadius: 'var(--radius-md)',
                      background: '#FFFFFF',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-primary)',
                      fontSize: '0.9rem',
                      outline: 'none',
                      transition: 'border-color 0.18s ease'
                    }}
                  />
                </div>
              </div>

              <button 
                type="submit" 
                className="btn-primary" 
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '0.8rem',
                  fontSize: '0.92rem',
                  fontWeight: 600,
                  marginBottom: '0.75rem',
                  background: 'linear-gradient(135deg, var(--accent-teal) 0%, var(--accent-teal-dk) 100%)',
                  borderRadius: 'var(--radius-md)',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: 'pointer',
                  boxShadow: '0 2px 6px rgba(46, 158, 158, 0.3)'
                }}
              >
                {loading ? 'Processing Authentication...' : (isSignUp ? 'Create Supabase Account' : 'Sign In')}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
