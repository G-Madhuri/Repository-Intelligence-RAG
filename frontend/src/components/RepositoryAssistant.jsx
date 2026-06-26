import React, { useState, useRef, useEffect } from 'react';
import { marked } from 'marked';
import {
  Send, Bot, User, Shield, Layers, Terminal, Play,
  HelpCircle, Cpu, Award, Activity, ChevronRight
} from 'lucide-react';
import { apiUrl } from '../api';

const SUGGESTED = [
  'How does authentication work?',
  'What is the architecture pattern?',
  'Which API endpoints exist?',
  'What are the main dependencies?',
  'Where should I start reading code?',
];

const getAgentIcon = (name) => {
  const map = {
    PlannerAgent:      <Cpu size={13} style={{ color: 'var(--accent-teal)' }} />,
    ArchitectureAgent: <Layers size={13} style={{ color: 'var(--accent-purple)' }} />,
    SecurityAgent:     <Shield size={13} style={{ color: 'var(--accent-rose)' }} />,
    ApiAgent:          <Terminal size={13} style={{ color: 'var(--accent-indigo)' }} />,
    DependencyAgent:   <Play size={13} style={{ color: 'var(--accent-amber)' }} />,
    QualityAgent:      <Activity size={13} style={{ color: 'var(--accent-green)' }} />,
    OnboardingAgent:   <HelpCircle size={13} style={{ color: 'var(--accent-teal)' }} />,
  };
  return map[name] || <Cpu size={13} />;
};

const getAgentLabel = (name) => name.replace('Agent', ' Agent');

const renderMarkdown = (text) => {
  try { return { __html: marked.parse(text || '') }; }
  catch (e) { return { __html: text || '' }; }
};

