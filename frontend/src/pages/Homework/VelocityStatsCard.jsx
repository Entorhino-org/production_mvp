/* VelocityStatsCard.jsx */
import React from 'react';

const VelocityStatsCard = ({ pct }) => {
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="velocity-card" style={{ minHeight: '180px' }}>
      <h4>Submission Velocity</h4>
      
      <div style={{ position: 'relative', width: '70px', height: '70px', margin: 'auto' }}>
        <svg width="70" height="70">
          <circle cx="35" cy="35" r={radius} fill="transparent" stroke="rgba(255,255,255,0.05)" strokeWidth="5" />
          <circle 
            cx="35" cy="35" r={radius} fill="transparent" 
            stroke="var(--neon-cyan)" strokeWidth="5" 
            strokeDasharray={circumference} 
            strokeDashoffset={offset} 
            strokeLinecap="round" 
            transform="rotate(-90 35 35)"
          />
        </svg>
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
          <span style={{ fontSize: '1.2rem', fontWeight: '800', display: 'block' }}>{pct}%</span>
          <span style={{ fontSize: '0.45rem', opacity: 0.5 }}>ON-TIME</span>
        </div>
      </div>

      <div className="velocity-stats">
        <div className="v-stat">
          <span className="v-val green">12</span>
          <span className="v-lbl">Early</span>
        </div>
        <div className="v-stat">
          <span className="v-val purple">02</span>
          <span className="v-lbl">Late</span>
        </div>
        <div className="v-stat">
          <span className="v-val gray">04</span>
          <span className="v-lbl">Missed</span>
        </div>
      </div>
    </div>
  );
};

export default VelocityStatsCard;
