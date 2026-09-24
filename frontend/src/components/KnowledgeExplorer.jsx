import React, { useState, useEffect } from 'react';
import {
  Search, Database, MessageSquare, Zap, FileText,
  ChevronRight, Clock, RefreshCw, Terminal,
  Activity, BookOpen, Play, Layers, Shield, Globe
} from 'lucide-react';
import { apiUrl } from '../api';
import { supabase } from '../App';

const CATEGORY_OPTIONS = [
  { value: '', label: 'All Categories' },
  { value: 'report',          label: 'Report' },
  { value: 'summary',         label: 'Summary' },
  { value: 'architecture',    label: 'Architecture' },
  { value: 'authentication',  label: 'Authentication' },
  { value: 'api',             label: 'API Endpoints' },
  { value: 'dependency',      label: 'Dependencies' },
  { value: 'business_flow',   label: 'Business Flows' },
  { value: 'concept',         label: 'Concepts' },
  { value: 'file',            label: 'Source Files' },
];

const TOOLS = [
  { name: 'repository_search',   icon: <Search size={14} />,     color: '#2E9E9E', bg: '#E6F7F7', border: '#A8D8D8', desc: 'Semantic search over indexed repo chunks' },
  { name: 'graph_query',         icon: <Layers size={14} />,     color: '#7C3AED', bg: '#F5F3FF', border: '#C4B5FD', desc: 'Query architecture graph, entry points, and flows' },
  { name: 'dependency_lookup',   icon: <Play size={14} />,       color: '#D97706', bg: '#FFFBEB', border: '#FDE68A', desc: 'Lookup packages, frameworks, and databases' },
  { name: 'file_reader',         icon: <FileText size={14} />,   color: '#4338CA', bg: '#EEF2FF', border: '#C7D2FE', desc: 'Retrieve specific source file content' },
  { name: 'architecture_lookup', icon: <Activity size={14} />,   color: '#059669', bg: '#ECFDF5', border: '#A7F3D0', desc: 'Query architecture pattern and key modules' },
  { name: 'api_lookup',          icon: <Terminal size={14} />,   color: '#E11D48', bg: '#FFF1F2', border: '#FECDD3', desc: 'Lookup HTTP routes and authentication methods' },
];

const CATEGORY_COLORS = {
  report:         { color: '#4338CA', bg: '#EEF2FF', border: '#C7D2FE' },
  summary:        { color: '#2E9E9E', bg: '#E6F7F7', border: '#A8D8D8' },
  architecture:   { color: '#7C3AED', bg: '#F5F3FF', border: '#C4B5FD' },
  authentication: { color: '#E11D48', bg: '#FFF1F2', border: '#FECDD3' },
  api:            { color: '#059669', bg: '#ECFDF5', border: '#A7F3D0' },
  dependency:     { color: '#D97706', bg: '#FFFBEB', border: '#FDE68A' },
  business_flow:  { color: '#2E9E9E', bg: '#E6F7F7', border: '#A8D8D8' },
  concept:        { color: '#7C3AED', bg: '#F5F3FF', border: '#C4B5FD' },
  file:           { color: '#475569', bg: '#F8FAFC', border: '#CBD5E1' },
};

const getCatStyle = (cat) => CATEGORY_COLORS[cat] || { color: '#64748B', bg: '#F8FAFC', border: '#CBD5E1' };

const TABS = [
  { id: 'search',        icon: <Search size={14} />,         label: 'Semantic Search' },
  { id: 'memory',        icon: <Database size={14} />,       label: 'Memory Inspector' },
  { id: 'conversations', icon: <MessageSquare size={14} />,  label: 'Conversations' },
  { id: 'tools',         icon: <Zap size={14} />,            label: 'Tool Catalog' },
];

