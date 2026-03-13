import React from 'react';

export interface AuditEvent {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  details?: string;
  verifiedOnChain?: boolean;
}

interface AuditTimelineProps {
  events: AuditEvent[];
}

const AuditTimeline: React.FC<AuditTimelineProps> = ({ events }) => {
  return (
    <div className="timeline-container">
      <ul className="timeline-list">
        {events.map((event) => (
          <li key={event.id} className="timeline-item flex items-center mb-4">
            <div className="timeline-dot mr-4">
              <span className={`inline-block w-3 h-3 rounded-full ${event.verifiedOnChain ? 'bg-green-500' : 'bg-gray-400'}`}></span>
            </div>
            <div className="flex-1">
              <div className="flex items-center">
                <span className="font-semibold mr-2">{event.user}</span>
                <span className="text-xs text-gray-500">{new Date(event.timestamp).toLocaleString()}</span>
                {event.verifiedOnChain && (
                  <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">Verified</span>
                )}
              </div>
              <div className="text-sm text-gray-700">{event.action}</div>
              {event.details && <div className="text-xs text-gray-500 mt-1">{event.details}</div>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AuditTimeline;
