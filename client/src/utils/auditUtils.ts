// Utility helpers for audit/blockchain stringification
export function storeRecordAsString(record: any): string {
  return typeof record === 'string' ? record : JSON.stringify(record);
}
