import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import {
  ArrowLeft,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Shield,
  Info,
} from 'lucide-react'

function DocumentDetail() {
  const { id } = useParams()
  const [document, setDocument] = useState(null)
  const [loading, setLoading] = useState(true)
  const [verifying, setVerifying] = useState(false)
  const [verification, setVerification] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    loadDocument()
  }, [id])

  const loadDocument = async () => {
    try {
      setLoading(true)
      const data = await api.getDocument(id)
      setDocument(data)
    } catch (err) {
      console.error('Failed to load document:', err)
      setError(err.message || 'Failed to load document')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    try {
      setVerifying(true)
      setError('')
      const result = await api.verifyDocument(id)
      setVerification(result)
      
      // Update document status
      if (document) {
        setDocument({
          ...document,
          verification_status: result.status || result.verdict,
        })
      }
    } catch (err) {
      console.error('Verification failed:', err)
      setError(err.message || 'Failed to verify document')
    } finally {
      setVerifying(false)
    }
  }

  const getVerificationBadge = (status) => {
    const statusConfig = {
      VERIFIED: {
        label: 'Verified',
        icon: CheckCircle,
        className: 'badge-green',
        description: 'This document has been verified against the records database',
      },
      REVOKED: {
        label: 'Revoked',
        icon: XCircle,
        className: 'badge-red',
        description: 'This document has been revoked and is no longer valid',
      },
      EXPIRED: {
        label: 'Expired',
        icon: Clock,
        className: 'badge-amber',
        description: 'This document has expired and may not be valid',
      },
      NOT_FOUND: {
        label: 'Not Found',
        icon: AlertCircle,
        className: 'badge-gray',
        description: 'This document was not found in the records database',
      },
    }

    const config = statusConfig[status] || statusConfig.NOT_FOUND
    const Icon = config.icon

    return { config, Icon }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error && !document) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card p-12 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Document</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link to="/documents" className="btn btn-primary">
            Back to Documents
          </Link>
        </div>
      </div>
    )
  }

  if (!document) {
    return null
  }

  const verificationStatus = verification?.status || verification?.verdict || document.verification_status
  const { config: verificationConfig, Icon: VerificationIcon } = verificationStatus
    ? getVerificationBadge(verificationStatus)
    : { config: null, Icon: null }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/documents"
          className="inline-flex items-center space-x-2 text-primary-600 hover:text-primary-700 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Documents</span>
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <div className="bg-primary-100 p-3 rounded-lg">
              <FileText className="w-8 h-8 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">{document.filename}</h1>
              <div className="flex items-center space-x-3">
                <span className="badge badge-blue">{document.document_type}</span>
                {verificationStatus && verificationConfig && (
                  <span className={`badge ${verificationConfig.className} flex items-center space-x-1`}>
                    <VerificationIcon className="w-3 h-3" />
                    <span>{verificationConfig.label}</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          {!verification && !verificationStatus && (
            <button
              onClick={handleVerify}
              disabled={verifying}
              className="btn btn-primary flex items-center space-x-2"
            >
              <Shield className="w-4 h-4" />
              <span>{verifying ? 'Verifying...' : 'Verify Document'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Verification result */}
      {(verification || verificationStatus) && verificationConfig && (
        <div className={`card p-6 mb-6 border-l-4 ${
          verificationStatus === 'VERIFIED' ? 'border-green-500' :
          verificationStatus === 'REVOKED' ? 'border-red-500' :
          verificationStatus === 'EXPIRED' ? 'border-amber-500' :
          'border-gray-500'
        }`}>
          <div className="flex items-start space-x-3">
            <VerificationIcon className={`w-6 h-6 flex-shrink-0 ${
              verificationStatus === 'VERIFIED' ? 'text-green-600' :
              verificationStatus === 'REVOKED' ? 'text-red-600' :
              verificationStatus === 'EXPIRED' ? 'text-amber-600' :
              'text-gray-600'
            }`} />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Verification: {verificationConfig.label}
              </h3>
              <p className="text-sm text-gray-600 mb-3">{verificationConfig.description}</p>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start space-x-2">
                <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-blue-700">
                  Checked against a records database. Production-ready to swap in a live government registry API.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Extracted Fields */}
      {document.extracted_fields && document.extracted_fields.length > 0 && (
        <div className="card p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Extracted Fields</h2>
          <div className="bg-gray-50 rounded-lg p-4">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 pr-4 text-sm font-semibold text-gray-700">Field</th>
                  <th className="text-left py-2 text-sm font-semibold text-gray-700">Value</th>
                  <th className="text-right py-2 text-sm font-semibold text-gray-700">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {document.extracted_fields.map((field, index) => (
                  <tr key={index}>
                    <td className="py-3 pr-4 text-sm font-medium text-gray-700">
                      {field.field}
                    </td>
                    <td className="py-3 text-sm text-gray-900">{field.value}</td>
                    <td className="py-3 text-right">
                      {field.confidence && (
                        <span className="text-sm text-gray-600">
                          {(field.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Document Metadata */}
      <div className="card p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Document Information</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Document ID</dt>
            <dd className="mt-1 text-sm text-gray-900 font-mono">{document.document_id}</dd>
          </div>
          
          {document.upload_date && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Upload Date</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {new Date(document.upload_date).toLocaleString()}
              </dd>
            </div>
          )}
          
          {document.ocr_confidence !== undefined && (
            <div>
              <dt className="text-sm font-medium text-gray-500">OCR Confidence</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {(document.ocr_confidence * 100).toFixed(1)}%
              </dd>
            </div>
          )}
          
          {document.classification_confidence !== undefined && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Classification Confidence</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {(document.classification_confidence * 100).toFixed(1)}%
              </dd>
            </div>
          )}
          
          {document.page_count && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Pages</dt>
              <dd className="mt-1 text-sm text-gray-900">{document.page_count}</dd>
            </div>
          )}
          
          {document.status && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Processing Status</dt>
              <dd className="mt-1 text-sm text-gray-900">{document.status}</dd>
            </div>
          )}
        </dl>
      </div>
    </div>
  )
}

export default DocumentDetail
