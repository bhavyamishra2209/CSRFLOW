import { useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, FileText, CheckCircle, MessageSquare, AlertCircle } from 'lucide-react'

function Analytics() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      const data = await api.userStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to load analytics:', err)
      setError(err.message || 'Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Analytics</h1>
          <p className="text-gray-600">View insights and statistics about your documents</p>
        </div>

        <div className="card p-12 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {error || 'No Analytics Data Available'}
          </h3>
          <p className="text-gray-600 mb-4">
            {error ? 'There was an error loading your analytics' : 'Upload documents to see analytics'}
          </p>
          <button onClick={loadStats} className="btn btn-primary">
            {error ? 'Try Again' : 'Refresh'}
          </button>
        </div>
      </div>
    )
  }

  // Prepare data for charts
  const documentTypeData = stats.documents_by_type
    ? Object.entries(stats.documents_by_type).map(([type, count]) => ({
        name: type,
        value: count,
      }))
    : []

  const verificationData = [
    { name: 'Verified', value: stats.verified_documents || 0, color: '#10b981' },
    { name: 'Unverified', value: (stats.total_documents || 0) - (stats.verified_documents || 0), color: '#6b7280' },
  ]

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#f97316', '#ec4899']

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Analytics</h1>
        <p className="text-gray-600">View insights and statistics about your documents</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Documents</h3>
            <FileText className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.total_documents || 0}</p>
          <p className="text-sm text-gray-500 mt-1">
            {stats.documents_this_week || 0} uploaded this week
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Verified</h3>
            <CheckCircle className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.verified_documents || 0}</p>
          <p className="text-sm text-gray-500 mt-1">
            {stats.verification_rate || 0}% verification rate
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">AI Queries</h3>
            <MessageSquare className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.total_queries ?? stats.total_queries_made ?? 0}</p>
          <p className="text-sm text-gray-500 mt-1">
            {stats.queries_today ?? stats.total_queries_made ?? 0} queries today
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">OCR Confidence</h3>
            <TrendingUp className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {stats.avg_ocr_confidence ?? (stats.average_ocr_confidence ? Math.round(stats.average_ocr_confidence * 100) : 100)}%
          </p>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${stats.avg_ocr_confidence ?? (stats.average_ocr_confidence ? Math.round(stats.average_ocr_confidence * 100) : 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Documents by Type - Bar Chart */}
        {documentTypeData.length > 0 && (
          <div className="card p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Documents by Type</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={documentTypeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Verification Status - Pie Chart */}
        <div className="card p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Verification Status</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={verificationData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {verificationData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Documents by Type - Pie Chart */}
        {documentTypeData.length > 0 && (
          <div className="card p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Document Type Distribution</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={documentTypeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {documentTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Additional Stats */}
        <div className="card p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Summary Statistics</h2>
          <dl className="space-y-4">
            <div className="flex justify-between items-center">
              <dt className="text-sm font-medium text-gray-600">Total Documents</dt>
              <dd className="text-lg font-semibold text-gray-900">{stats.total_documents || 0}</dd>
            </div>
            
            <div className="flex justify-between items-center">
              <dt className="text-sm font-medium text-gray-600">Verified Documents</dt>
              <dd className="text-lg font-semibold text-green-600">{stats.verified_documents || 0}</dd>
            </div>
            
            <div className="flex justify-between items-center">
              <dt className="text-sm font-medium text-gray-600">Documents This Week</dt>
              <dd className="text-lg font-semibold text-blue-600">{stats.documents_this_week || 0}</dd>
            </div>
            
            <div className="flex justify-between items-center">
              <dt className="text-sm font-medium text-gray-600">Total Queries</dt>
              <dd className="text-lg font-semibold text-gray-900">{stats.total_queries ?? stats.total_queries_made ?? 0}</dd>
            </div>
            
            <div className="flex justify-between items-center">
              <dt className="text-sm font-medium text-gray-600">Queries Today</dt>
              <dd className="text-lg font-semibold text-purple-600">{stats.queries_today ?? stats.total_queries_made ?? 0}</dd>
            </div>
            
            <div className="flex justify-between items-center pt-4 border-t border-gray-200">
              <dt className="text-sm font-medium text-gray-600">Average OCR Confidence</dt>
              <dd className="text-lg font-semibold text-gray-900">
                {stats.avg_ocr_confidence ?? (stats.average_ocr_confidence ? Math.round(stats.average_ocr_confidence * 100) : 100)}%
              </dd>
            </div>
            
            {stats.verification_rate !== undefined && (
              <div className="flex justify-between items-center">
                <dt className="text-sm font-medium text-gray-600">Verification Rate</dt>
                <dd className="text-lg font-semibold text-gray-900">{stats.verification_rate}%</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </div>
  )
}

export default Analytics
