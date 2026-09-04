import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Upload as UploadIcon, File, CheckCircle, AlertCircle, X } from 'lucide-react'

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 Bytes'
  if (bytes < 1024) return `${bytes} Bytes`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  const handleFileSelect = (selectedFile) => {
    setError('')
    setResult(null)

    // Validate file type
    const validTypes = [
      'application/pdf',
      'image/jpeg',
      'image/jpg',
      'image/png',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ]
    if (!validTypes.includes(selectedFile.type)) {
      setError('Invalid file type. Please upload a PDF, image, DOCX, or TXT file.')
      return
    }

    // Validate file size (50MB max)
    if (selectedFile.size > 50 * 1024 * 1024) {
      setError('File size exceeds 50MB limit.')
      return
    }

    setFile(selectedFile)
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setError('')

    try {
      const response = await api.upload(file)
      setResult(response)
    } catch (err) {
      console.error('Upload error:', err)
      setError(err.message || 'Failed to upload document.')
    } finally {
      setUploading(false)
    }
  }

  const clearFile = () => {
    setFile(null)
    setResult(null)
    setError('')
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Document</h1>
        <p className="text-gray-600">
          Upload a document for AI-powered processing, classification, and field extraction
        </p>
      </div>

      {/* Upload card */}
      <div className="card p-8">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center ${
            dragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {!file ? (
            <>
              <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-base text-gray-700 mb-2">
                Drag and drop your file here, or{' '}
                <label className="text-primary-600 hover:text-primary-700 font-semibold cursor-pointer">
                  browse
                  <input
                    type="file"
                    className="hidden"
                    onChange={handleFileInput}
                    accept=".pdf,.jpg,.jpeg,.png,.docx,.txt"
                  />
                </label>
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Supported formats: PDF, JPG, PNG, DOCX, TXT (max 50MB)
              </p>
            </>
          ) : (
            <div className="flex items-center justify-between bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <File className="w-8 h-8 text-primary-600" />
                <div className="text-left">
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-600">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
              <button
                onClick={clearFile}
                className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
                disabled={uploading}
              >
                <X className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {file && !uploading && (
          <button onClick={handleUpload} className="w-full mt-4 btn btn-primary">
            Upload and Process
          </button>
        )}

        {uploading && (
          <div className="mt-4 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">
              Processing document... This may take a few moments.
            </p>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="card p-6">
          <div className="flex items-center space-x-2 mb-6">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <h2 className="text-xl font-bold text-gray-900">Processing Complete</h2>
          </div>

          {/* Document classification */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Classification</h3>
            <div className="flex items-center space-x-3">
              <span className="badge badge-blue text-base px-3 py-1">
                {result.document_type || 'Unknown'}
              </span>
              {result.classification_confidence && (
                <span className="text-sm text-gray-600 font-semibold">
                  {(result.classification_confidence * 100).toFixed(1)}% confidence
                </span>
              )}
            </div>
          </div>

          {/* Extracted fields */}
          {result.extracted_fields && result.extracted_fields.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Extracted Fields</h3>
              <div className="bg-gray-50 rounded-lg p-4 border">
                <table className="w-full">
                  <tbody className="divide-y divide-gray-200">
                    {result.extracted_fields.map((field, index) => (
                      <tr key={index}>
                        <td className="py-2 pr-4 text-sm font-semibold text-gray-700 w-1/3">
                          {field.field}
                        </td>
                        <td className="py-2 text-sm text-gray-900 font-medium">
                          {field.value !== null && field.value !== undefined && field.value !== '' ? (
                            field.value
                          ) : (
                            <span className="text-gray-400 italic text-xs font-normal">Not extracted</span>
                          )}
                        </td>
                        <td className="py-2 text-right">
                          {typeof field.confidence === 'number' && field.confidence > 0 ? (
                            <span className="text-xs font-semibold text-gray-500">
                              {(field.confidence * 100).toFixed(0)}%
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Knowledge graph info */}
          {result.knowledge_graph && (
            <div className="mb-6 bg-blue-50 p-4 rounded-xl border border-blue-100">
              <h3 className="text-sm font-bold text-blue-900 mb-1">Knowledge Graph Indexing</h3>
              <p className="text-xs font-semibold text-blue-700">
                Indexed {result.knowledge_graph.entity_count || 0} entities and{' '}
                {result.knowledge_graph.relation_count || 0} relationships into knowledge graph.
              </p>
            </div>
          )}

          {/* Document ID */}
          {result.document_id && (
            <div className="pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                Document ID: <span className="font-mono">{result.document_id}</span>
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="mt-6 flex space-x-3">
            <button
              onClick={() => setResult(null)}
              className="btn btn-primary"
            >
              Upload Another
            </button>
            {result.document_id && (
              <button
                onClick={() => navigate(`/documents/${result.document_id}`)}
                className="btn btn-secondary"
              >
                View Details
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Upload
