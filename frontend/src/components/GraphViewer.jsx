import React, { useState, useMemo } from 'react';
import { Network, Activity, ArrowRight, Zap, Target, BookOpen, FileCode } from 'lucide-react';

export default function GraphViewer({ graphData }) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeFlow, setActiveFlow] = useState(null);
  const [activePath, setActivePath] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  const width = 800;
  const height = 500;

  // 1. Process nodes and assign architectural layers (X-coordinates)
  const layoutData = useMemo(() => {
    if (!graphData || !graphData.nodes) return { nodes: [], edges: [] };

    const nodes = [...graphData.nodes];
    const edges = [...graphData.edges];

    // Group nodes by type to layer them
    const layers = {
      entrypoint: [],
      api: [],
      module: [],
      file: [],
      database: [],
      other: []
    };

    nodes.forEach(node => {
      // Normalise type checks
      const type = (node.type || 'file').toLowerCase();
      if (layers[type]) {
        layers[type].push(node);
      } else {
        layers['other'].push(node);
      }
    });

    // Map layer to an X coordinate
    const layerX = {
      entrypoint: 100,
      api: 240,
      module: 440,
      file: 440, // Combine modules and files in the middle
      database: 660,
      other: 550
    };

    const nodePositions = {};

    // Position nodes evenly in Y for each layer
    Object.entries(layers).forEach(([type, layerNodes]) => {
      const x = layerX[type] || 380;
      const count = layerNodes.length;
      
      layerNodes.forEach((node, index) => {
        // Distribute Y values evenly
        const y = count === 1 ? height / 2 : ((index + 0.5) / count) * height;
        nodePositions[node.id] = {
          ...node,
          x,
          y,
          color: getNodeColor(node.type),
        };
      });
    });

    return {
      nodes: Object.values(nodePositions),
      edges: edges.map(edge => ({
        ...edge,
        sourceNode: nodePositions[edge.source],
        targetNode: nodePositions[edge.target]
      })).filter(edge => edge.sourceNode && edge.targetNode)
    };
  }, [graphData]);

  // Color mapping based on node type
  function getNodeColor(type) {
    switch (type?.toLowerCase()) {
      case 'entrypoint':
        return '#f97316'; // Neon Orange
      case 'api':
        return '#10b981'; // Neon Emerald
      case 'database':
        return '#a855f7'; // Purple
      case 'module':
        return '#00f2fe'; // Neon Cyan
      case 'file':
        return '#3b82f6'; // Bright Blue
      default:
        return '#94a3b8'; // Slate
    }
  }

  // Check if link or node is highlighted by selected business flow or critical path
  const highlightedNodeIds = useMemo(() => {
    if (activeFlow) {
      const flow = graphData.business_flows.find(f => f.flow_name === activeFlow);
      return new Set(flow?.steps || []);
    }
    if (activePath) {
      const path = graphData.critical_paths.find(p => p.path_name === activePath);
      return new Set(path?.nodes || []);
    }
    return null;
  }, [activeFlow, activePath, graphData]);

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  const clearSelection = () => {
    setSelectedNode(null);
    setActiveFlow(null);
    setActivePath(null);
  };

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        No relationship graph metadata available.
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '2rem' }}>
      
      {/* Graph Visualiser SVG Panel */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="graph-viewport">
          <svg className="graph-svg" viewBox={`0 0 ${width} ${height}`}>
            <defs>
              {/* Arrow Head markers for directional lines */}
              <marker 
                id="arrow" 
                viewBox="0 0 10 10" 
                refX="18" 
                refY="5" 
                markerWidth="6" 
                markerHeight="6" 
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
              </marker>
              <marker 
                id="arrow-active" 
                viewBox="0 0 10 10" 
                refX="18" 
                refY="5" 
                markerWidth="8" 
                markerHeight="8" 
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#00f2fe" />
              </marker>
            </defs>

            {/* Link lines */}
            {layoutData.edges.map((edge, idx) => {
              const { sourceNode, targetNode } = edge;
              
              // Draw a smooth quadratic Bezier curve
              const dx = targetNode.x - sourceNode.x;
              const dy = targetNode.y - sourceNode.y;
              const cx = sourceNode.x + dx / 2;
              const cy = sourceNode.y + dy / 2 - (dx > 0 ? 30 : -30); // Curve offset

              const isEdgeHighlighted = highlightedNodeIds 
                ? highlightedNodeIds.has(edge.source) && highlightedNodeIds.has(edge.target)
                : false;

              // Dim link lines if another node/path is hovered/active
              let strokeOpacity = 0.25;
              if (hoveredNode) {
                const isConnected = edge.source === hoveredNode || edge.target === hoveredNode;
                strokeOpacity = isConnected ? 0.8 : 0.05;
              } else if (highlightedNodeIds) {
                strokeOpacity = isEdgeHighlighted ? 0.9 : 0.05;
              }

              return (
                <g key={`edge-${idx}`}>
                  <path
                    d={`M ${sourceNode.x} ${sourceNode.y} Q ${cx} ${cy} ${targetNode.x} ${targetNode.y}`}
                    fill="none"
                    stroke={isEdgeHighlighted ? "var(--accent-cyan)" : "#475569"}
                    strokeWidth={isEdgeHighlighted ? 2.5 : 1.25}
                    strokeDasharray={isEdgeHighlighted ? "5,5" : "none"}
                    markerEnd={isEdgeHighlighted ? "url(#arrow-active)" : "url(#arrow)"}
                    style={{ transition: 'stroke-opacity 0.3s', strokeOpacity }}
                  />
                  {/* Subtle label hover */}
                  {isEdgeHighlighted && (
                    <text 
                      x={cx} 
                      y={cy - 10} 
                      fill="var(--accent-cyan)" 
                      fontSize="9px" 
                      fontWeight="600"
                      textAnchor="middle"
                    >
                      {edge.label}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Node elements */}
            {layoutData.nodes.map((node) => {
              const isNodeHighlighted = highlightedNodeIds ? highlightedNodeIds.has(node.id) : true;
              
              // Calculate focus opacity
              let nodeOpacity = 1;
              if (hoveredNode) {
                const isSelf = node.id === hoveredNode;
                const isNeighbour = layoutData.edges.some(
                  e => (e.source === hoveredNode && e.target === node.id) || 
                       (e.target === hoveredNode && e.source === node.id)
                );
                nodeOpacity = (isSelf || isNeighbour) ? 1 : 0.15;
              } else if (highlightedNodeIds) {
                nodeOpacity = isNodeHighlighted ? 1 : 0.15;
              }

              const isSelected = selectedNode?.id === node.id;

              return (
                <g 
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  style={{ transition: 'opacity 0.3s, transform 0.2s', opacity: nodeOpacity }}
                  onClick={() => handleNodeClick(node)}
                  onMouseEnter={() => setHoveredNode(node.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                  className="node-circle"
                >
                  {/* Outer ring for selected node */}
                  {isSelected && (
                    <circle r={14} fill="none" stroke="var(--accent-cyan)" strokeWidth={2} />
                  )}
                  {/* Colored center node */}
                  <circle 
                    r={9} 
                    fill={node.color} 
                    stroke="#0b0f19" 
                    strokeWidth={1.5}
                    style={{ filter: isSelected ? 'drop-shadow(0 0 6px var(--accent-cyan))' : 'none' }}
                  />
                  {/* Node Title text */}
                  <text
                    y={-14}
                    fill="#f1f5f9"
                    fontSize="10px"
                    fontWeight="500"
                    textAnchor="middle"
                    style={{ pointerEvents: 'none', filter: 'drop-shadow(0px 1px 2px rgba(0,0,0,0.9))' }}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Graph Legend */}
          <div className="graph-legend">
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#f97316' }}></span>
              <span>Entry Points</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#10b981' }}></span>
              <span>APIs</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#00f2fe' }}></span>
              <span>Modules / Code</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#a855f7' }}></span>
              <span>Databases / Storage</span>
            </div>
          </div>
        </div>

        {/* Selected Node Details Card */}
        {selectedNode ? (
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <h4 style={{ fontFamily: 'var(--font-display)', color: 'var(--accent-cyan)', margin: 0 }}>
                {selectedNode.label}
              </h4>
              <button 
                onClick={clearSelection}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem' }}
              >
                Clear Focus
              </button>
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <strong>Type:</strong> <span style={{ textTransform: 'capitalize' }}>{selectedNode.type}</span>
            </p>
            {selectedNode.properties?.path && (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem', fontFamily: 'var(--font-mono)' }}>
                {selectedNode.properties.path}
              </p>
            )}
            {selectedNode.properties?.db_type && (
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                <strong>DB Technology:</strong> {selectedNode.properties.db_type}
              </p>
            )}
          </div>
        ) : (
          <div className="glass-panel" style={{ padding: '1.25rem', color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center' }}>
            Hover over nodes to inspect dependencies. Click a node to view properties.
          </div>
        )}
      </div>

      {/* Sidebar: Business Flows, Critical Paths, Concepts lists */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        {/* Business Flows Panel */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div className="summary-title" style={{ fontSize: '1.05rem', marginBottom: '0.75rem' }}>
            <Activity size={18} /> Business Flows
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Sequence steps mapping end-to-end user operations. Click to trace path in the graph.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {graphData.business_flows?.map((flow, idx) => (
              <div 
                key={idx}
                onClick={() => {
                  setActiveFlow(activeFlow === flow.flow_name ? null : flow.flow_name);
                  setActivePath(null);
                }}
                style={{ 
                  padding: '0.75rem', 
                  borderRadius: 'var(--radius-sm)', 
                  background: activeFlow === flow.flow_name ? 'rgba(0, 242, 254, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${activeFlow === flow.flow_name ? 'var(--accent-cyan)' : 'var(--border-color)'}`,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: activeFlow === flow.flow_name ? 'var(--accent-cyan)' : '#f1f5f9' }}>
                  {flow.flow_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  {flow.description}
                </div>
                
                {activeFlow === flow.flow_name && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', alignItems: 'center', marginTop: '0.5rem' }}>
                    {flow.steps.map((step, sIdx) => (
                      <React.Fragment key={sIdx}>
                        <span style={{ fontSize: '8px', background: 'rgba(0,0,0,0.3)', padding: '2px 4px', borderRadius: '2px', color: '#fff', fontFamily: 'var(--font-mono)' }}>
                          {step.split('/').pop()}
                        </span>
                        {sIdx < flow.steps.length - 1 && <ArrowRight size={8} style={{ color: 'var(--text-muted)' }} />}
                      </React.Fragment>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Critical Paths Panel */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div className="summary-title" style={{ fontSize: '1.05rem', marginBottom: '0.75rem', color: 'var(--accent-orange)' }}>
            <Zap size={18} /> Critical Paths
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {graphData.critical_paths?.map((path, idx) => (
              <div 
                key={idx}
                onClick={() => {
                  setActivePath(activePath === path.path_name ? null : path.path_name);
                  setActiveFlow(null);
                }}
                style={{ 
                  padding: '0.75rem', 
                  borderRadius: 'var(--radius-sm)', 
                  background: activePath === path.path_name ? 'rgba(249, 115, 22, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${activePath === path.path_name ? 'var(--accent-orange)' : 'var(--border-color)'}`,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: activePath === path.path_name ? 'var(--accent-orange)' : '#f1f5f9' }}>
                  {path.path_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  {path.description}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Concepts list */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div className="summary-title" style={{ fontSize: '1.05rem', marginBottom: '0.75rem', color: 'var(--accent-purple)' }}>
            <BookOpen size={18} /> Code Concepts
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {graphData.concepts?.map((concept, idx) => (
              <div key={idx} style={{ borderBottom: idx < graphData.concepts.length - 1 ? '1px solid var(--border-color)' : 'none', paddingBottom: '0.5rem' }}>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#c084fc' }}>
                  {concept.name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem', marginBottom: '0.4rem' }}>
                  {concept.description}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {concept.files.map((file, fIdx) => (
                    <div key={fIdx} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      <FileCode size={10} /> {file}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
