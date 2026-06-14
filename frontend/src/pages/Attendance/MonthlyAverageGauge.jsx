/* MonthlyAverageGauge.jsx */
import React from 'react';

const MonthlyAverageGauge = ({ pct, present, absent, leave }) => {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="avg-card">
      <div className="gauge-wrapper">
        <svg width="140" height="140">
          <circle cx="70" cy="70" r={radius} fill="transparent" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
          <circle 
            cx="70" cy="70" r={radius} fill="transparent" 
            stroke="var(--neon-purple)" strokeWidth="12" 
            strokeDasharray={circumference} 
            strokeDashoffset={offset} 
            strokeLinecap="round" 
            transform="rotate(-90 70 70)"
            filter="drop-shadow(0 0 5px var(--neon-purple))"
          />
        </svg>
        <div className="gauge-inner">
          <span className="gauge-pct">{pct}%</span>
          <span className="gauge-lbl">Monthly Average</span>
        </div>
      </div>

      <div className="stat-tri-row">
        <div className="tri-item">
          <span className="tri-num green">{present}</span>
          <span className="tri-lbl">Present</span>
        </div>
        <div className="tri-item">
          <span className="tri-num red">{absent}</span>
          <span className="tri-lbl">Absent</span>
        </div>
        <div className="tri-item">
          <span className="tri-num cyan">{leave}</span>
          <span className="tri-lbl">Leave</span>
        </div>
      </div>
    </div>
  );
};

export default MonthlyAverageGauge;
