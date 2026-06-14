/* UpdateGridItem.jsx */
import React from 'react';
import { ChevronRight, Calendar, GraduationCap, Coffee, Zap, Library, ShieldCheck, ExternalLink } from 'lucide-react';

const UpdateGridItem = ({ title, desc, date, type, cta }) => {
  const getIcon = (t) => {
    switch(t) {
      case 'calendar': return <Calendar size={18} />;
      case 'grad': return <GraduationCap size={18} />;
      case 'coffee': return <Coffee size={18} />;
      case 'zap': return <Zap size={18} />;
      case 'library': return <Library size={18} />;
      case 'shield': return <ShieldCheck size={18} />;
      default: return <Zap size={18} />;
    }
  };

  return (
    <div className="update-card">
      <div className="update-top">
        <div className="update-icon">{getIcon(type)}</div>
        <span className="update-date">{date}</span>
      </div>
      <h4>{title}</h4>
      <p>{desc}</p>
      <div className="update-link">
        {cta === 'AccessLibrary' ? (
          <>Access Library <ExternalLink size={12} /></>
        ) : (
          <>{cta} <ChevronRight size={12} /></>
        )}
      </div>
    </div>
  );
};

export default UpdateGridItem;
