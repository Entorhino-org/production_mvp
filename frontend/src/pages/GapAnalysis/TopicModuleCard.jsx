/* TopicModuleCard.jsx */
import React from 'react';
import { Microscope, Sigma, Laptop } from 'lucide-react';

const TopicModuleCard = ({ title, subject, desc, color, type }) => {
  const getIcon = (t) => {
    switch(t) {
      case 'physics': return <Microscope size={18} />;
      case 'math': return <Sigma size={18} />;
      case 'cs': return <Laptop size={18} />;
      default: return <Sigma size={18} />;
    }
  };

  return (
    <div className={`deep-dive-card dd-${color}`}>
      <div className="dd-top">
        <div className="dd-icon">{getIcon(type)}</div>
        <span className="dd-tag">{subject}</span>
      </div>
      <h4>{title}</h4>
      <p>{desc}</p>
      <button className="btn-start-mod">Start Module</button>
    </div>
  );
};

export default TopicModuleCard;
