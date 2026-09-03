import { useState, useRef } from 'react'
import { api } from '../api/client'
import { Upload as UploadIcon, File, CheckCircle, AlertCircle, X } from 'lucide-react'

function Upload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

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

  const handleFileSelect = (selectedFile) => {
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
      setError('Invalid file type. Please upload PDF, JPG, PNG, DOCX, or TXT files.')
      return
    }

    // Validate file size (50MB max)
    if (selectedFile.size > 50 * 1024 * 1024) {
      setError('File size exceeds 50MB limit.')
      return
    }

    setFile(selectedFile)
    setError('')
    setResult(null)
  }

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first.')
      return
    }

    setUploading(true)
    setError('')

    try {
      const response = await api.upload(file)
      setResult(response)
      setFile(null)
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err) {
      console.error('Upload error:', err)
      setError(err.message || 'Failed to upload document. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const clearFile = () => {
    setFile(null)
    setError('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Document</h1>
        <p className="text-gray-600">
          Upload a document for AI-powered processing, classification, and field extraction
        </p>
      </div>

      {/* Upload area */}
      <div className="card p-8 mb-6">
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            dragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          {!file ? (
            <>
              <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Drag and drop your file here
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                or click to browse from your computer
              </p>
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileInputChange}
                accept=".pdf,.jpg,.jpeg,.png,.docx,.txt"
                className="hidden"
                id="file-input"
              />
              <label htmlFor="file-input" className="btn btn-primary cursor-pointer">
                Select File
              </label>
              <p className="text-xs text-gray-500 mt-4">
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
                    {(file.size / 1024 / 1024).toFixed(2)} MB
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
                <span className="text-sm text-gray-600">
                  {(result.classification_confidence * 100).toFixed(1)}% confidence
                </span>
              )}
            </div>
          </div>

          {/* Extracted fields */}
          {result.extracted_fields && result.extracted_fields.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Extracted Fields</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <table className="w-full">
                  <tbody className="divide-y divide-gray-200">
                    {result.extracted_fields.map((field, index) => (
                      <tr key={index}>
                        <td className="py-2 pr-4 text-sm font-medium text-gray-700 w-1/3">
                          {field.field}
                        </td>
                        <td className="py-2 text-sm text-gray-900">{field.value}</td>
                        <td className="py-2 text-right">
                          {field.confidence && (
                            <span className="text-xs text-gray-500">
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

          {/* Knowledge graph info */}
          {result.knowledge_graph && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Knowledge Graph</h3>
              <p className="text-sm text-gray-600">
                Extracted {result.knowledge_graph.entity_count || 0} entities and{' '}
                {result.knowledge_graph.relation_count || 0} relationships
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
                onClick={() => window.location.href = `/documents/${result.document_id}`}
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
