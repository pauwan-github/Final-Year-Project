import api from '../Api/apiClient';
import type { AuditEvent } from '../components/shared/AuditTimeline';

// Utility to fetch audits and check on-chain verification
export async function fetchAuditEventsWithVerification(): Promise<AuditEvent[]> {
  const res = await api.get('/audits/');
  const data = Array.isArray(res.data) ? res.data : (res.data.results || res.data);

  // For each audit, check on-chain verification (via /audits/:id/verify/)
  const events: AuditEvent[] = await Promise.all(
    data.map(async (a: any) => {
      let verifiedOnChain = false;
      try {
        const verifyRes = await api.get(`/audits/${a.id}/verify/`);
        verifiedOnChain = !!verifyRes.data.on_chain;
      } catch (e) {
        // ignore
      }
      return {
        id: a.id.toString(),
        timestamp: a.created_at,
        user: a.user || 'Unknown',
        action: a.record_type + (a.tx_hash ? ' (On-chain)' : ''),
        details: a.record_hash ? `Hash: ${a.record_hash}` : undefined,
        verifiedOnChain,
      };
    })
  );
  // Sort by timestamp descending
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  return events;
}
