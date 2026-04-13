/* AvailableTestCard.jsx */
import React from 'react';
import { Clock, HelpCircle, ArrowRight } from 'lucide-react';

const AvailableTestCard = ({ title, sub, duration, questions, icon: Icon, isNew, type }) => {
  return (
    <div className="test-card">
      <div className="test-card-top">
        <div className={`test-icon-box ${type}`} style={{ width: '40px', height: '40px' }}>
          <Icon size={20} />
        </div>
        {isNew && <span className="badge-new">NEW</span>}
      </div>
      
      <div className="test-info">
        <h3>{title}</h3>
        <p className="test-sub">{sub}</p>
      </div>

      <div className="test-meta">
        <div className="meta-stats">
          <span><Clock size={14} strokeWidth={3} /> {duration}</span>
          <span><HelpCircle size={14} strokeWidth={3} /> {questions} Qs</span>
        </div>
        <button className="btn-start">
          Start
        </button>
      </div>
    </div>
  );
};

export default AvailableTestCard;
