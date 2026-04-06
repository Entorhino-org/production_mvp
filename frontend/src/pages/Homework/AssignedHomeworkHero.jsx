/* AssignedHomeworkHero.jsx */
import React from 'react';
import { ClipboardList, CheckCircle2 } from 'lucide-react';

const AssignedHomeworkHero = () => {
  return (
    <div className="hw-hero">
      <div className="hw-hero-text">
        <h1>Assigned <span>Homework</span></h1>
        <p>You have 4 active tasks this week. Keep the momentum high to maintain your "Pulse" streak.</p>
      </div>
      
      <div className="hw-stats">
        <div className="stat-chip pending">
          <div className="stat-icon-wrapper">
            <ClipboardList size={20} />
          </div>
          <div>
            <span className="stat-number">04</span>
            <span className="stat-label">Pending</span>
          </div>
        </div>
        
        <div className="stat-chip completed">
          <div className="stat-icon-wrapper">
            <CheckCircle2 size={20} />
          </div>
          <div>
            <span className="stat-number">18</span>
            <span className="stat-label">Completed</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssignedHomeworkHero;
