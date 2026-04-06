/* DomainConfidenceStats.jsx */
import React from 'react';
import { Zap } from 'lucide-react';

const DomainConfidenceStats = ({ domains, action }) => {
  return (
    <div className="gap-side">
      <div className="confidence-card">
        <h4>Domain Confidence</h4>
        <div className="conf-list">
          {domains.map((d, idx) => (
             <div key={idx} className="conf-item" style={{ marginBottom: '15px' }}>
                <div className={`conf-badge ${d.color}`}>{d.score}</div>
                <div className="conf-info">
                   <span className="conf-label">{d.label}</span>
                   <div className="conf-bar"><div className="conf-fill" style={{ width: `${d.score}%`, background: `var(--neon-${d.color})` }} /></div>
                </div>
             </div>
          ))}
        </div>
      </div>

      <div className="rec-action-card">
        <div className="rec-icon"><Zap size={20} fill="currentColor" /></div>
        <div className="rec-text">
          <span>RECOMMENDED ACTION</span>
          <b>{action}</b>
        </div>
      </div>
    </div>
  );
};

export default DomainConfidenceStats;