export default function KnowledgeExplorer({ repo_id, apiKey }) {
  const [activeTab, setActiveTab] = useState('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCategory, setSearchCategory] = useState('');
  const [searchTopK, setSearchTopK] = useState(5);
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchLatency, setSearchLatency] = useState(null);
  const [searchError, setSearchError] = useState(null);

  const [memoryInfo, setMemoryInfo] = useState(null);
  const [memoryLoading, setMemoryLoading] = useState(false);

  const [conversations, setConversations] = useState([]);
  const [convsLoading, setConvsLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionHistory, setSessionHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const getAuthHeaders = async () => {
    const h = { 'Content-Type': 'application/json' };
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      h['Authorization'] = `Bearer ${session.access_token}`;
    }
    if (apiKey) h['x-gemini-key'] = apiKey;
    return h;
  };

  useEffect(() => {
    if (activeTab === 'memory') loadMemory();
    if (activeTab === 'conversations') loadConversations();
  }, [activeTab]);

  const loadMemory = async () => {
    setMemoryLoading(true);
    try {
      const headers = await getAuthHeaders();
      const r = await fetch(apiUrl(`/api/memory?repo_id=${repo_id}`), { headers });
      setMemoryInfo(await r.json());
    } catch { setMemoryInfo(null); }
    setMemoryLoading(false);
  };

  const loadConversations = async () => {
    setConvsLoading(true);
    try {
      const headers = await getAuthHeaders();
      const r = await fetch(apiUrl(`/api/conversations?repo_id=${repo_id}`), { headers });
      const d = await r.json();
      setConversations(d.sessions || []);
    } catch { setConversations([]); }
    setConvsLoading(false);
  };

  const loadSessionHistory = async (sessionId) => {
    setHistoryLoading(true);
    try {
      const headers = await getAuthHeaders();
      const r = await fetch(apiUrl(`/api/conversations/${sessionId}`), { headers });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail);
      setSessionHistory(data.history || []);
    } catch {
      setSessionHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSelectSession = (sessionId) => {
    if (selectedSession === sessionId) {
      setSelectedSession(null);
      setSessionHistory([]);
      return;
    }
    setSelectedSession(sessionId);
    loadSessionHistory(sessionId);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setSearchError(null);
    setSearchResults([]);

    try {
      const headers = await getAuthHeaders();
      const r = await fetch(apiUrl('/api/search'), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          repo_id,
          query: searchQuery.trim(),
          top_k: Number(searchTopK),
          category: searchCategory || null,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Search failed');
      setSearchResults(data.results || []);
      setSearchLatency(data.latency_ms);
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'var(--accent-indigo)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', color: '#fff'
          }}>
            <Database size={16} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>Knowledge Explorer</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Pinecone Vector Search, Session History & MCP Catalog
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.35rem', background: 'rgba(0,0,0,0.04)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.4rem',
                padding: '0.4rem 0.75rem', borderRadius: '6px', fontSize: '0.8rem',
                fontWeight: 600, border: 'none', cursor: 'pointer', transition: 'all 0.15s ease',
                background: activeTab === tab.id ? '#fff' : 'transparent',
                color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                boxShadow: activeTab === tab.id ? '0 1px 3px rgba(0,0,0,0.08)' : 'none'
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'search' && (
        <div>
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
              <Search size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Ask a question or enter keywords (e.g. 'JWT verification', 'FastAPI router')..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ width: '100%', paddingLeft: '2.25rem', paddingRight: '0.75rem', height: '38px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}
              />
            </div>
            <select
              value={searchCategory}
              onChange={e => setSearchCategory(e.target.value)}
              style={{ height: '38px', padding: '0 0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.82rem', background: '#fff' }}
            >
              {CATEGORY_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <button type="submit" className="btn-primary" disabled={searchLoading} style={{ height: '38px', padding: '0 1rem', fontSize: '0.85rem' }}>
              {searchLoading ? 'Searching...' : 'Search Vectors'}
            </button>
          </form>

          {searchError && (
            <div style={{ padding: '0.75rem', borderRadius: '8px', background: '#FEF2F2', border: '1px solid #FECDD3', color: '#991B1B', fontSize: '0.82rem', marginBottom: '1rem' }}>
              {searchError}
            </div>
          )}

          {searchResults.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <span>Found <strong>{searchResults.length}</strong> matching vector chunks</span>
                {searchLatency && <span>Search latency: <strong>{searchLatency}ms</strong></span>}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {searchResults.map((item, idx) => {
                  const cat = item.metadata?.category || 'chunk';
                  const style = getCatStyle(cat);
                  return (
                    <div key={item.id || idx} style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '0.85rem', background: '#FAFAFA' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', background: style.bg, color: style.color, border: `1px solid ${style.border}`, textTransform: 'uppercase' }}>
                          {cat}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                          Similarity: {(item.similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <pre style={{ margin: 0, fontSize: '0.82rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'var(--font-mono)', background: '#fff', padding: '0.65rem', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                        {item.content}
                      </pre>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'memory' && (
        <div>
          {memoryLoading ? <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Loading vector stats...</div> :
            memoryInfo ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                <div style={{ padding: '1rem', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Indexed Chunks</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-teal)' }}>{memoryInfo.indexed_chunks}</div>
                </div>
                <div style={{ padding: '1rem', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Pinecone Index</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>{memoryInfo.index_name || 'discord-agent-knowledge'}</div>
                </div>
              </div>
            ) : <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No vector stats available.</div>
          }
        </div>
      )}

      {activeTab === 'conversations' && (
        <div>
          {convsLoading ? <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Loading sessions...</div> :
            conversations.length === 0 ? <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No conversation sessions found.</div> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {conversations.map(sess => (
                  <div key={sess.session_id} onClick={() => handleSelectSession(sess.session_id)} style={{ padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: selectedSession === sess.session_id ? '#EEF2FF' : '#fff', cursor: 'pointer' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Session: {sess.session_id}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Messages: {sess.message_count}</div>
                  </div>
                ))}
              </div>
            )
          }
        </div>
      )}

      {activeTab === 'tools' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
          {TOOLS.map(t => (
            <div key={t.name} style={{ padding: '0.85rem', borderRadius: '8px', border: `1px solid ${t.border}`, background: t.bg }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.85rem', color: t.color, marginBottom: '0.35rem' }}>
                {t.icon} {t.name}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{t.desc}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
