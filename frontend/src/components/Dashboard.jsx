import React, { useState } from 'react';
import { marked } from 'marked';
import {
  FileText, Shield, Layers, HelpCircle, HardDrive,
  Terminal, Download, Eye, Play, ListFilter,
  AlertTriangle, Network, ChevronDown, ChevronRight, Database
} from 'lucide-react';
import GraphViewer from './GraphViewer';
import RepositoryAssistant from './RepositoryAssistant';
import KnowledgeExplorer from './KnowledgeExplorer';
import { apiUrl } from '../api';

const TABS = [
  { id: 'report',      icon: <FileText size={15} />,      label: 'Intelligence Report' },
  { id: 'summary',     icon: <Play size={15} />,           label: 'Knowledge Summary' },
  { id: 'profile',     icon: <Layers size={15} />,         label: 'Repository Profile' },
  { id: 'graph',       icon: <Network size={15} />,        label: 'Architecture Graph' },
  { id: 'assistant',   icon: <HelpCircle size={15} />,     label: 'AI Assistant' },
  { id: 'knowledge',   icon: <Database size={15} />,       label: 'Knowledge Explorer' },
];

export default function Dashboard({ analysisResult }) {
  const [activeTab, setActiveTab] = useState('report');
  const [showFullJson, setShowFullJson] = useState(false);

  const { repo_id, project_name, data } = analysisResult;
  const { report, profile, summary, graph } = data;

  const renderedReportHtml = React.useMemo(() => {
    try { return { __html: marked.parse(report || '') }; }
    catch (e) { return { __html: `<p>Failed to render: ${e.message}</p>` }; }
  }, [report]);

  const getDownloadUrl = (type) => apiUrl(`/api/download/${repo_id}/${type}`);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

      {/* ── Header Bar ── */}
      <div className="dashboard-header">
        <div>
          <h2 className="section-title" style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>
            Intelligence Dashboard
          </h2>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <span className="repo-meta">
              <Layers size={13} style={{ color: 'var(--accent-teal)' }} />
              {project_name}
            </span>
            <span className="repo-meta">
              <Terminal size={13} style={{ color: 'var(--accent-indigo)' }} />
              {profile.architecture_pattern}
            </span>
          </div>
        </div>

        <div className="download-bar">
          {[
            ['report', 'Report.md'],
            ['profile', 'Profile.json'],
            ['summary', 'Summary.json'],
            ['graph', 'Graph.json'],
          ].map(([type, label]) => (
            <a key={type} href={getDownloadUrl(type)} download className="btn-secondary">
              <Download size={13} /> {label}
            </a>
          ))}
        </div>
      </div>

      {/* ── Tab Navigation ── */}
      <div className="dashboard-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ── */}
      <div className="tab-pane">

        {/* ── REPORT ── */}
        {activeTab === 'report' && (
          <div className="card report-content" dangerouslySetInnerHTML={renderedReportHtml} />
        )}

        {/* ── SUMMARY ── */}
        {activeTab === 'summary' && (
          <div className="summary-grid">
            {/* Elevator pitch */}
            <div className="summary-card full-width">
              <div className="summary-title">
                <Eye size={18} style={{ color: 'var(--accent-teal)' }} /> Project Purpose
              </div>
              <p style={{
                fontSize: '1.05rem',
                color: 'var(--text-secondary)',
                fontStyle: 'italic',
                lineHeight: 1.7,
                borderLeft: '3px solid var(--accent-teal)',
                paddingLeft: '1rem',
              }}>
                "{summary.elevator_pitch}"
              </p>
            </div>

            {/* Core Features */}
            <div className="summary-card">
              <div className="summary-title">
                <Play size={16} style={{ color: 'var(--accent-green)' }} /> Core Features
              </div>
              <ul className="list-styled">
                {summary.core_features?.map((f, i) => (
                  <li key={i} className="list-item-styled">
                    <span className="list-item-icon">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Workflows */}
            <div className="summary-card">
              <div className="summary-title">
                <ListFilter size={16} style={{ color: 'var(--accent-indigo)' }} /> User Workflows
              </div>
              <ul className="list-styled">
                {summary.main_workflows?.map((w, i) => (
                  <li key={i} className="list-item-styled">
                    <span className="list-item-icon">⚡</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Key Components */}
            <div className="summary-card">
              <div className="summary-title">
                <Layers size={16} style={{ color: 'var(--accent-purple)' }} /> Key Components
              </div>
              <ul className="list-styled">
                {summary.key_components?.map((c, i) => (
                  <li key={i} className="list-item-styled">
                    <span className="list-item-icon">⚙</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Risks */}
            <div className="summary-card">
              <div className="summary-title">
                <AlertTriangle size={16} style={{ color: 'var(--accent-amber)' }} /> Architectural Risks
              </div>
              <ul className="list-styled">
                {summary.key_risks?.map((r, i) => (
                  <li key={i} className="list-item-styled">
                    <span className="list-item-icon risk">⚠</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Start Points */}
            <div className="summary-card full-width">
              <div className="summary-title">
                <HelpCircle size={16} style={{ color: 'var(--accent-teal)' }} /> Where to Start Reading Code
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.25rem' }}>
                {summary.developer_start_points?.map((pt, i) => (
                  <div key={i} className="module-chip" style={{ color: 'var(--accent-teal-dk)' }}>
                    {pt}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── PROFILE ── */}
        {activeTab === 'profile' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="tech-cards-grid">

              <div className="tech-card">
                <div className="tech-card-header"><Terminal size={16} /> Languages</div>
                <div className="badge-container">
                  {profile.languages?.map((l, i) => (
                    <span key={i} className="tech-badge language">{l}</span>
                  ))}
                </div>
              </div>

              <div className="tech-card">
                <div className="tech-card-header"><Layers size={16} /> Frameworks</div>
                <div className="badge-container">
                  {profile.frameworks?.map((f, i) => (
                    <span key={i} className="tech-badge">{f}</span>
                  ))}
                </div>
              </div>

              <div className="tech-card">
                <div className="tech-card-header"><HardDrive size={16} /> Databases</div>
                <div className="badge-container">
                  {profile.databases?.map((d, i) => (
                    <span key={i} className="tech-badge db">{d}</span>
                  ))}
                </div>
              </div>

              <div className="tech-card">
                <div className="tech-card-header"><Shield size={16} /> Security & Auth</div>
                <div className="badge-container">
                  {profile.authentication_methods?.map((a, i) => (
                    <span key={i} className="tech-badge" style={{
                      color: 'var(--accent-rose)',
                      background: '#FFF1F2',
                      borderColor: '#FECDD3',
                    }}>{a}</span>
                  ))}
                </div>
              </div>

            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="card" style={{ padding: '1.5rem' }}>
                <h4 style={{
                  fontFamily: 'var(--font-display)', marginBottom: '1rem',
                  fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 700
                }}>API Endpoints</h4>
                <div style={{ maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {profile.api_endpoints?.map((ep, i) => (
                    <div key={i} className="api-endpoint-item">{ep}</div>
                  ))}
                </div>
              </div>

              <div className="card" style={{ padding: '1.5rem' }}>
                <h4 style={{
                  fontFamily: 'var(--font-display)', marginBottom: '1rem',
                  fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 700
                }}>Core Modules</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', maxHeight: 280, overflowY: 'auto' }}>
                  {profile.major_modules?.map((m, i) => (
                    <span key={i} className="module-chip">{m}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showFullJson ? '1rem' : 0 }}>
                <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 700 }}>
                  Raw repository_profile.json
                </h4>
                <button className="btn-secondary" onClick={() => setShowFullJson(!showFullJson)}>
                  {showFullJson ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  {showFullJson ? 'Hide' : 'Show'} JSON
                </button>
              </div>
              {showFullJson && (
                <pre className="json-block">{JSON.stringify(profile, null, 2)}</pre>
              )}
            </div>
          </div>
        )}

        {/* ── GRAPH ── */}
        {activeTab === 'graph' && (
          <div className="card" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
              Code Topology Graph
            </h3>
            <GraphViewer graphData={graph} />
          </div>
        )}

        {/* ── AI ASSISTANT ── */}
        {activeTab === 'assistant' && (
          <RepositoryAssistant repo_id={repo_id} apiKey={analysisResult.apiKey} />
        )}

        {/* ── KNOWLEDGE EXPLORER ── */}
        {activeTab === 'knowledge' && (
          <KnowledgeExplorer repo_id={repo_id} apiKey={analysisResult.apiKey} />
        )}

      </div>
    </div>
  );
}
