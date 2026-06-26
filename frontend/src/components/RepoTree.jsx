import React, { useState } from 'react';
import { Folder, FolderOpen, FileCode, ChevronRight, ChevronDown, GitBranch } from 'lucide-react';

function TreeNode({ name, node }) {
  const isDir = node.type === 'directory';
  const [open, setOpen] = useState(false);

  const fmtSize = (b) => {
    if (!b) return '';
    if (b < 1024) return `${b}B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)}KB`;
    return `${(b / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div style={{ marginBottom: 1 }}>
      <div
        className="tree-item"
        onClick={() => isDir && setOpen(!open)}
        style={{ paddingLeft: 0 }}
      >
        {isDir ? (
          <>
            {open
              ? <ChevronDown size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              : <ChevronRight size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            }
            {open
              ? <FolderOpen size={14} style={{ color: 'var(--accent-amber)', flexShrink: 0 }} />
              : <Folder size={14} style={{ color: 'var(--accent-amber)', flexShrink: 0 }} />
            }
            <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.8rem' }}>{name}</span>
          </>
        ) : (
          <>
            <span style={{ width: 13, flexShrink: 0 }} />
            <FileCode size={13} style={{ color: 'var(--accent-teal)', flexShrink: 0 }} />
            <span className="file" style={{ fontSize: '0.78rem', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {name}
            </span>
            {node.size !== undefined && (
              <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', marginLeft: 'auto', flexShrink: 0, paddingLeft: '0.25rem' }}>
                {fmtSize(node.size)}
              </span>
            )}
          </>
        )}
      </div>

      {isDir && open && node.children && (
        <div style={{ paddingLeft: '0.9rem', borderLeft: '1px solid var(--border-color)', marginLeft: '0.4rem' }}>
          {Object.entries(node.children)
            .sort(([, a], [, b]) => {
              if (a.type === 'directory' && b.type !== 'directory') return -1;
              if (a.type !== 'directory' && b.type === 'directory') return 1;
              return 0;
            })
            .map(([n, c]) => <TreeNode key={c.path || n} name={n} node={c} />)
          }
        </div>
      )}
    </div>
  );
}

export default function RepoTree({ tree, title }) {
  if (!tree || Object.keys(tree).length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '2rem 0' }}>
        No file tree available.
      </div>
    );
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.4rem',
        fontFamily: 'var(--font-display)',
        fontSize: '0.82rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        color: 'var(--text-muted)',
        marginBottom: '0.75rem',
        paddingBottom: '0.5rem',
        borderBottom: '1px solid var(--border-color)',
      }}>
        <GitBranch size={13} style={{ color: 'var(--accent-teal)' }} />
        {title || 'Repository'}
      </div>
      <div style={{ overflow: 'auto', maxHeight: 'calc(100vh - 220px)', paddingRight: '0.25rem' }}>
        {Object.entries(tree)
          .sort(([, a], [, b]) => {
            if (a.type === 'directory' && b.type !== 'directory') return -1;
            if (a.type !== 'directory' && b.type === 'directory') return 1;
            return 0;
          })
          .map(([n, node]) => <TreeNode key={node.path || n} name={n} node={node} />)
        }
      </div>
    </div>
  );
}
