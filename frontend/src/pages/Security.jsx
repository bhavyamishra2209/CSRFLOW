import { useState, useEffect } from 'react';
import { Shield, Lock, FileCheck, Activity, AlertTriangle, CheckCircle } from 'lucide-react';
import api from '../api/client';

export default function Security() {
  const [loading, setLoading] = useState(true);
  const [chainStats, setChainStats] = useState(null);
  const [chainValid, setChainValid] = useState(null);
  const [auditStats, setAuditStats] = useState(null);
  const [recentLogs, setRecentLogs] = useState([]);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    loadSecurityData();
  }, []);

  const loadSecurityData = async () => {
    setLoading(true);
    try {
      // Load chain stats
      const chainStatsRes = await fetch(`${import.meta.env.VITE_API_BASE_URL}/security/hash-chain/stats`);
      const chainStatsData = await chainStatsRes.json();
      console.log('🔗 Hash Chain Stats:', chainStatsData);
      setChainStats(chainStatsData);

      // Load audit stats
      const auditStatsRes = await fetch(`${import.meta.env.VITE_API_BASE_URL}/security/audit/stats`);
      const auditStatsData = await auditStatsRes.json();
      console.log('📊 Audit Stats:', auditStatsData);
      setAuditStats(auditStatsData);

      // Load recent audit logs
      const logsRes = await fetch(`${import.meta.env.VITE_API_BASE_URL}/security/audit/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 10 })
      });
      const logsData = await logsRes.json();
      console.log('📋 Audit Logs:', logsData);
      setRecentLogs(logsData.logs || []);

    } catch (error) {
      console.error('❌ Error loading security data:', error);
    } finally {
      setLoading(false);
    }
  };

  const verifyChain = async () => {
    setVerifying(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/security/hash-chain/verify`);
      const data = await response.json();
      setChainValid(data);
      
      // Reload stats after verification
      await loadSecurityData();
    } catch (error) {
      console.error('Error verifying chain:', error);
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="h-8 w-8 text-blue-600" />
            Security & Audit
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            SHA256 hash chain and comprehensive audit trail
          </p>
        </div>
        <button
          onClick={verifyChain}
          disabled={verifying}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <FileCheck className="h-4 w-4" />
          {verifying ? 'Verifying...' : 'Verify Chain'}
        </button>
      </div>

      {/* Chain Verification Result */}
      {chainValid && (
        <div className={`p-4 rounded-lg border ${
          chainValid.valid 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-2">
            {chainValid.valid ? (
              <CheckCircle className="h-5 w-5 text-green-600" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-red-600" />
            )}
            <span className={`font-medium ${
              chainValid.valid ? 'text-green-800' : 'text-red-800'
            }`}>
              {chainValid.message}
            </span>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Hash Chain Stats */}
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Lock className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Hash Chain</p>
              <p className="text-2xl font-bold text-gray-900">
                {chainStats?.total_entries || 0}
              </p>
            </div>
          </div>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Documents:</span>
              <span className="font-medium">{chainStats?.unique_documents || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Users:</span>
              <span className="font-medium">{chainStats?.unique_users || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Status:</span>
              <span className={`flex items-center gap-1 ${
                chainStats?.chain_valid ? 'text-green-600' : 'text-red-600'
              }`}>
                {chainStats?.chain_valid ? (
                  <>
                    <CheckCircle className="h-3 w-3" />
                    Valid
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-3 w-3" />
                    Invalid
                  </>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Audit Stats */}
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Activity className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Audit Logs</p>
              <p className="text-2xl font-bold text-gray-900">
                {auditStats?.total_entries || 0}
              </p>
            </div>
          </div>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Success:</span>
              <span className="font-medium text-green-600">{auditStats?.success_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Failed:</span>
              <span className="font-medium text-red-600">{auditStats?.failure_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Success Rate:</span>
              <span className="font-medium">{auditStats?.success_rate || 0}%</span>
            </div>
          </div>
        </div>

        {/* Documents Tracked */}
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-100 rounded-lg">
              <FileCheck className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Documents</p>
              <p className="text-2xl font-bold text-gray-900">
                {auditStats?.unique_documents || 0}
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Documents with audit trail
          </p>
        </div>

        {/* Active Users */}
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-orange-100 rounded-lg">
              <Activity className="h-6 w-6 text-orange-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Active Users</p>
              <p className="text-2xl font-bold text-gray-900">
                {auditStats?.unique_users || 0}
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Users with logged actions
          </p>
        </div>
      </div>

      {/* Actions Breakdown */}
      {auditStats?.actions && Object.keys(auditStats.actions).length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Actions Breakdown
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {Object.entries(auditStats.actions).map(([action, count]) => (
              <div key={action} className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className="text-sm text-gray-600 capitalize">{action}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Audit Logs */}
      <div className="bg-white rounded-lg shadow border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Document
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {recentLogs.length > 0 ? (
                recentLogs.map((log, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 capitalize">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.user_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.document_id || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {log.success ? (
                        <span className="flex items-center gap-1 text-green-600 text-sm">
                          <CheckCircle className="h-4 w-4" />
                          Success
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-600 text-sm">
                          <AlertTriangle className="h-4 w-4" />
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                    No audit logs yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
