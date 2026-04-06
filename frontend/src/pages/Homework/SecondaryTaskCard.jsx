/* SecondaryTaskCard.jsx */
import React from 'react';
import { Sigma, ArrowUpRight } from 'lucide-react';

const SecondaryTaskCard = ({ title, sub, status, date, icon: Icon }) => {
  return (
    <div className="secondary-card">
      <div className="status-badge-cyan">{status}</div>
      <div className="card-icon-box">
        {Icon ? <Icon size={18} /> : <Sigma size={18} />}
      </div>
      
      <h3>{title}</h3>
      <p>{sub}</p>

      <div className="details-link">
        <span className="result-date" style={{ fontSize: '0.65rem', opacity: 0.6, marginRight: 'auto' }}>{date}</span>
        Details <ArrowUpRight size={14} />
      </div>
    </div>
  );
};

export default SecondaryTaskCard;
