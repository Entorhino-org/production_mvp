/* CompletedResultCard.jsx */
import React from 'react';
import { Star, CheckCircle, Award } from 'lucide-react';

const CompletedResultCard = ({ title, date, score, status, iconType }) => {
  const isDistinction = status === 'DISTINCTION';
  const statusClass = isDistinction ? 'status-distinction' : (iconType === 'cyan' ? 'status-pass-cyan' : 'status-pass');
  
  return (
    <div className="result-card">
      <div className="result-header">
        <div className={`result-status-icon ${statusClass}`}>
          {isDistinction ? <Award size={18} /> : iconType === 'star' ? <Star size={18} /> : <CheckCircle size={18} />}
        </div>
        <div className="score-display">
          <span className="score-pct" style={{ color: isDistinction ? 'var(--neon-green)' : 'var(--neon-purple)' }}>{score}%</span>
          <span className="score-label">{status}</span>
        </div>
      </div>

      <div className="result-info">
        <h4>{title}</h4>
        <span className="result-date">Finished {date}</span>
      </div>

      <div className="progress-bar-container">
        <div 
          className="progress-fill" 
          style={{ 
            width: `${score}%`, 
            background: isDistinction ? 'var(--neon-green)' : (iconType === 'cyan' ? 'var(--neon-cyan)' : 'var(--neon-purple)') 
          }} 
        />
      </div>
    </div>
  );
};

export default CompletedResultCard;
