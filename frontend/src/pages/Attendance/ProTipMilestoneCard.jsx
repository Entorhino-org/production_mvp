/* ProTipMilestoneCard.jsx */
import React from 'react';
import { Info } from 'lucide-react';

const ProTipMilestoneCard = () => {
  return (
    <div className="pro-tip-card">
      <div className="tip-head">
        <h3>Pro Tip</h3>
        <div className="tip-icon"><Info size={20} /></div>
      </div>
      
      <p className="tip-content">
        Maintaining above 98% attendance unlocks the "Elite Learner" badge and priority access to AI tutoring modules.
      </p>

      <button className="btn-milestones">
        View Milestones
      </button>
    </div>
  );
};

export default ProTipMilestoneCard;
