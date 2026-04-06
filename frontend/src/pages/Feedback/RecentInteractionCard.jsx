/* RecentInteractionCard.jsx */
import React from 'react';
import { Activity } from 'lucide-react';

const RecentInteractionCard = () => {
  return (
    <div className="recent-int-card">
      <div className="int-icon"><Activity size={18} /></div>
      <h3>Recent Interaction</h3>
      <p>How was your last "Learn with AI" session?</p>
      <div className="int-actions">
        <button className="btn-int-small active">EXCELLENT</button>
        <button className="btn-int-small">POOR</button>
      </div>
    </div>
  );
};

export default RecentInteractionCard;
