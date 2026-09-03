import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Settings, Plus, Trash2, Save, AlertCircle, CheckCircle } from 'lucide-react'

const DOCUMENT_TYPES = [
  'Application',
  'Identity Proof',
  'Address Proof',
  'Affidavit',
  'Certificate',
  'Court Document',
  'Invoice',
  'Contract',
  'Receipt',
  'Other',
]

function SchemaManagement() {
  const { isAdmin } = useAuth()
  const [selectedType, setSelectedType] = useState(DOCUMENT_TYPES[0])
  const [schema, setSchema] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    if (selectedType) {
      loadSchema(selectedType)
    }
  }, [selectedType])

  const loadSchema = async (docType) => {
    try {
      setLoading(true)
      setError('')
      const data = await api.getSchema(docType)
      setSchema(data)
    } catch (err) {
      console.error('Failed to load schema:', err)
      setError(err.message || 'Failed to load schema')
      // Initialize empty schema on error
      setSchema({
        document_type: docType,
        fields: [],
      })
    } finally {
      setLoading(false)
    }
  }

  const handleAddField = () => {
    if (!schema) return
    
    const newField = {
      name: 'new_field',
      type: 'string',
      required: false,
      description: '',
    }
    
    setSchema({
      ...schema,
      fields: [...(schema.fields || []), newField],
    })
  }

  const handleUpdateField = (index, key, value) => {
    if (!schema) return
    
    const updatedFields = [...schema.fields]
    updatedFields[index] = {
      ...updatedFields[index],
      [key]: value,
    }
    
    setSchema({
      ...schema,
      fields: updatedFields,
    })
  }

  const handleRemoveField = (index) => {
    if (!schema) return
    
    const updatedFields = schema.fields.filter((_, i) => i !== index)
    setSchema({
      ...schema,
      fields: updatedFields,
    })
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError('')
      setSuccess('')
      
      await api.updateSchema(selectedType, schema)
      
      setSuccess('Schema updated successfully!')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      console.error('Failed to save schema:', err)
      setError(err.message || 'Failed to save schema')
    } finally {
      setSaving(false)
    }
  }

  // Check if user is admin
  if (!isAdmin()) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card p-12 text-center">
          <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Admin Access Required
          </h3>
          <p className="text-gray-600">
            You need administrator privileges to access schema management.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Schema Management</h1>
        <p className="text-gray-600">
          Configure field extraction schemas for different document types
        </p>
      </div>

      {/* Success/Error messages */}
      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start space-x-3">
          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Document type selector */}
        <div className="lg:col-span-1">
          <div className="card p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Document Types</h2>
            <div className="space-y-1">
              {DOCUMENT_TYPES.map((type) => (
                <button
                  key={type}
                  onClick={() => setSelectedType(type)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedType === type
                      ? 'bg-primary-100 text-primary-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Schema editor */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="card p-12 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <Settings className="w-6 h-6 text-gray-600" />
                  <h2 className="text-xl font-bold text-gray-900">{selectedType} Schema</h2>
                </div>
                
                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleAddField}
                    className="btn btn-secondary flex items-center space-x-2"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Field</span>
                  </button>
                  
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn btn-primary flex items-center space-x-2"
                  >
                    <Save className="w-4 h-4" />
                    <span>{saving ? 'Saving...' : 'Save Schema'}</span>
                  </button>
                </div>
              </div>

              {/* Fields */}
              {schema && schema.fields && schema.fields.length > 0 ? (
                <div className="space-y-4">
                  {schema.fields.map((field, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Field Name
                          </label>
                          <input
                            type="text"
                            value={field.name}
                            onChange={(e) => handleUpdateField(index, 'name', e.target.value)}
                            className="input"
                            placeholder="field_name"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Field Type
                          </label>
                          <select
                            value={field.type}
                            onChange={(e) => handleUpdateField(index, 'type', e.target.value)}
                            className="input"
                          >
                            <option value="string">String</option>
                            <option value="number">Number</option>
                            <option value="date">Date</option>
                            <option value="boolean">Boolean</option>
                            <option value="array">Array</option>
                            <option value="object">Object</option>
                          </select>
                        </div>
                      </div>

                      <div className="mb-3">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Description
                        </label>
                        <textarea
                          value={field.description || ''}
                          onChange={(e) => handleUpdateField(index, 'description', e.target.value)}
                          className="input"
                          rows={2}
                          placeholder="Field description for AI extraction..."
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <label className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={field.required || false}
                            onChange={(e) => handleUpdateField(index, 'required', e.target.checked)}
                            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="text-sm text-gray-700">Required field</span>
                        </label>

                        <button
                          onClick={() => handleRemoveField(index)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-600 mb-4">No fields defined yet</p>
                  <button onClick={handleAddField} className="btn btn-primary">
                    Add First Field
                  </button>
                </div>
              )}

              {/* Schema preview */}
              {schema && schema.fields && schema.fields.length > 0 && (
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Schema Preview (JSON)</h3>
                  <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 text-xs overflow-x-auto">
                    {JSON.stringify(schema, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SchemaManagement
