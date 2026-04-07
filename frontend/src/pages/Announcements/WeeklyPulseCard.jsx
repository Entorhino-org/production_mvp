/* WeeklyPulseCard.jsx */
import React from 'react';
import { AlertCircle } from 'lucide-react';

const WeeklyPulseCard = ({ events, resources, deadline }) => {
  return (
    <div className="pulse-card">
      <h3>Weekly Pulse</h3>
      <div className="pulse-stat">
        <div className="pulse-info">
          <span className="pulse-lbl">Active Events</span>
          <span className="pulse-val">{events}</span>
        </div>
        <div className="pulse-bar">
          <div className="pulse-fill" style={{ width: '80%', background: 'var(--neon-cyan)', boxShadow: '0 0 10px var(--neon-cyan)' }} />
        </div>
      </div>

      <div className="pulse-stat">
        <div className="pulse-info">
          <span className="pulse-lbl">New Resources</span>
          <span className="pulse-val green">{resources}</span>
        </div>
        <div className="pulse-bar">
          <div className="pulse-fill" style={{ width: '55%', background: 'var(--neon-green)', boxShadow: '0 0 10px var(--neon-green)' }} />
        </div>
      </div>

      <div className="deadline-alert">
         <AlertCircle size={14} color="#f87171" style={{ marginRight: 6 }} />
         UPCOMING DEADLINE: {deadline}
      </div>
    </div>
  );
};

export default WeeklyPulseCard;
