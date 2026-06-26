import React, { useState, useRef } from 'react';
import {
  GitBranch, UploadCloud, Link2, Lock, FileArchive,
  Cpu, Sparkles, ArrowRight
} from 'lucide-react';

const EXAMPLE_REPOS = [
  'https://github.com/pallets/flask',
  'https://github.com/tiangolo/fastapi',
  'https://github.com/django/django',
];

export default function InputForm({ onSubmit, loading }) {
  const [inputType, setInputType] = useState('url');
  const [repoUrl, setRepoUrl] = useState('');
  const [token, setToken] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [zipFile, setZipFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file?.name.endsWith('.zip')) setZipFile(file);
    else if (file) alert('Only .zip archives are supported.');
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file?.name.endsWith('.zip')) setZipFile(file);
    else if (file) alert('Only .zip archives are supported.');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputType === 'url') {
      if (!repoUrl.trim()) return;
      onSubmit({ type: 'url', url: repoUrl.trim(), token, apiKey: apiKey.trim() });
    } else {
      if (!zipFile) return;
      onSubmit({ type: 'zip', file: zipFile, apiKey: apiKey.trim() });
    }
  };

  const canSubmit = inputType === 'url' ? !!repoUrl.trim() : !!zipFile;

  return (
    <div className="input-section">
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          background: '#E6F7F7',
          border: '1px solid var(--accent-teal-lt)',
          borderRadius: 'var(--radius-full)',
          padding: '0.3rem 0.9rem',
          fontSize: '0.78rem',
          fontWeight: 600,
          color: 'var(--accent-teal-dk)',
          marginBottom: '1.25rem',
        }}>
          <Sparkles size={12} />
          Powered by Gemini 2.5 Flash + RAG
        </div>
        <h1 className="section-title" style={{ fontSize: '2rem', lineHeight: 1.2, marginBottom: '0.75rem' }}>
          Understand any codebase<br />in seconds
        </h1>
        <p className="section-desc" style={{ maxWidth: '480px', margin: '0 auto' }}>
          Analyze repositories, map architecture, extract APIs, and build a semantic knowledge
          base ready for AI agents — no setup required.
        </p>
      </div>

      {/* Card */}
      <div className="card" style={{ padding: '2rem' }}>
        {/* Input Type Toggle */}
        <div className="dashboard-tabs" style={{ marginBottom: '1.75rem' }}>
          <button
            type="button"
            className={`tab-btn ${inputType === 'url' ? 'active' : ''}`}
            onClick={() => setInputType('url')}
          >
            <Link2 size={15} /> GitHub URL
          </button>
          <button
            type="button"
            className={`tab-btn ${inputType === 'zip' ? 'active' : ''}`}
            onClick={() => setInputType('zip')}
          >
            <FileArchive size={15} /> Upload ZIP
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {inputType === 'url' ? (
            <>
              <div className="form-group">
                <label className="form-label">GitHub Repository URL</label>
                <div className="input-wrapper">
                  <GitBranch className="input-icon" size={17} />
                  <input
                    type="url"
                    required
                    className="form-input"
                    placeholder="https://github.com/owner/repository"
                    value={repoUrl}
                    onChange={e => setRepoUrl(e.target.value)}
                    disabled={loading}
                    id="repo-url-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">
                  GitHub Personal Access Token
                  <span style={{ textTransform: 'none', color: 'var(--text-muted)', marginLeft: '0.5rem', fontWeight: 400 }}>
                    (required for private repos)
                  </span>
                </label>
                <div className="input-wrapper">
                  <Lock className="input-icon" size={17} />
                  <input
                    type="password"
                    className="form-input"
                    placeholder="ghp_xxxxxxxxxxxxxxxx"
                    value={token}
                    onChange={e => setToken(e.target.value)}
                    disabled={loading}
                    id="github-token-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Gemini API Key
                  <span style={{ textTransform: 'none', color: 'var(--text-muted)', marginLeft: '0.5rem', fontWeight: 400 }}>
                    (optional, useful if the server key is rate-limited)
                  </span>
                </label>
                <div className="input-wrapper">
                  <Cpu className="input-icon" size={17} />
                  <input
                    type="password"
                    className="form-input"
                    placeholder="Paste your Gemini API key"
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    disabled={loading}
                    id="gemini-api-key-input"
                  />
                </div>
              </div>

              {/* Example repos */}
              <div style={{ marginBottom: '1.5rem' }}>
                <div className="form-label" style={{ marginBottom: '0.5rem' }}>Try an example</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {EXAMPLE_REPOS.map(url => (
                    <button
                      key={url}
                      type="button"
                      className="btn-secondary"
                      style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
                      onClick={() => setRepoUrl(url)}
                    >
                      {url.split('/').slice(-2).join('/')}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="form-group">
              <label className="form-label">Upload ZIP Archive</label>
              <div
                className={`drag-drop-area ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                id="zip-drop-zone"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  style={{ display: 'none' }}
                  accept=".zip"
                  onChange={handleFileChange}
                  disabled={loading}
                />
                <UploadCloud size={36} className="upload-icon" />
                {zipFile ? (
                  <div>
                    <p style={{ fontWeight: 600, color: 'var(--accent-teal-dk)' }}>{zipFile.name}</p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      {(zipFile.size / (1024 * 1024)).toFixed(2)} MB · Click to change
                    </p>
                  </div>
                ) : (
                  <div>
                    <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      Drop your .zip file here
                    </p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      or click to browse files
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          <button
            id="submit-analysis-btn"
            className="btn-primary"
            type="submit"
            disabled={loading || !canSubmit}
          >
            {loading ? (
              <>
                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2, margin: 0 }} />
                Analyzing...
              </>
            ) : (
              <>Run Intelligence Analysis <ArrowRight size={16} /></>
            )}
          </button>
        </form>
      </div>

      {/* Features strip */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem',
        marginTop: '1.5rem',
      }}>
        {[
          { icon: '🏗', title: 'Architecture Map', desc: 'Auto-detect patterns, entry points, and data flows' },
          { icon: '🔍', title: 'Semantic Search', desc: 'RAG-powered search across indexed code knowledge' },
          { icon: '🤖', title: 'AI Agents', desc: 'Multi-agent Q&A with confidence scoring' },
        ].map(f => (
          <div key={f.title} style={{
            background: 'var(--bg-muted)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            padding: '1rem',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '0.4rem' }}>{f.icon}</div>
            <div style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{f.title}</div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
