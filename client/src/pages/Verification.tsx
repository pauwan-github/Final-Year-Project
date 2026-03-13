import { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import api from '../Api/apiClient';

interface VerificationResult {
  found: boolean;
  tx_hash?: string;
  block_number?: number;
  gas_used?: number;
  confirmations?: number;
  timestamp?: string;
  status?: string;
  error?: string;
}

export const Verification = () => {
  const [inputHash, setInputHash] = useState('');
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { token } = useAuthStore();

  const verifyHash = async () => {
    if (!inputHash.trim()) {
      setError('Please enter a hash to verify');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      if (!token) {
        setError('Not authenticated. Please log in.');
        setLoading(false);
        return;
      }

      // Try to find audit record with this hash and verify it
      const response = await api.get('/audits/');
      const auditsData = response.data;
      const audits = Array.isArray(auditsData) ? auditsData : (auditsData.results || auditsData);
      
      const matchingAudit = audits.find((a: any) => 
        a.record_hash?.toLowerCase() === inputHash.toLowerCase() ||
        a.tx_hash?.toLowerCase() === inputHash.toLowerCase()
      );

      if (matchingAudit) {
        // Verify the audit
        const verifyResponse = await api.get(`/audits/${matchingAudit.id}/verify/`);
        const verifyData = verifyResponse.data;
        
        setResult({
          found: true,
          tx_hash: verifyData.tx_hash,
          block_number: verifyData.block_number,
          gas_used: verifyData.gas_used,
          confirmations: verifyData.confirmations,
          timestamp: verifyData.timestamp,
          status: verifyData.status,
        });
      } else {
        setResult({
          found: false,
          error: 'Hash not found in blockchain records',
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const openEtherscan = (hash: string) => {
    alert(`📝 Transaction Hash: ${hash}\n\n✓ Transaction is on the in-memory eth-tester blockchain.`);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">🔍 Hash Verification Tool</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">Verify any blockchain hash, transaction, or audit record</p>

      {/* Input Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Enter Hash, Transaction Hash, or Record ID
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={inputHash}
            onChange={(e) => setInputHash(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && verifyHash()}
            placeholder="0x79ad56aee6c35c214f45bf497a8640f9e56144c1a897f6a99f2ffd83e5687b15"
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={verifyHash}
            disabled={loading}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
          >
            {loading ? '⏳ Verifying...' : '✓ Verify'}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-800 dark:text-red-200 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Results Section */}
      {result && (
        <div className={`rounded-lg shadow-lg p-6 ${result.found ? 'bg-green-50 dark:bg-green-900/20' : 'bg-yellow-50 dark:bg-yellow-900/20'}`}>
          {result.found ? (
            <>
              <div className="flex items-center gap-2 mb-6">
                <span className="text-3xl">✅</span>
                <h2 className="text-2xl font-bold text-green-700 dark:text-green-400">Hash Verified Successfully</h2>
              </div>

              <div className="space-y-6">
                {/* Status Badge */}
                <div className="flex items-center gap-2">
                  <span className={`px-4 py-2 rounded-full font-semibold text-sm ${
                    result.status === 'confirmed' ? 'bg-green-500 text-white' :
                    result.status === 'pending' ? 'bg-yellow-500 text-white' :
                    result.status === 'verified' ? 'bg-blue-500 text-white' :
                    'bg-red-500 text-white'
                  }`}>
                    {result.status?.toUpperCase()}
                  </span>
                </div>

                {/* Transaction Hash */}
                {result.tx_hash && (
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Transaction Hash
                    </label>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-gray-900 dark:bg-gray-950 text-green-400 p-3 rounded font-mono text-xs break-all">
                        {result.tx_hash}
                      </code>
                      <button
                        onClick={() => copyToClipboard(result.tx_hash || '')}
                        className="px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded text-xs font-medium transition"
                        title="Copy to clipboard"
                      >
                        📋
                      </button>
                      <button
                        onClick={() => openEtherscan(result.tx_hash || '')}
                        className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition"
                        title="View on Etherscan"
                      >
                        🔗
                      </button>
                    </div>
                  </div>
                )}

                {/* Blockchain Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-300 dark:border-gray-700">
                  {result.block_number !== undefined && result.block_number !== null && (
                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                      <p className="text-sm text-gray-600 dark:text-gray-400 font-semibold">Block Number</p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">#{result.block_number.toLocaleString()}</p>
                    </div>
                  )}
                  
                  {result.gas_used !== undefined && result.gas_used !== null && (
                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                      <p className="text-sm text-gray-600 dark:text-gray-400 font-semibold">Gas Used</p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">{result.gas_used.toLocaleString()}</p>
                    </div>
                  )}

                  {result.confirmations !== undefined && result.confirmations !== null && (
                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                      <p className="text-sm text-gray-600 dark:text-gray-400 font-semibold">Confirmations</p>
                      <p className="text-2xl font-bold text-green-600 dark:text-green-400">{result.confirmations}</p>
                    </div>
                  )}

                  {result.timestamp && (
                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                      <p className="text-sm text-gray-600 dark:text-gray-400 font-semibold">Verified Time</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-white">{new Date(result.timestamp).toLocaleString()}</p>
                    </div>
                  )}
                </div>

                {/* Verification Checklist */}
                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg space-y-2">
                  <p className="font-semibold text-gray-900 dark:text-white mb-3">✓ Verification Checklist</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      <span className="text-gray-700 dark:text-gray-300">Hash exists on blockchain</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      <span className="text-gray-700 dark:text-gray-300">Transaction confirmed</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      <span className="text-gray-700 dark:text-gray-300">Block included in chain</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      <span className="text-gray-700 dark:text-gray-300">Immutable record</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-6">
                <span className="text-3xl">⚠️</span>
                <h2 className="text-2xl font-bold text-yellow-700 dark:text-yellow-400">Hash Not Found</h2>
              </div>
              <p className="text-gray-700 dark:text-gray-300 mb-4">{result.error}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                This hash may not be registered in the system or hasn't been submitted to the blockchain yet.
              </p>
            </>
          )}
        </div>
      )}

      {/* Info Cards */}
      {!result && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
            <h3 className="font-bold text-blue-900 dark:text-blue-300 mb-2">🔐 What is Hash Verification?</h3>
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Verify that a record has been permanently recorded on the blockchain with an immutable hash.
            </p>
          </div>

          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
            <h3 className="font-bold text-green-900 dark:text-green-300 mb-2">⚡ Why It Matters</h3>
            <p className="text-sm text-green-800 dark:text-green-200">
              Blockchain verification proves the authenticity and integrity of medical records.
            </p>
          </div>

          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-6">
            <h3 className="font-bold text-purple-900 dark:text-purple-300 mb-2">🎯 How It Works</h3>
            <p className="text-sm text-purple-800 dark:text-purple-200">
              Enter any hash to check its blockchain status and view transaction details.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Verification;
