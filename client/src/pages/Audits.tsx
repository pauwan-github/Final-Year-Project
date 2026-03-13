
import { useEffect, useState, useRef } from 'react';
import { Eye, CheckCircle, Copy, AlertCircle, Check, ExternalLink } from 'lucide-react';
import api from '../Api/apiClient';
import AuditTimeline from '../components/shared/AuditTimeline';
import type { AuditEvent } from '../components/shared/AuditTimeline';
import { fetchAuditEventsWithVerification } from '../utils/auditTimelineUtils';


type Audit = {
  id: number;
  record_type: string;
  object_id: number;
  record_hash: string;
  record_cid?: string | null;
  tx_hash?: string | null;
  created_at: string;
  user?: string;
  status?: 'pending' | 'confirmed' | 'failed' | 'verified';
  block_number?: number;
  gas_used?: number;
  miner?: string;
};

type BlockchainStatus = {
  connected: boolean;
  chainId: number;
  latestBlock: number;
  gasPrice: string;
  network: string;
};

export const Audits: React.FC = () => {
  const [audits, setAudits] = useState<Audit[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'onchain'>('onchain');
  const [actionLoading, setActionLoading] = useState<Record<number, string | null>>({});
  const [blockchainStatus, setBlockchainStatus] = useState<BlockchainStatus>({
    connected: false,
    chainId: 0,
    latestBlock: 0,
    gasPrice: '0',
    network: 'Unknown'
  });
  const [selectedAudit, setSelectedAudit] = useState<Audit | null>(null);
  const [detailsModal, setDetailsModal] = useState<Audit | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Pagination state
  const [auditCurrentPage, setAuditCurrentPage] = useState(1);
  const [timelineCurrentPage, setTimelineCurrentPage] = useState(1);
  const auditPageSize = 6;
  const timelinePageSize = 6;

  const fetchAudits = async () => {
    setLoading(true);
    try {
      const res = await api.get('/audits/');
      const data = Array.isArray(res.data) ? res.data : (res.data.results || res.data);

      const dedupeByHash = (items: any[]) => {
        const m = new Map<string, any>();
        items.forEach(it => {
          const key = it.record_hash || `${it.record_type}:${it.object_id}`;
          const existing = m.get(key);
          if (!existing) {
            m.set(key, it);
            return;
          }
          try {
            const a = new Date(it.created_at).getTime();
            const b = new Date(existing.created_at).getTime();
            if (!isNaN(a) && !isNaN(b)) {
              if (a > b) m.set(key, it);
            }
          } catch (e) {
            // fallback: keep existing
          }
        });
        return Array.from(m.values());
      };

      const deduped = dedupeByHash(data as any[]);
      const auditData = deduped.map((a: any) => ({
        ...a,
        status: 'confirmed',
      })) as Audit[];
      
      setAudits(auditData);
      
      // Update blockchain status
      await fetchBlockchainStatus();

    } catch (e) {
      console.error('Failed to load audits', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchBlockchainStatus = async () => {
    try {
      const res = await api.get('/blockchain/status/');
      
      // Handle both successful responses and error messages
      const data = res.data || {};
      const isConnected = data.connected === true;
      
      setBlockchainStatus({
        connected: isConnected,
        chainId: data.chain_id || 0,
        latestBlock: data.latest_block || 0,
        gasPrice: data.gas_price || '0',
        network: isConnected ? (data.network || 'Unknown') : (data.network || 'Disconnected')
      });
      
      // Log the status for debugging
      if (!isConnected && data.error) {
        console.warn('Blockchain not connected:', data.error);
      }
    } catch (e) {
      console.error('Failed to fetch blockchain status:', e);
      // Set disconnect state on network error
      setBlockchainStatus({
        connected: false,
        chainId: 0,
        latestBlock: 0,
        gasPrice: '0',
        network: 'Network Error'
      });
    }
  };


  // Fetch audits and timeline events
  useEffect(() => {
    fetchAudits();
    fetchTimeline();
    
    // WebSocket for real-time updates (optional, not required for functionality)
    const wsUrl = import.meta.env.VITE_AUDIT_WS_URL;
    if (wsUrl) {
      try {
        wsRef.current = new window.WebSocket(wsUrl);
        wsRef.current.onmessage = () => {
          fetchAudits();
          fetchTimeline();
        };
        wsRef.current.onerror = (err) => {
          console.warn('WebSocket connection failed:', err);
        };
        wsRef.current.onclose = (evt) => {
          if (evt.code !== 1000) {
            console.warn('WebSocket closed unexpectedly:', evt);
          }
        };
      } catch (e) {
        console.warn('WebSocket setup failed:', e);
      }
    }

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const fetchTimeline = async () => {
    try {
      const events = await fetchAuditEventsWithVerification();
      setTimelineEvents(events);
    } catch (e) {
      // ignore
    }
  };

  const verify = async (id: number) => {
    setActionLoading(prev => ({ ...prev, [id]: 'verify' }));
    try {
      let res;
      try {
        res = await api.get(`/audits/${id}/verify/`);
      } catch (err: any) {
        if (err?.response?.status === 405) {
          res = await api.post(`/audits/${id}/verify/`);
        } else {
          throw err;
        }
      }
      await fetchAudits();
      const txHash = res?.data?.tx_hash;
      const blockNumber = res?.data?.block_number;
      alert(`✓ Verified on Blockchain\nChain: ${blockchainStatus.network}\nBlock: ${blockNumber || 'Pending'}\nTx: ${txHash || '—'}`);
    } catch (e: any) {
      console.error('verify failed', e);
      alert((e?.response?.data?.detail) || 'Verification failed');
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: null }));
    }
  };

  const openIPFSExplorer = (cid: string) => {
    if (!cid) return;
    const ipfsUrl = `https://ipfs.io/ipfs/${cid}`;
    window.open(ipfsUrl, '_blank');
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  const getStatusBadge = (status: string | undefined) => {
    const baseClass = 'px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1 w-fit';
    switch (status) {
      case 'confirmed':
        return <span className={`${baseClass} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`}><CheckCircle size={14} /> Confirmed</span>;
      case 'pending':
        return <span className={`${baseClass} bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200`}><AlertCircle size={14} /> Pending</span>;
      case 'verified':
        return <span className={`${baseClass} bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200`}><CheckCircle size={14} /> Verified</span>;
      case 'failed':
        return <span className={`${baseClass} bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200`}><AlertCircle size={14} /> Failed</span>;
      default:
        return <span className={`${baseClass} bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200`}>—</span>;
    }
  };

  // Pagination helpers
  const getPaginatedAudits = () => {
    const startIdx = (auditCurrentPage - 1) * auditPageSize;
    return audits.slice(startIdx, startIdx + auditPageSize);
  };

  const getPaginatedTimeline = () => {
    const startIdx = (timelineCurrentPage - 1) * timelinePageSize;
    return timelineEvents.slice(startIdx, startIdx + timelinePageSize);
  };

  const totalAuditPages = Math.max(1, Math.ceil(audits.length / auditPageSize));
  const totalTimelinePages = Math.max(1, Math.ceil(timelineEvents.length / timelinePageSize));

  // Simple pagination footer component
  const PaginationFooter = ({ 
    currentPage, 
    totalPages, 
    totalItems,
    pageSize,
    onPageChange 
  }: { 
    currentPage: number; 
    totalPages: number; 
    totalItems: number;
    pageSize: number;
    onPageChange: (page: number) => void 
  }) => {
    if (totalItems === 0) return null;
    return (
      <div className="px-6 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Showing {totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalItems)} of {totalItems}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 rounded-md bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-300 disabled:opacity-50 transition hover:bg-gray-50 dark:hover:bg-gray-600"
          >
            Prev
          </button>

          <div className="flex items-center space-x-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => onPageChange(page)}
                aria-current={page === currentPage}
                className={`px-2 py-1 rounded text-sm transition ${
                  page === currentPage 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                }`}
              >
                {page}
              </button>
            ))}
          </div>

          <button
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 rounded-md bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-300 disabled:opacity-50 transition hover:bg-gray-50 dark:hover:bg-gray-600"
          >
            Next
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 min-h-screen">
      {/* Header with Blockchain Status */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            🔗 Blockchain Audit Ledger
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Immutable medical record verification and transaction tracking
          </p>
        </div>
        <div className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 ${
          blockchainStatus.connected 
            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
            : blockchainStatus.network === 'Network Error'
            ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
        }`}>
          <span className={`w-2 h-2 rounded-full animate-pulse ${
            blockchainStatus.connected 
              ? 'bg-green-600' 
              : blockchainStatus.network === 'Network Error'
              ? 'bg-red-600'
              : 'bg-gray-600'
          }`}></span>
          {blockchainStatus.connected ? 'Blockchain Connected' : 
           blockchainStatus.network === 'Network Error' ? 'Network Error' :
           'Disconnected'}
        </div>
      </div>

      {/* Blockchain Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-blue-500">
          <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">Network</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{blockchainStatus.network}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            {blockchainStatus.network?.includes('Memory') && '(In-Memory Test)'}
            {blockchainStatus.network?.includes('Mainnet') && '(Mainnet)'}
            {blockchainStatus.network === 'Network Error' && '(Check Server)'}
            {blockchainStatus.network === 'Disconnected' && '(Not Available)'}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-purple-500">
          <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">Chain ID</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{blockchainStatus.chainId || '—'}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-green-500">
          <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">Latest Block</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{blockchainStatus.latestBlock.toLocaleString()}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {[
              { key: 'timeline', label: '📊 Audit Timeline' },
              { key: 'onchain', label: '⛓️ On-Chain Records' }
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === key
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Timeline Tab */}
          {activeTab === 'timeline' && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">📅 Audit Timeline</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Chronological view of all system activities and medical record modifications
                </p>
              </div>

              {loading ? (
                <div className="text-center py-12">
                  <div className="inline-block">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                  </div>
                  <p className="mt-4 text-gray-600 dark:text-gray-400">Loading timeline events...</p>
                </div>
              ) : timelineEvents.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <p className="text-gray-600 dark:text-gray-400">No timeline events found</p>
                </div>
              ) : (
                <>
                  <div className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-800 rounded-t-lg p-4">
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      📊 Showing {timelineEvents.length === 0 ? 0 : (timelineCurrentPage - 1) * timelinePageSize + 1} - {Math.min(timelineCurrentPage * timelinePageSize, timelineEvents.length)} of {timelineEvents.length} events
                    </p>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded-b-lg overflow-hidden border border-t-0 border-blue-200 dark:border-blue-700">
                    <AuditTimeline events={getPaginatedTimeline()} />
                    <PaginationFooter 
                      currentPage={timelineCurrentPage}
                      totalPages={totalTimelinePages}
                      totalItems={timelineEvents.length}
                      pageSize={timelinePageSize}
                      onPageChange={setTimelineCurrentPage}
                    />
                  </div>
                </>
              )}
            </div>
          )}

          {/* On-Chain Records Tab */}
          {activeTab === 'onchain' && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">⛓️ On-Chain Audit Records</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Cryptographic hashes and blockchain transaction details for all medical records
                </p>
              </div>

              {loading ? (
                <div className="text-center py-12">
                  <div className="inline-block">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                  </div>
                  <p className="mt-4 text-gray-600 dark:text-gray-400">Loading blockchain records...</p>
                </div>
              ) : audits.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <p className="text-gray-600 dark:text-gray-400">No audit records found</p>
                </div>
              ) : (
                <>
                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900 dark:to-blue-800 rounded-lg p-4 border border-blue-200 dark:border-blue-700">
                      <p className="text-sm text-blue-600 dark:text-blue-300 font-medium">Total Records</p>
                      <p className="text-2xl font-bold text-blue-900 dark:text-blue-100 mt-1">{audits.length}</p>
                    </div>
                    <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900 dark:to-green-800 rounded-lg p-4 border border-green-200 dark:border-green-700">
                      <p className="text-sm text-green-600 dark:text-green-300 font-medium">Confirmed</p>
                      <p className="text-2xl font-bold text-green-900 dark:text-green-100 mt-1">{audits.filter(a => a.status === 'confirmed').length}</p>
                    </div>
                    <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900 dark:to-yellow-800 rounded-lg p-4 border border-yellow-200 dark:border-yellow-700">
                      <p className="text-sm text-yellow-600 dark:text-yellow-300 font-medium">Pending</p>
                      <p className="text-2xl font-bold text-yellow-900 dark:text-yellow-100 mt-1">{audits.filter(a => a.status === 'pending').length}</p>
                    </div>
                  </div>

                  {/* Records Info */}
                  <div className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-800 rounded-t-lg p-4">
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      📊 Showing {audits.length === 0 ? 0 : (auditCurrentPage - 1) * auditPageSize + 1} - {Math.min(auditCurrentPage * auditPageSize, audits.length)} of {audits.length} records
                    </p>
                  </div>

                  {/* Table */}
                  <div className="overflow-x-auto rounded-b-lg border border-t-0 border-blue-200 dark:border-blue-700">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
                        <tr>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wider">Status</th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wider">Record Type</th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wider">Object ID</th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wider">Hash (SHA-256)</th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wider">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {getPaginatedAudits().map(audit => (
                          <tr key={audit.id} className="hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                              onClick={() => setSelectedAudit(selectedAudit?.id === audit.id ? null : audit)}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {getStatusBadge(audit.status)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                                {audit.record_type}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 dark:text-white">
                              #{audit.object_id}
                            </td>
                            <td className="px-6 py-4 text-sm">
                              <code className="bg-gray-100 dark:bg-gray-900 px-3 py-1 rounded font-mono text-xs text-gray-700 dark:text-gray-300 break-all max-w-xs inline-block hover:bg-gray-200 dark:hover:bg-gray-800 transition">
                                {audit.record_hash.slice(0, 16)}...{audit.record_hash.slice(-8)}
                              </code>
                            </td>

                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2" onClick={(e) => e.stopPropagation()}>
                              <button
                                onClick={() => setDetailsModal(audit)}
                                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-medium transition shadow-sm hover:shadow flex items-center gap-1"
                                title="View full details"
                              >
                                <Eye size={14} /> Details
                              </button>
                              <button
                                onClick={() => verify(audit.id)}
                                disabled={!!actionLoading[audit.id]}
                                className={`px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition shadow-sm hover:shadow flex items-center gap-1 ${actionLoading[audit.id] ? 'opacity-60 cursor-not-allowed' : ''}`}
                                title="Verify on blockchain"
                              >
                                {actionLoading[audit.id] === 'verify' ? '...' : <><Check size={14} /> Verify</>}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <PaginationFooter 
                      currentPage={auditCurrentPage}
                      totalPages={totalAuditPages}
                      totalItems={audits.length}
                      pageSize={auditPageSize}
                      onPageChange={setAuditCurrentPage}
                    />
                  </div>
                </>
              )}
            </div>
          )}


        </div>
      </div>

      {/* Details Modal */}
      {detailsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-96 overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">Hash Details</h3>
                <button
                  onClick={() => setDetailsModal(null)}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-2xl"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-6">
                {/* Record Info */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Record Type: {detailsModal.record_type} | Object ID: #{detailsModal.object_id}
                  </label>
                </div>

                {/* SHA-256 Hash */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">SHA-256 Hash</label>
                    <button
                      onClick={() => copyToClipboard(detailsModal.record_hash)}
                      className="text-xs bg-gray-300 dark:bg-gray-700 px-2 py-1 rounded hover:bg-gray-400 dark:hover:bg-gray-600 flex items-center gap-1"
                    >
                      <Copy size={14} /> Copy
                    </button>
                  </div>
                  <code className="block bg-gray-900 text-green-400 p-3 rounded font-mono text-xs break-all overflow-x-auto">
                    {detailsModal.record_hash}
                  </code>
                </div>

                {/* Transaction Hash */}
                {detailsModal.tx_hash && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Transaction Hash</label>
                      <div className="space-x-2">
                        <button
                          onClick={() => copyToClipboard(detailsModal.tx_hash || '')}
                          className="text-xs bg-gray-300 dark:bg-gray-700 px-2 py-1 rounded hover:bg-gray-400 dark:hover:bg-gray-600 flex items-center gap-1"
                        >
                          <Copy size={14} /> Copy
                        </button>
                      </div>
                    </div>
                    <code className="block bg-blue-950 text-blue-300 p-3 rounded font-mono text-xs break-all overflow-x-auto">
                      {detailsModal.tx_hash}
                    </code>
                  </div>
                )}

                {/* IPFS CID */}
                {detailsModal.record_cid && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">IPFS CID</label>
                      <div className="space-x-2">
                        <button
                          onClick={() => copyToClipboard(detailsModal.record_cid || '')}
                          className="text-xs bg-gray-300 dark:bg-gray-700 px-2 py-1 rounded hover:bg-gray-400 dark:hover:bg-gray-600 flex items-center gap-1"
                        >
                          <Copy size={14} /> Copy
                        </button>
                        <button
                          onClick={() => openIPFSExplorer(detailsModal.record_cid || '')}
                          className="text-xs bg-amber-600 hover:bg-amber-700 text-white px-2 py-1 rounded flex items-center gap-1"
                        >
                          <ExternalLink size={14} /> View on IPFS
                        </button>
                      </div>
                    </div>
                    <code className="block bg-amber-950 text-amber-300 p-3 rounded font-mono text-xs break-all overflow-x-auto">
                      {detailsModal.record_cid}
                    </code>
                  </div>
                )}

                {/* Status Info */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400">Status</p>
                    <p className="font-semibold text-gray-900 dark:text-white">{getStatusBadge(detailsModal.status)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400">Created</p>
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">{new Date(detailsModal.created_at).toLocaleString()}</p>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setDetailsModal(null)}
                className="mt-6 w-full px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Audits;
