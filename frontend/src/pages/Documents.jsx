import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { FileText, Search, Calendar, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react'

function Documents() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('all') // all, verified, unverified

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      setLoading(true)
      const data = await api.documentsList()
      setDocuments(Array.isArray(data) ? data : data.documents || [])
    } catch (err) {
      console.error('Failed to load documents:', err)
      setError(err.message || 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = 
      doc.filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.document_type?.toLowerCase().includes(searchTerm.toLowerCase())
    
    const vStatus = (doc.verification_status || '').toUpperCase()
    const isReviewed = Boolean(vStatus && ['VERIFIED', 'COMPLETE', 'REJECTED', 'NEEDS_REVIEW', 'INCOMPLETE', 'HOLD', 'REVOKED', 'EXPIRED'].includes(vStatus))

    if (filter === 'reviewed') {
      return matchesSearch && isReviewed
    } else if (filter === 'unreviewed') {
      return matchesSearch && !isReviewed
    }
    
    return matchesSearch
  })

  const getStatusBadge = (rawStatus) => {
    const status = (rawStatus || '').toUpperCase()
    const statusConfig = {
      VERIFIED: { label: 'Verified', icon: CheckCircle, className: 'badge-green' },
      COMPLETE: { label: 'Verified', icon: CheckCircle, className: 'badge-green' },
      REJECTED: { label: 'Rejected', icon: XCircle, className: 'badge-red' },
      REVOKED: { label: 'Rejected', icon: XCircle, className: 'badge-red' },
      NEEDS_REVIEW: { label: 'Hold for Review', icon: Clock, className: 'badge-amber' },
      INCOMPLETE: { label: 'Hold for Review', icon: Clock, className: 'badge-amber' },
      HOLD: { label: 'Hold for Review', icon: Clock, className: 'badge-amber' },
      EXPIRED: { label: 'Expired', icon: Clock, className: 'badge-amber' },
      UNREVIEWED: { label: 'Unreviewed', icon: AlertCircle, className: 'badge-gray' },
      PENDING: { label: 'Unreviewed', icon: AlertCircle, className: 'badge-gray' },
    }

    const config = statusConfig[status] || { label: 'Unreviewed', icon: AlertCircle, className: 'badge-gray' }
    const Icon = config.icon

    return (
      <span className={`badge ${config.className} flex items-center space-x-1`}>
        <Icon className="w-3 h-3" />
        <span>{config.label}</span>
      </span>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Documents</h1>
        <p className="text-gray-600">Manage and view your uploaded documents</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={loadDocuments}
              className="mt-2 text-sm text-red-700 underline hover:text-red-800"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Filters and search */}
      <div className="card p-4 mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Filter buttons */}
          <div className="flex space-x-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('reviewed')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === 'reviewed'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Reviewed
            </button>
            <button
              onClick={() => setFilter('unreviewed')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === 'unreviewed'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Unreviewed
            </button>
          </div>
        </div>
      </div>

      {/* Documents list */}
      {filteredDocuments.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {searchTerm ? 'No documents found' : 'No documents yet'}
          </h3>
          <p className="text-gray-600 mb-4">
            {searchTerm
              ? 'Try adjusting your search or filter'
              : 'Upload your first document to get started'}
          </p>
          {!searchTerm && (
            <Link to="/upload" className="btn btn-primary">
              Upload Document
            </Link>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredDocuments.map((doc) => (
            <Link
              key={doc.document_id}
              to={`/documents/${doc.document_id}`}
              className="card p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="bg-primary-100 p-3 rounded-lg">
                    <FileText className="w-6 h-6 text-primary-600" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-gray-900 mb-1 truncate">
                      {doc.filename}
                    </h3>
                    
                    <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 mb-2">
                      <span className="badge badge-blue">{doc.document_type}</span>
                      
                      <div className="flex items-center space-x-1">
                        <Calendar className="w-4 h-4" />
                        <span>{formatDate(doc.upload_date)}</span>
                      </div>
                      
                      {doc.ocr_confidence && (
                        <span>OCR: {(doc.ocr_confidence * 100).toFixed(0)}%</span>
                      )}
                    </div>
                    
                    {doc.extracted_fields && doc.extracted_fields.length > 0 && (
                      <p className="text-sm text-gray-600">
                        {doc.extracted_fields.length} fields extracted
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="ml-4">
                  {getStatusBadge(doc.verification_status)}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Results count */}
      {filteredDocuments.length > 0 && (
        <p className="text-sm text-gray-600 mt-4 text-center">
          Showing {filteredDocuments.length} of {documents.length} documents
        </p>
      )}
    </div>
  )
}

export default Documents
