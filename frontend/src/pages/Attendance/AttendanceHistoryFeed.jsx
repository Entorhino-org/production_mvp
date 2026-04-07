/* AttendanceHistoryFeed.jsx */
import React from 'react';
import { Check, X, Clock } from 'lucide-react';

const AttendanceHistoryFeed = ({ history, onViewAll }) => {
  return (
    <div className="history-feed">
      <div className="history-head">
        <h3>Attendance History</h3>
        <button className="history-all" onClick={onViewAll}>View All</button>
      </div>

      <div className="history-list">
        {history.map((item, idx) => (
          <div key={idx} className="history-item">
            <div className="date-box">
              <span className="date-month">{item.month}</span>
              <span className="date-day">{item.day}</span>
            </div>
            <div className="hist-info">
              <span className="hist-subj">{item.subject}</span>
              <span className="hist-time">{item.time}</span>
            </div>
            <div className={`hist-status ${item.status}`}>
              {item.status === 'present' ? <Check size={14} strokeWidth={3} /> : item.status === 'absent' ? <X size={14} strokeWidth={3} /> : <Clock size={14} strokeWidth={3} />}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AttendanceHistoryFeed;
