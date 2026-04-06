/* ProficiencyVarianceCard.jsx */
import React from 'react';

const ProficiencyVarianceCard = ({ data }) => {
  return (
    <div className="variance-panel">
      <div className="variance-head">
        <h3>Subject Proficiency Variance</h3>
        <div className="variance-legend">
          <span className="leg-curr">● CURRENT</span>
          <span className="leg-targ">● TARGET</span>
        </div>
      </div>

      <div className="subj-var-list">
        {data.map((item, idx) => (
          <div key={idx} className="subj-var-item">
            <div className="subj-var-info">
              <span className="subj-var-title">{item.subject}: {item.topic}</span>
              <span className="subj-var-score">{item.current}% <span>/{item.target}% target</span></span>
            </div>
            <div className="var-bar-wrap">
              <div className="var-bar-fill" style={{ width: `${item.current}%` }} />
              <div className="var-bar-target" style={{ left: `${item.target}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProficiencyVarianceCard;
