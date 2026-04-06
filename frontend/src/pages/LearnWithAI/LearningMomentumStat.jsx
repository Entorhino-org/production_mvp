/* LearningMomentumStat.jsx */
import React from 'react';
import { Medal } from 'lucide-react';

const LearningMomentumStat = ({ xp, today }) => {
  return (
    <div className="momentum-card">
      <div className="momentum-info">
        <h4>Learning Momentum</h4>
        <div className="momentum-val">+{xp.toLocaleString()} XP <span>Today</span></div>
      </div>
      <div className="medal-box">
        <Medal size={48} color="var(--neon-purple)" />
      </div>
    </div>
  );
};

export default LearningMomentumStat;
