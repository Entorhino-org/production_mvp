/* AcceleratedPathCard.jsx */
import React from 'react';
import { Microscope, Sigma, Brain } from 'lucide-react';

const AcceleratedPathCard = ({ title, category, match, color, desc, type }) => {
  const getIcon = (t) => {
    switch(t) {
      case 'physics': return <Microscope size={18} />;
      case 'math': return <Sigma size={18} />;
      case 'ai': return <Brain size={18} />;
      default: return <Brain size={18} />;
    }
  };

  return (
    <div className="path-card">
      <div className="path-top">
        <div className={`path-icon ${color}`}>{getIcon(type)}</div>
        <div className="path-category">{category}</div>
      </div>
      <h4>{title}</h4>
      <p>{desc}</p>
      <div className="path-progress">
        <div className="path-bar">
          <div className={`path-fill ${color}`} style={{ width: `${match}%` }} />
        </div>
        <span className="path-pct">{match}% Match</span>
      </div>
    </div>
  );
};

export default AcceleratedPathCard;