export default function RepositoryAssistant({ repo_id, apiKey }) {
  const [messages, setMessages] = useState([{
    id: 'welcome',
    role: 'assistant',
    content: 'Hello! Ask me anything about this codebase — architecture, security, APIs, dependencies, or how to get started.',
    timeline: null, planner_decision: null, confidence: null,
    total_time_ms: null, references: [], retrieved_context: []
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [selectedId, setSelectedId] = useState('welcome');
  const chatEndRef = useRef(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    setLoading(true);
    const userMsg = { id: `u-${Date.now()}`, role: 'user', content: text.trim() };
    setMessages(prev => [...prev, userMsg]);
    setSelectedId(userMsg.id);
    setInput('');

    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['x-gemini-key'] = apiKey;

    try {
      const res = await fetch(apiUrl('/api/chat'), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          repo_id,
          question: text.trim(),
          session_id: sessionId,
        }),
      });
      const raw = await res.text();
      let data;
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        throw new Error(raw || `Server error (${res.status})`);
      }
      if (!res.ok) throw new Error(data.detail || 'Agent orchestration failed.');

      if (data.session_id) setSessionId(data.session_id);

      const assistMsg = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: data.answer || data.summary || (data.agent_contributions || []).join('\n\n') || 'No answer returned from agent.',
        summary: data.summary,
        agents_used: data.agents_used,
        confidence: data.confidence,
        references: data.references || [],
        agent_contributions: data.agent_contributions,
        planner_decision: data.planner_decision,
        timeline: data.timeline,
        total_time_ms: data.total_time_ms,
        retrieved_context: data.retrieved_context || [],
        rag_latency_ms: data.rag_latency_ms,
        session_id: data.session_id,
      };
      setMessages(prev => [...prev, assistMsg]);
      setSelectedId(assistMsg.id);
    } catch (err) {
      const errMsg = { id: `e-${Date.now()}`, role: 'assistant', content: `**Error:** ${err.message}`, isError: true };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => { e.preventDefault(); sendMessage(input); };

  const activeMsg = messages.find(m => m.id === selectedId && m.role === 'assistant')
    || [...messages].reverse().find(m => m.role === 'assistant' && !m.isError)
    || messages[0];

  const confLevel = (c) => c >= 0.75 ? 'high' : c >= 0.5 ? 'medium' : 'low';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.25rem', alignItems: 'start' }}>

      {/* ── Chat Column ── */}
      <div className="chat-container">
        <div className="chat-header">
          <div className="chat-header-title">
            <Bot size={16} style={{ color: 'var(--accent-teal)' }} />
            AI Repository Assistant
          </div>
          <span style={{
            fontSize: '0.7rem', background: 'var(--status-success-bg)',
            color: 'var(--status-success-txt)', border: '1px solid #A7F3D0',
            borderRadius: 'var(--radius-full)', padding: '0.15rem 0.6rem', fontWeight: 600
          }}>
            Multi-Agent Online
          </span>
        </div>

        <div className="chat-messages">
          {/* Suggested questions — shown only when just the welcome message exists */}
          {messages.length === 1 && (
            <div className="chat-welcome">
              <div className="chat-welcome-icon">🤖</div>
              <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                {messages[0].content}
              </p>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                Try one of these questions:
              </p>
              <div className="suggested-questions">
                {SUGGESTED.map(q => (
                  <button key={q} className="suggested-q-btn" onClick={() => sendMessage(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.slice(1).map(msg => (
            <div
              key={msg.id}
              className={`chat-message ${msg.role}`}
              onClick={() => msg.role === 'assistant' && setSelectedId(msg.id)}
              style={{ cursor: msg.role === 'assistant' ? 'pointer' : 'default' }}
            >
              <div className="chat-bubble">
                {msg.role === 'assistant' ? (
                  <div
                    className="markdown-body"
                    dangerouslySetInnerHTML={renderMarkdown(msg.content)}
                    style={{ fontSize: '0.9rem', lineHeight: 1.65 }}
                  />
                ) : (
                  <span>{msg.content}</span>
                )}
              </div>

              <div className="chat-meta" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                {msg.role === 'assistant' && msg.confidence != null && (
                  <span className={`confidence-badge ${confLevel(msg.confidence)}`}>
                    {Math.round(msg.confidence * 100)}% confidence
                  </span>
                )}
                {msg.role === 'assistant' && msg.total_time_ms && (
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    {msg.total_time_ms}ms
                  </span>
                )}
                {msg.role === 'assistant' && msg.agents_used?.length > 0 && (
                  <div className="rag-context-strip">
                    {msg.agents_used.map(a => (
                      <span key={a} className="agent-tag">{getAgentIcon(a)} {getAgentLabel(a)}</span>
                    ))}
                  </div>
                )}
                {msg.role === 'assistant' && msg.retrieved_context?.length > 0 && (
                  <span className="rag-badge">
                    {msg.retrieved_context.length} RAG chunks
                  </span>
                )}
              </div>

              {/* References */}
              {msg.references?.length > 0 && (
                <div style={{
                  marginTop: '0.5rem',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '0.35rem',
                }}>
                  {msg.references.map((r, i) => (
                    <span key={i} className="src-path-tag">{r}</span>
                  ))}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant">
              <div className="chat-bubble" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Bot size={16} className="spin-slow" style={{ color: 'var(--accent-teal)', flexShrink: 0 }} />
                <span style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                  Orchestrating agents...
                </span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="chat-input-area">
          <form onSubmit={handleSubmit} className="chat-input-row">
            <textarea
              className="chat-input"
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
              placeholder="Ask about architecture, security, APIs, or onboarding..."
              disabled={loading}
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={loading || !input.trim()}
              id="chat-send-button"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>

      {/* ── Observability Panel ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <h4 style={{
            fontFamily: 'var(--font-display)', fontSize: '0.88rem', fontWeight: 700,
            color: 'var(--text-primary)', marginBottom: '0.75rem',
            display: 'flex', alignItems: 'center', gap: '0.4rem'
          }}>
            <Activity size={14} style={{ color: 'var(--accent-teal)' }} />
            Orchestration Observability
          </h4>

          {activeMsg && activeMsg.id !== 'welcome' && !activeMsg.isError ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

              {/* Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div style={{ background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)', padding: '0.65rem' }}>
                  <div className="msc-label">Time</div>
                  <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--accent-teal-dk)' }}>
                    {activeMsg.total_time_ms}ms
                  </div>
                </div>
                <div style={{ background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)', padding: '0.65rem' }}>
                  <div className="msc-label">Confidence</div>
                  <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--accent-green)' }}>
                    {activeMsg.confidence != null ? `${Math.round(activeMsg.confidence * 100)}%` : '—'}
                  </div>
                </div>
              </div>

              {/* RAG context */}
              {activeMsg.retrieved_context?.length > 0 && (
                <div style={{ background: 'var(--status-info-bg)', border: '1px solid #BFDBFE', borderRadius: 'var(--radius-md)', padding: '0.65rem' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--status-info-txt)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.4rem' }}>
                    RAG Context ({activeMsg.retrieved_context.length} chunks)
                  </div>
                  {activeMsg.retrieved_context.slice(0, 3).map((c, i) => (
                    <div key={i} style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '150px' }}>
                        {c.metadata?.category || 'chunk'}
                      </span>
                      <span style={{ color: 'var(--accent-teal-dk)', fontWeight: 600 }}>
                        {Math.round(c.similarity * 100)}%
                      </span>
                    </div>
                  ))}
                  {activeMsg.rag_latency_ms && (
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      Retrieved in {activeMsg.rag_latency_ms}ms
                    </div>
                  )}
                </div>
              )}

              {/* Planner Decision */}
              {activeMsg.planner_decision && (
                <div style={{ background: 'var(--bg-muted)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Cpu size={11} /> Planner Decision
                  </div>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '0.5rem' }}>
                    {activeMsg.planner_decision.reasoning}
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                    {activeMsg.planner_decision.execution_order?.flat().map(a => (
                      <span key={a} style={{
                        display: 'inline-flex', alignItems: 'center', gap: '0.2rem',
                        fontSize: '0.7rem', padding: '0.15rem 0.45rem',
                        background: '#fff', border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-full)', color: 'var(--text-secondary)'
                      }}>
                        {getAgentIcon(a)} {getAgentLabel(a)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Agent Timeline */}
              {activeMsg.timeline?.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
                    Agent Timeline
                  </div>
                  {activeMsg.timeline.map((step, i) => (
                    <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                      <div style={{
                        width: 6, height: 6, borderRadius: '50%', flexShrink: 0, marginTop: 6,
                        background: (step.status === 'completed' || step.status === 'success') ? 'var(--accent-green)' : step.status === 'error' ? 'var(--accent-rose)' : 'var(--accent-teal)',
                      }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            {getAgentIcon(step.agent)} {getAgentLabel(step.agent)}
                          </span>
                          <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{step.execution_time_ms}ms</span>
                        </div>
                        {step.confidence != null && step.agent !== 'PlannerAgent' && (
                          <div style={{ marginTop: '0.2rem', height: 3, background: 'var(--bg-card)', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{ width: `${step.confidence * 100}%`, height: '100%', background: 'var(--accent-green)', borderRadius: 2 }} />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Contributions */}
              {activeMsg.agent_contributions?.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Award size={11} /> Contributions
                  </div>
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                    {activeMsg.agent_contributions.map((c, i) => (
                      <li key={i} style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'flex', gap: '0.35rem', alignItems: 'flex-start' }}>
                        <span style={{ color: 'var(--accent-teal)', flexShrink: 0 }}>•</span>
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '1.5rem 0.5rem', color: 'var(--text-muted)' }}>
              <Bot size={28} style={{ margin: '0 auto 0.5rem', color: 'var(--border-hover)' }} />
              <p style={{ fontSize: '0.8rem', lineHeight: 1.5 }}>
                Click any response to see agent timeline & orchestration details.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
