/* GapAnalysisCard.jsx */
import React from 'react';
import { BarChart3 } from 'lucide-react';

const GapAnalysisCard = ({ onClick }) => {
  return (
    <div className="gap-analysis">
      <div className="gap-icon">
        <BarChart3 size={28} />
      </div>
      <h3>Gap Analysis</h3>
      <p>
        Review topics that need more focus based on recent test results.
      </p>
      <button className="btn-review" onClick={onClick}>
        Review Gaps
      </button>
    </div>
  );
};

export default GapAnalysisCard;
