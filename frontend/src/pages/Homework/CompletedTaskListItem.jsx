/* CompletedTaskListItem.jsx */
import React from 'react';
import { Check } from 'lucide-react';

const CompletedTaskListItem = ({ title, sub, grade, date, isVerified }) => {
  return (
    <div className="completed-item">
      <div className="c-left">
        <div className="c-check">
          <Check size={14} strokeWidth={3} />
        </div>
        <div className="c-info">
          <span className="c-title">{title}</span>
          <span className="c-description">{sub}</span>
        </div>
      </div>
      
      <div className="c-right">
        {grade && <span className="c-grade">GRADED: {grade}</span>}
        {isVerified && <span className="c-grade" style={{ color: 'var(--neon-cyan)' }}>VERIFIED</span>}
        <span className="c-date">{date}</span>
      </div>
    </div>
  );
};

export default CompletedTaskListItem;
