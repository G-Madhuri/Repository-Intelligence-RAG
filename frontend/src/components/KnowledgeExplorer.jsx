import React, { useState, useEffect } from 'react';
import {
  Search, Database, MessageSquare, Zap, FileText,
  ChevronRight, Clock, RefreshCw, Terminal,
  Activity, BookOpen, Play, Layers, Shield, Globe
} from 'lucide-react';
import { apiUrl } from '../api';

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

  const headers = () => {
    const h = { 'Content-Type': 'application/json' };
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
      const r = await fetch(apiUrl(`/api/memory?repo_id=${repo_id}`));
      setMemoryInfo(await r.json());
    } catch { setMemoryInfo(null); }
    setMemoryLoading(false);
  };

  const loadConversations = async () => {
    setConvsLoading(true);
    try {
      const r = await fetch(apiUrl(`/api/conversations?repo_id=${repo_id}`));
      const d = await r.json();
      setConversations(d.sessions || []);
    } catch { setConversations([]); }
    setConvsLoading(false);
  };

  const loadSessionHistory = async (sessionId) => {
    setHistoryLoading(true);
    try {
      const r = await fetch(apiUrl(`/api/conversations/${sessionId}`));
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
    setSearchLatency(null);
    try {
      const body = { repo_id, query: searchQuery.trim(), top_k: searchTopK };
      if (searchCategory) body.category = searchCategory;
      const r = await fetch(apiUrl('/api/search'), { method: 'POST', headers: headers(), body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Search failed');
      setSearchResults(d.results || []);
      setSearchLatency(d.latency_ms);
    } catch (e) {
      setSearchError(e.message);
    }
    setSearchLoading(false);
  };

  return (
    <div className="ke-container">
      {/* Sub-tabs */}
      <div className="ke-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`ke-tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
            id={`ke-tab-${t.id}`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── SEMANTIC SEARCH ── */}
      {activeTab === 'search' && (
        <div className="ke-panel">
          <div className="ke-panel-title">
            <Search size={16} style={{ color: 'var(--accent-teal)' }} />
            Semantic Knowledge Search
          </div>
          <p className="ke-panel-desc">
            Search across all indexed repository knowledge using natural language.
            Results are ranked by cosine similarity score.
          </p>

          <form onSubmit={handleSearch} className="search-form-row">
            <input
              type="text"
              className="ke-input"
              placeholder="e.g. 'JWT authentication middleware' or 'database connection'"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              id="semantic-search-input"
            />
            <select className="ke-select" value={searchCategory} onChange={e => setSearchCategory(e.target.value)}>
              {CATEGORY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select className="ke-select ke-select-sm" value={searchTopK} onChange={e => setSearchTopK(Number(e.target.value))}>
              {[3, 5, 8, 10].map(n => <option key={n} value={n}>Top {n}</option>)}
            </select>
            <button
              type="submit"
              className="ke-search-btn"
              disabled={searchLoading || !searchQuery.trim()}
              id="semantic-search-btn"
            >
              {searchLoading ? <RefreshCw size={14} className="spin-slow" /> : <Search size={14} />}
              {searchLoading ? 'Searching…' : 'Search'}
            </button>
          </form>

          {searchError && <div className="ke-error-box">{searchError}</div>}

          {searchLatency != null && !searchLoading && (
            <div className="ke-latency-badge">
              <Clock size={11} />
              {searchResults.length} results · {searchLatency}ms
            </div>
          )}

          <div className="search-results-list">
            {searchResults.map((r, i) => {
              const cs = getCatStyle(r.metadata?.category);
              const sim = r.similarity;
              const fillColor = sim > 0.8 ? 'var(--accent-green)' : sim > 0.6 ? 'var(--accent-teal)' : 'var(--accent-amber)';
              return (
                <div key={i} className="search-result-card">
                  <div className="src-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                      <span className="src-category-tag" style={{ color: cs.color, background: cs.bg, borderColor: cs.border }}>
                        {r.metadata?.category || 'general'}
                      </span>
                      {r.metadata?.path && <span className="src-path-tag">{r.metadata.path}</span>}
                    </div>
                    <div className="src-score-bar-wrap">
                      <span className="src-score-label">{Math.round(sim * 100)}%</span>
                      <div className="src-score-bg">
                        <div className="src-score-fill" style={{ width: `${sim * 100}%`, background: fillColor }} />
                      </div>
                    </div>
                  </div>
                  <pre className="src-content">{r.content}</pre>
                </div>
              );
            })}
            {!searchLoading && searchResults.length === 0 && searchLatency != null && (
              <div className="ke-empty">No results found. Try different search terms or select a different category.</div>
            )}
          </div>
        </div>
      )}

      {/* ── MEMORY INSPECTOR ── */}
      {activeTab === 'memory' && (
        <div className="ke-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <div className="ke-panel-title" style={{ marginBottom: 0 }}>
              <Database size={16} style={{ color: 'var(--accent-indigo)' }} />
              Vector Memory Inspector
            </div>
            <button className="ke-refresh-btn" onClick={loadMemory} disabled={memoryLoading}>
              <RefreshCw size={13} className={memoryLoading ? 'spin-slow' : ''} /> Refresh
            </button>
          </div>
          <p className="ke-panel-desc">
            Inspect the repository's semantic knowledge stored in ChromaDB. Each chunk is
            tagged with category metadata for precise retrieval.
          </p>

          {memoryLoading && (
            <div className="ke-spinner-row">
              <RefreshCw size={18} className="spin-slow" style={{ color: 'var(--accent-teal)' }} />
              Loading memory info…
            </div>
          )}

          {memoryInfo && !memoryLoading && (
            <div className="memory-stats-grid">
              <div className="memory-stat-card">
                <div className="msc-label">Indexed Chunks</div>
                <div className="msc-value">{memoryInfo.indexed_chunks?.toLocaleString()}</div>
                <div className="msc-sub">ChromaDB documents</div>
              </div>
              <div className="memory-stat-card">
                <div className="msc-label">Repository ID</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-muted)', wordBreak: 'break-all', marginTop: '0.25rem' }}>
                  {memoryInfo.repo_id}
                </div>
              </div>
              <div className="memory-stat-card">
                <div className="msc-label">Storage Path</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-secondary)', wordBreak: 'break-all', marginTop: '0.25rem' }}>
                  {memoryInfo.storage_path}
                </div>
              </div>
            </div>
          )}

          <div className="ke-info-box" style={{ marginBottom: '1rem' }}>
            <BookOpen size={14} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>
              The knowledge index contains chunked embeddings of the intelligence report, source files,
              architecture concepts, API endpoints, dependencies, business flows, and concepts.
              Embeddings are generated using Gemini <code>text-embedding-004</code>.
            </span>
          </div>

          <div className="ke-category-legend">
            <div className="ke-legend-title">Indexed Categories</div>
            <div className="ke-legend-grid">
              {CATEGORY_OPTIONS.filter(o => o.value).map(o => {
                const cs = getCatStyle(o.value);
                return (
                  <div key={o.value} className="ke-legend-item">
                    <span className="ke-legend-dot" style={{ background: cs.color }} />
                    {o.label}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── CONVERSATIONS ── */}
      {activeTab === 'conversations' && (
        <div className="ke-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <div className="ke-panel-title" style={{ marginBottom: 0 }}>
              <MessageSquare size={16} style={{ color: 'var(--accent-green)' }} />
              Conversation History
            </div>
            <button className="ke-refresh-btn" onClick={loadConversations} disabled={convsLoading}>
              <RefreshCw size={13} className={convsLoading ? 'spin-slow' : ''} /> Refresh
            </button>
          </div>
          <p className="ke-panel-desc">
            All AI Assistant chat sessions for this repository, stored in conversation memory.
          </p>

          {convsLoading && (
            <div className="ke-spinner-row">
              <RefreshCw size={18} className="spin-slow" style={{ color: 'var(--accent-teal)' }} />
              Loading conversations…
            </div>
          )}

          {!convsLoading && conversations.length === 0 && (
            <div className="ke-empty">
              No conversations yet. Start chatting in the AI Assistant tab to see sessions here.
            </div>
          )}

          <div className="conv-list">
            {conversations.map((s, idx) => (
              <div
                key={s.session_id}
                className={`conv-item ${selectedSession === s.session_id ? 'selected' : ''}`}
                onClick={() => handleSelectSession(s.session_id)}
                id={`conv-item-${idx}`}
              >
                <div className="conv-item-header">
                  <span className="conv-idx">#{idx + 1}</span>
                  <span className="conv-summary">{s.summary || 'Untitled Session'}</span>
                  <span className="conv-count">{s.message_count} msgs</span>
                  <ChevronRight
                    size={14}
                    style={{
                      transition: 'transform 0.2s',
                      transform: selectedSession === s.session_id ? 'rotate(90deg)' : 'none',
                      color: 'var(--text-muted)',
                      flexShrink: 0,
                    }}
                  />
                </div>
                <div className="conv-item-meta">
                  <span className="conv-id">{s.session_id?.substring(0, 8)}…</span>
                  <span className="conv-time">{new Date(s.last_updated * 1000).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>

          {selectedSession && (
            <div style={{ marginTop: '1.25rem' }}>
              <div className="ke-panel-title" style={{ marginBottom: '0.75rem' }}>
                <MessageSquare size={14} style={{ color: 'var(--accent-teal)' }} />
                Session Messages
              </div>
              {historyLoading && (
                <div className="ke-spinner-row">
                  <RefreshCw size={16} className="spin-slow" style={{ color: 'var(--accent-teal)' }} />
                  Loading message history…
                </div>
              )}
              {!historyLoading && sessionHistory.length === 0 && (
                <div className="ke-empty">No messages in this session.</div>
              )}
              {!historyLoading && sessionHistory.length > 0 && (
                <div className="conv-list" style={{ maxHeight: 360 }}>
                  {sessionHistory.map((msg, i) => (
                    <div key={i} className="search-result-card">
                      <div className="src-header">
                        <span className={`src-category-tag`} style={{
                          color: msg.role === 'user' ? 'var(--accent-teal-dk)' : 'var(--accent-indigo)',
                          background: msg.role === 'user' ? '#E6F7F7' : '#EEF2FF',
                          borderColor: msg.role === 'user' ? '#A8D8D8' : '#C7D2FE',
                        }}>
                          {msg.role}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── TOOL CATALOG ── */}
      {activeTab === 'tools' && (
        <div className="ke-panel">
          <div className="ke-panel-title">
            <Zap size={16} style={{ color: 'var(--accent-amber)' }} />
            Tool Catalog (MCP-Ready)
          </div>
          <p className="ke-panel-desc">
            These tools are available to the Planner Agent during orchestration.
            Interfaces are compatible with Model Context Protocol (MCP) and Google ADK.
          </p>

          <div className="tool-catalog-grid">
            {TOOLS.map(t => (
              <div key={t.name} className="tool-card" id={`tool-${t.name}`}>
                <div
                  className="tc-icon-wrap"
                  style={{ background: t.bg, borderColor: t.border, color: t.color }}
                >
                  {t.icon}
                </div>
                <div className="tc-body">
                  <div className="tc-name">{t.name}</div>
                  <div className="tc-desc">{t.desc}</div>
                </div>
                <span className="tc-badge">execute()</span>
              </div>
            ))}
          </div>

          <div className="ke-info-box" style={{ marginTop: '1.25rem' }}>
            <Globe size={14} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>
              Each tool implements a <code>BaseTool</code> interface with <code>name</code>,
              <code>description</code>, and <code>execute(**kwargs)</code>. This design is
              forward-compatible with Google ADK, LangGraph, CrewAI, and MCP server registration.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
