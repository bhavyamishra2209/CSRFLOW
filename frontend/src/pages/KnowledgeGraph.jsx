import { useEffect, useState, useRef } from 'react'
import { api } from '../api/client'
import { Network, AlertCircle, Info } from 'lucide-react'
import ForceGraph2D from 'react-force-graph-2d'

function KnowledgeGraph() {
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedNode, setSelectedNode] = useState(null)
  const graphRef = useRef()

  useEffect(() => {
    loadGraph()
  }, [])

  const loadGraph = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await api.kgVisualize()
      
      // Check if response is HTML (iframe content)
      if (typeof response === 'string' && response.includes('<html')) {
        // For HTML response, we'll display it in an iframe
        setGraphData({ type: 'html', content: response })
      } else if (response.nodes && response.links) {
        // For JSON graph data
        setGraphData({
          type: 'json',
          nodes: response.nodes.map(node => ({
            id: node.id,
            name: node.label || node.name || node.id,
            type: node.type || 'unknown',
            ...node
          })),
          links: response.links.map(link => ({
            source: link.source,
            target: link.target,
            label: link.type || link.label || '',
            ...link
          }))
        })
      } else {
        setError('No graph data available')
      }
    } catch (err) {
      console.error('Failed to load knowledge graph:', err)
      setError(err.message || 'Failed to load knowledge graph')
    } finally {
      setLoading(false)
    }
  }

  const handleNodeClick = (node) => {
    setSelectedNode(node)
  }

  const getNodeColor = (node) => {
    const colorMap = {
      person: '#3b82f6',
      location: '#10b981',
      date: '#f59e0b',
      organization: '#8b5cf6',
      document: '#ef4444',
    }
    return colorMap[node.type?.toLowerCase()] || '#6b7280'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-12rem)] flex flex-col">
      <div className="mb-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Knowledge Graph</h1>
        <p className="text-gray-600">
          Visualize entities and relationships extracted from your documents
        </p>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={loadGraph}
              className="mt-2 text-sm text-red-700 underline hover:text-red-800"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {!error && !graphData && (
        <div className="card p-12 text-center">
          <Network className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Knowledge Graph Available
          </h3>
          <p className="text-gray-600 mb-4">
            Upload a document to populate the knowledge graph
          </p>
          <a href="/upload" className="btn btn-primary">
            Upload Document
          </a>
        </div>
      )}

      {graphData && graphData.type === 'html' && (
        <div className="flex-1 card p-0 overflow-hidden">
          <iframe
            srcDoc={graphData.content}
            className="w-full h-full border-0"
            title="Knowledge Graph Visualization"
          />
        </div>
      )}

      {graphData && graphData.type === 'json' && (
        <div className="flex-1 flex gap-4">
          {/* Graph visualization */}
          <div className="flex-1 card p-0 overflow-hidden relative">
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              nodeLabel="name"
              nodeColor={getNodeColor}
              nodeRelSize={6}
              linkLabel="label"
              linkDirectionalArrowLength={3.5}
              linkDirectionalArrowRelPos={1}
              linkCurvature={0.25}
              onNodeClick={handleNodeClick}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const label = node.name
                const fontSize = 12 / globalScale
                ctx.font = `${fontSize}px Sans-Serif`
                
                // Draw node circle
                ctx.beginPath()
                ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false)
                ctx.fillStyle = getNodeColor(node)
                ctx.fill()
                
                // Draw label
                ctx.textAlign = 'center'
                ctx.textBaseline = 'middle'
                ctx.fillStyle = '#1f2937'
                ctx.fillText(label, node.x, node.y + 12)
              }}
              backgroundColor="#f9fafb"
            />
            
            {/* Legend */}
            <div className="absolute top-4 right-4 bg-white rounded-lg shadow-md p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Entity Types</h3>
              <div className="space-y-2">
                {[
                  { type: 'Person', color: '#3b82f6' },
                  { type: 'Location', color: '#10b981' },
                  { type: 'Date', color: '#f59e0b' },
                  { type: 'Organization', color: '#8b5cf6' },
                  { type: 'Document', color: '#ef4444' },
                  { type: 'Other', color: '#6b7280' },
                ].map((item) => (
                  <div key={item.type} className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-xs text-gray-700">{item.type}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Node details panel */}
          {selectedNode && (
            <div className="w-80 card p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Node Details</h3>
              
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Name</dt>
                  <dd className="mt-1 text-sm text-gray-900">{selectedNode.name}</dd>
                </div>
                
                {selectedNode.type && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Type</dt>
                    <dd className="mt-1">
                      <span className="badge badge-blue">{selectedNode.type}</span>
                    </dd>
                  </div>
                )}
                
                {selectedNode.properties && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500 mb-2">Properties</dt>
                    <dd className="space-y-2">
                      {Object.entries(selectedNode.properties).map(([key, value]) => (
                        <div key={key} className="text-sm">
                          <span className="text-gray-600">{key}:</span>{' '}
                          <span className="text-gray-900">{String(value)}</span>
                        </div>
                      ))}
                    </dd>
                  </div>
                )}
              </dl>
              
              <button
                onClick={() => setSelectedNode(null)}
                className="mt-4 w-full btn btn-secondary text-sm"
              >
                Close
              </button>
            </div>
          )}
        </div>
      )}

      {/* Info banner */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start space-x-2">
        <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-blue-700">
          The knowledge graph shows entities (Person, Location, Date, Organization) and their relationships 
          (BORN_ON, LIVES_AT, IDENTIFIED_BY) extracted from your documents.
        </p>
      </div>
    </div>
  )
}

export default KnowledgeGraph
