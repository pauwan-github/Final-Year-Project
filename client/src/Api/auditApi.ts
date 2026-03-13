import api from '../Api/apiClient';

// Send a record string to the audit backend for blockchain logging
export async function sendRecordToAudit(recordType: string, objectId: number | string, recordString: string) {
  // This endpoint should exist in your backend to accept audit logs
  // Adjust the URL and payload as needed for your backend
  return api.post('/audits/log/', {
    record_type: recordType,
    object_id: objectId,
    record: recordString,
  });
}
