/* DeadlineWarningStrip.jsx */
import React from 'react';
import { Microscope, Pencil } from 'lucide-react';

const DeadlineWarningStrip = ({ title, sub, date, icon: Icon }) => {
  return (
    <div className="warning-strip">
      <div className="strip-left">
        <div className="strip-icon">
          {Icon ? <Icon size={16} /> : <Microscope size={16} />}
        </div>
        <div className="strip-info">
          <h4>{title}</h4>
          <p>{sub}</p>
        </div>
      </div>
      
      <div className="strip-right">
        <div>
          <span className="deadline-txt">DEADLINE LOOMING</span>
          <span className="deadline-date">{date}</span>
        </div>
        <button className="btn-edit">
          <Pencil size={14} />
        </button>
      </div>
    </div>
  );
};

export default DeadlineWarningStrip;
